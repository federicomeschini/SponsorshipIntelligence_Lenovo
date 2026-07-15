"""D2 ingestion for the complete client-supplied Blinkfire summary export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


def _number(value: str) -> int:
    return int((value or "0").replace(",", ""))


def ingest_blinkfire(source_path: str, output_dir: str, manifest_path: str,
                     taxonomy_path: str = "data/reference/property_taxonomy.csv") -> None:
    """Normalize the wide daily export; views remain views, never engagements."""
    source, taxonomy = Path(source_path), Path(taxonomy_path)
    with taxonomy.open(encoding="utf-8-sig", newline="") as handle:
        taxonomy_rows = list(csv.DictReader(handle))
    by_label = {row["source_label"]: row["property_id"] for row in taxonomy_rows}
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        source_rows = list(reader)

    labels = [name[:-4] for name in fieldnames if name.endswith(" Imp")]
    expected = {"DATE", *(f"{label} {suffix}" for label in labels for suffix in ("Imp", "Views"))}
    if set(fieldnames) != expected:
        raise ValueError("D2 Blinkfire contract violation: unexpected or unpaired columns")
    missing_taxonomy = sorted(set(labels) - set(by_label))
    if missing_taxonomy:
        raise ValueError(f"D2 Blinkfire contract violation: unmapped source labels {missing_taxonomy}")
    totals = [row for row in source_rows if row["DATE"].strip().upper() == "TOTAL"]
    dated = [row for row in source_rows if row["DATE"].strip().upper() != "TOTAL"]
    if len(totals) != 1:
        raise ValueError("D2 Blinkfire contract violation: expected exactly one TOTAL row")

    output: list[dict[str, Any]] = []
    for row in dated:
        day = date.fromisoformat(row["DATE"])
        for label in labels:
            output.append({
                "date": day, "property_id": by_label[label], "source_label": label,
                "impressions": _number(row[f"{label} Imp"]),
                "views": _number(row[f"{label} Views"]),
            })
    for label in labels:
        for suffix, key in (("Imp", "impressions"), ("Views", "views")):
            observed = sum(row[key] for row in output if row["source_label"] == label)
            declared = _number(totals[0][f"{label} {suffix}"])
            if observed != declared:
                raise ValueError(f"D2 Blinkfire contract violation: TOTAL mismatch for {label} {suffix}")

    output.sort(key=lambda row: (row["date"], row["property_id"]))
    schema = pa.schema([
        ("date", pa.date32()), ("property_id", pa.string()), ("source_label", pa.string()),
        ("impressions", pa.int64()), ("views", pa.int64()),
    ])
    table = pa.Table.from_pylist(output, schema=schema)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    pacsv.write_csv(table, target / "blinkfire_exposure_daily.csv")
    pq.write_table(table, target / "blinkfire_exposure_daily.parquet")
    manifest = {
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_client_scope", "raw_rows": len(source_rows),
        "dated_rows": len(dated), "normalized_rows": len(output),
        "date_min": min(row["date"] for row in output).isoformat(),
        "date_max": max(row["date"] for row in output).isoformat(),
        "properties": len(labels), "total_row_excluded": True,
        "total_row_validation": "passed", "available_measures": ["impressions", "views"],
        "unavailable_measures": ["engagements", "posts", "platform", "post_metadata"],
        "method_note": "Client confirmed this is the complete available D2 scope; views are not relabelled as engagements.",
    }
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/raw/blinkfire/lenovo_sponsorship_exposure_daily_export.csv")
    parser.add_argument("--output-dir", default="data/staged/blinkfire")
    parser.add_argument("--manifest", default="data/staged/blinkfire/pull_manifest.json")
    parser.add_argument("--taxonomy", default="data/reference/property_taxonomy.csv")
    args = parser.parse_args()
    ingest_blinkfire(args.source, args.output_dir, args.manifest, args.taxonomy)
