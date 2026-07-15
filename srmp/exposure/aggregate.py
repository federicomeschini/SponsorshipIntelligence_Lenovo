"""L3 aggregation for the confirmed impressions/views-only D2 scope."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


def _load(path: Path) -> list[dict]:
    if path.suffix == ".parquet":
        return pq.read_table(path).to_pylist()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [{**row, "date": date.fromisoformat(row["date"]),
             "impressions": int(row["impressions"]), "views": int(row["views"])} for row in rows]


def aggregate_weekly(source_path: str, output_path: str,
                     taxonomy_path: str = "data/reference/property_taxonomy.csv") -> None:
    """Create a weekly observed-exposure artifact without fabricating missing measures."""
    rows = _load(Path(source_path))
    with Path(taxonomy_path).open(encoding="utf-8-sig", newline="") as handle:
        valid_ids = {row["property_id"] for row in csv.DictReader(handle)}
    unknown = sorted({row["property_id"] for row in rows} - valid_ids)
    if unknown:
        raise ValueError(f"D2 weekly aggregation violation: unknown property IDs {unknown}")

    groups: dict[tuple[str, date], dict] = {}
    for row in rows:
        week = row["date"] - timedelta(days=row["date"].weekday())
        key = row["property_id"], week
        group = groups.setdefault(key, {"property_id": row["property_id"], "week": week,
                                        "impressions": 0, "views": 0, "dates": set()})
        group["impressions"] += int(row["impressions"])
        group["views"] += int(row["views"])
        group["dates"].add(row["date"])
    output = []
    for group in groups.values():
        impressions, views = group["impressions"], group["views"]
        output.append({
            "property_id": group["property_id"], "week": group["week"],
            "impressions": impressions, "views": views,
            "view_rate": (views / impressions if impressions else None),
            "days_observed": len(group["dates"]), "measurement_scope": "impressions_views_only",
        })
    output.sort(key=lambda row: (row["week"], row["property_id"]))
    schema = pa.schema([
        ("property_id", pa.string()), ("week", pa.date32()), ("impressions", pa.int64()),
        ("views", pa.int64()), ("view_rate", pa.float64()), ("days_observed", pa.int64()),
        ("measurement_scope", pa.string()),
    ])
    table = pa.Table.from_pylist(output, schema=schema)
    target = Path(output_path)
    target.mkdir(parents=True, exist_ok=True)
    pacsv.write_csv(table, target / "blinkfire_exposure_weekly.csv")
    pq.write_table(table, target / "blinkfire_exposure_weekly.parquet")
    manifest = {
        "source": source_path, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "weekly_observed_exposure_available", "row_count": len(output),
        "week_min": min(row["week"] for row in output).isoformat(),
        "week_max": max(row["week"] for row in output).isoformat(),
        "properties": len({row["property_id"] for row in output}),
        "contract_status": "not_C_EXPOSURE_until_adstock_is_added",
    }
    (target / "weekly_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/staged/blinkfire/blinkfire_exposure_daily.parquet")
    parser.add_argument("--output-dir", default="data/staged/blinkfire")
    parser.add_argument("--taxonomy", default="data/reference/property_taxonomy.csv")
    args = parser.parse_args()
    aggregate_weekly(args.source, args.output_dir, args.taxonomy)
