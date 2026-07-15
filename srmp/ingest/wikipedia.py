"""D4 Wikimedia pageview connector."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from srmp.ingest._public import load_yaml, read_or_pull_json, sha256_bytes, write_json


def _chunks(start: date, end: date):
    cursor = start
    while cursor <= end:
        chunk_end = min(end, date(cursor.year, 12, 31))
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def pull_wikipedia(config_path: str, output_dir: str, manifest_path: str) -> None:
    """Pull immutable daily article-language pageviews and stage one typed table."""
    config = load_yaml(config_path)
    start = date.fromisoformat(str(config["horizon"]["start"]))
    configured_end = config["horizon"].get("end")
    end = date.fromisoformat(str(configured_end)) if configured_end else date.today() - timedelta(days=1)
    raw_dir = Path(output_dir)
    staged_dir = Path(config.get("staged_output_dir", "data/staged/wikipedia"))
    rows: list[dict] = []
    pulls: list[dict] = []

    for item in config["articles"]:
        project = item.get("project", "en.wikipedia")
        article = item["article"]
        for chunk_start, chunk_end in _chunks(start, end):
            stem = f"{item['proxy_id']}__{chunk_start:%Y%m%d}_{chunk_end:%Y%m%d}.json"
            url = (
                "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
                f"{quote(project, safe='.')}/all-access/user/{quote(article.replace(' ', '_'), safe='')}/daily/"
                f"{chunk_start:%Y%m%d}/{chunk_end:%Y%m%d}"
            )
            content, payload, cache_hit = read_or_pull_json(raw_dir / stem, url)
            items = payload.get("items", [])
            pulls.append({"file": stem, "url": url, "sha256": sha256_bytes(content),
                          "row_count": len(items), "cache_hit": cache_hit})
            for obs in items:
                rows.append({
                    "proxy_id": item["proxy_id"], "entity_type": item["entity_type"],
                    "project": project, "article": article,
                    "date": datetime.strptime(obs["timestamp"][:8], "%Y%m%d").date(),
                    "views": int(obs["views"]),
                })

    rows.sort(key=lambda row: (row["proxy_id"], row["date"]))
    schema = pa.schema([
        ("proxy_id", pa.string()), ("entity_type", pa.string()), ("project", pa.string()),
        ("article", pa.string()), ("date", pa.date32()), ("views", pa.int64()),
    ])
    table = pa.Table.from_pylist(rows, schema=schema)
    staged_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, staged_dir / "wikipedia_pageviews_daily.parquet")
    pacsv.write_csv(table, staged_dir / "wikipedia_pageviews_daily.csv")
    manifest = {
        "source": "Wikimedia REST API", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path), "horizon": {"start": str(start), "end": str(end)},
        "row_count": len(rows), "pulls": pulls,
    }
    write_json(manifest_path, manifest)
    write_json(staged_dir / "pull_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/wikipedia.yaml")
    parser.add_argument("--output-dir", default="data/raw/wikipedia")
    parser.add_argument("--manifest", default="data/raw/wikipedia/pull_manifest.json")
    args = parser.parse_args()
    pull_wikipedia(args.config, args.output_dir, args.manifest)
