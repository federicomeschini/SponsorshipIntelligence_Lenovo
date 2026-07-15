"""D6 market-data connector using Yahoo's public chart endpoint."""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from srmp.ingest._public import load_yaml, read_or_pull_json, sha256_bytes, write_json


def _epoch(day: date) -> int:
    return int(datetime.combine(day, time.min, tzinfo=timezone.utc).timestamp())


def pull_market_data(config_path: str, output_dir: str, manifest_path: str) -> None:
    """Pull immutable daily prices and stage a typed long table."""
    config = load_yaml(config_path)
    start = date.fromisoformat(str(config["horizon"]["start"]))
    configured_end = config["horizon"].get("end")
    end = date.fromisoformat(str(configured_end)) if configured_end else date.today()
    raw_dir = Path(output_dir)
    staged_dir = Path(config.get("staged_output_dir", "data/staged/market"))
    rows: list[dict] = []
    pulls: list[dict] = []

    for item in config["series"]:
        symbol = item["ticker"]
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}"
            f"?period1={_epoch(start)}&period2={_epoch(end + timedelta(days=1))}"
            "&interval=1d&events=history&includeAdjustedClose=true"
        )
        stem = f"{item['factor_id']}__{start:%Y%m%d}_{end:%Y%m%d}.json"
        content, payload, cache_hit = read_or_pull_json(raw_dir / stem, url)
        result = payload["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote_data = result["indicators"]["quote"][0]
        adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose", quote_data["close"])
        currency = result.get("meta", {}).get("currency", item.get("currency"))
        pulled_rows = 0
        for index, timestamp in enumerate(timestamps):
            close = quote_data["close"][index]
            if close is None:
                continue
            rows.append({
                "factor_id": item["factor_id"], "ticker": symbol,
                "date": datetime.fromtimestamp(timestamp, timezone.utc).date(), "currency": currency,
                "open": quote_data["open"][index], "high": quote_data["high"][index],
                "low": quote_data["low"][index], "close": close,
                "adj_close": adjclose[index], "volume": quote_data["volume"][index],
            })
            pulled_rows += 1
        pulls.append({
            "factor_id": item["factor_id"], "ticker": symbol, "file": stem, "url": url,
            "sha256": sha256_bytes(content), "row_count": pulled_rows, "cache_hit": cache_hit,
        })

    rows.sort(key=lambda row: (row["factor_id"], row["date"]))
    schema = pa.schema([
        ("factor_id", pa.string()), ("ticker", pa.string()), ("date", pa.date32()),
        ("currency", pa.string()), ("open", pa.float64()), ("high", pa.float64()),
        ("low", pa.float64()), ("close", pa.float64()), ("adj_close", pa.float64()),
        ("volume", pa.int64()),
    ])
    table = pa.Table.from_pylist(rows, schema=schema)
    staged_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, staged_dir / "market_prices_daily.parquet")
    pacsv.write_csv(table, staged_dir / "market_prices_daily.csv")
    manifest = {
        "source": "Yahoo Finance chart API", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path), "horizon": {"start": str(start), "end": str(end)},
        "row_count": len(rows), "pulls": pulls,
        "limitations": ["Public endpoint; adjusted-close methodology is provider-defined.",
                        "HKEX-session event mapping remains a separate L5 step."],
    }
    write_json(manifest_path, manifest)
    write_json(staged_dir / "pull_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/market.yaml")
    parser.add_argument("--output-dir", default="data/raw/market")
    parser.add_argument("--manifest", default="data/raw/market/pull_manifest.json")
    args = parser.parse_args()
    pull_market_data(args.config, args.output_dir, args.manifest)
