"""D5 GDELT connector with DOC API probe and BigQuery fallback query."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import requests

from srmp.ingest._public import load_yaml, write_json


def _doc_url(query: str, mode: str, start: str, end: str) -> str:
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode({
        "query": query, "mode": mode, "format": "json",
        "startdatetime": start.replace("-", "") + "000000",
        "enddatetime": end.replace("-", "") + "235959", "maxrecords": 250,
    })


def _bigquery_sql(start: str, end: str) -> str:
    return f'''-- D5 fallback for gdelt-bq.gdeltv2.gkg_partitioned
SELECT
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS date,
  COUNT(DISTINCT DocumentIdentifier) AS news_volume,
  AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS mean_tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN DATE('{start}') AND DATE('{end}')
  AND REGEXP_CONTAINS(LOWER(COALESCE(V2Organizations, '')), r'(^|[;,])lenovo([,;]|$)')
GROUP BY date
ORDER BY date;
'''


def _timeline(payload: dict, metric: str) -> list[dict]:
    timelines = payload.get("timeline", [])
    if not timelines:
        return []
    return [{"date": date.fromisoformat(item["date"][:10]), metric: float(item["value"])}
            for item in timelines[0].get("data", [])]


def pull_gdelt(config_path: str, output_dir: str, manifest_path: str) -> None:
    """Pull brand-day volume/tone, or emit an executable BigQuery fallback."""
    config = load_yaml(config_path)
    start = str(config["horizon"]["start"])
    end = str(config["horizon"].get("end") or date.today())
    raw_dir, staged_dir = Path(output_dir), Path(config["staged_output_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    sql_path = raw_dir / "gdelt_bigquery_fallback.sql"
    sql_path.write_text(_bigquery_sql(start, end), encoding="utf-8")
    pulls: list[dict] = []
    payloads: dict[str, dict] = {}
    status = "doc_api_complete"
    for index, (mode, metric) in enumerate((("timelinevolraw", "news_volume"), ("timelinetone", "mean_tone"))):
        if index:
            time.sleep(6)
        url = _doc_url(config["query"], mode, start, end)
        raw_path = raw_dir / f"gdelt_{mode}_{start}_{end}.json"
        try:
            if raw_path.exists():
                content = raw_path.read_bytes()
                pulls.append({"mode": mode, "url": url, "status_code": 200,
                              "response_sha256": hashlib.sha256(content).hexdigest(), "cache_hit": True})
                payloads[metric] = json.loads(content)
            else:
                response = requests.get(url, timeout=90, headers={"User-Agent": "SRMP/0.1 OpenEconomics research"})
                pulls.append({"mode": mode, "url": url, "status_code": response.status_code,
                              "response_sha256": hashlib.sha256(response.content).hexdigest(), "cache_hit": False})
                if response.status_code == 429:
                    status = "blocked_doc_api_rate_limit_bigquery_required"
                    break
                response.raise_for_status()
                payloads[metric] = response.json()
                raw_path.write_bytes(response.content)
        except (requests.RequestException, ValueError) as exc:
            status = "blocked_doc_api_error_bigquery_required"
            if pulls:
                pulls[-1]["error"] = f"{type(exc).__name__}: {exc}"
            else:
                pulls.append({"mode": mode, "url": url, "error": f"{type(exc).__name__}: {exc}"})
            break

    rows = []
    if status == "doc_api_complete" and len(payloads) == 2:
        volume = {row["date"]: row["news_volume"] for row in _timeline(payloads["news_volume"], "news_volume")}
        tone = {row["date"]: row["mean_tone"] for row in _timeline(payloads["mean_tone"], "mean_tone")}
        rows = [{"date": day, "news_volume": volume.get(day, 0.0), "mean_tone": tone.get(day)}
                for day in sorted(set(volume) | set(tone))]
        staged_dir.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(rows)
        pacsv.write_csv(table, staged_dir / "gdelt_brand_daily.csv")
        pq.write_table(table, staged_dir / "gdelt_brand_daily.parquet")

    start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
    observed_days = {row["date"] for row in rows}
    calendar_days = [start_day + timedelta(days=offset) for offset in range((end_day - start_day).days + 1)]
    missing_days = [day.isoformat() for day in calendar_days if day not in observed_days] if rows else []
    manifest = {
        "source": "GDELT", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": config["query"], "horizon": {"start": start, "end": end},
        "status": status, "row_count": len(rows), "pulls": pulls,
        "calendar_day_count": len(calendar_days), "missing_calendar_day_count": len(missing_days),
        "missing_calendar_days": missing_days,
        "fallback": {"type": "BigQuery", "sql_path": str(sql_path),
                     "table": "gdelt-bq.gdeltv2.gkg_partitioned",
                     "execution_status": "requires Google Cloud credentials and a billing project"},
    }
    write_json(manifest_path, manifest)
    staged_dir.mkdir(parents=True, exist_ok=True)
    write_json(staged_dir / "pull_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/gdelt.yaml")
    parser.add_argument("--output-dir", default="data/raw/gdelt")
    parser.add_argument("--manifest", default="data/raw/gdelt/pull_manifest.json")
    args = parser.parse_args()
    pull_gdelt(args.config, args.output_dir, args.manifest)
