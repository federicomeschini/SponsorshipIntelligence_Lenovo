"""D2 ingestion for the complete client-supplied Blinkfire summary exports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


def _number(value: Any) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return int((value or "0").replace(",", ""))


def _read_export(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Read a wide Blinkfire export (CSV or single-sheet XLSX) as header + rows."""
    if path.suffix.lower() == ".xlsx":
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        if len(workbook.sheetnames) != 1:
            raise ValueError(f"D2 Blinkfire contract violation: expected one sheet in {path.name}")
        values = list(workbook.worksheets[0].iter_rows(values_only=True))
        workbook.close()
        fieldnames = [str(name).strip() for name in values[0]]
        rows = []
        for record in values[1:]:
            if all(cell is None for cell in record):
                continue
            row = dict(zip(fieldnames, record))
            day = row["DATE"]
            row["DATE"] = day.date().isoformat() if isinstance(day, datetime) else str(day).strip()
            rows.append(row)
        return fieldnames, rows
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _normalize_export(path: Path, by_label: dict[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate one export against its own TOTAL row and return long rows."""
    fieldnames, source_rows = _read_export(path)
    labels = [name[:-4] for name in fieldnames if name.endswith(" Imp")]
    expected = {"DATE", *(f"{label} {suffix}" for label in labels for suffix in ("Imp", "Views"))}
    if set(fieldnames) != expected:
        raise ValueError(f"D2 Blinkfire contract violation: unexpected or unpaired columns in {path.name}")
    missing_taxonomy = sorted(set(labels) - set(by_label))
    if missing_taxonomy:
        raise ValueError(f"D2 Blinkfire contract violation: unmapped source labels {missing_taxonomy}")
    totals = [row for row in source_rows if row["DATE"].upper() == "TOTAL"]
    dated = [row for row in source_rows if row["DATE"].upper() != "TOTAL"]
    if len(totals) != 1:
        raise ValueError(f"D2 Blinkfire contract violation: expected exactly one TOTAL row in {path.name}")

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
                raise ValueError(f"D2 Blinkfire contract violation: TOTAL mismatch for {label} {suffix} in {path.name}")
    days = sorted({row["date"] for row in output})
    summary = {
        "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "raw_rows": len(source_rows), "dated_rows": len(dated), "properties": len(labels),
        "date_min": days[0].isoformat(), "date_max": days[-1].isoformat(),
        "total_row_validation": "passed",
    }
    return output, summary


def ingest_blinkfire(source_path: str, output_dir: str, manifest_path: str,
                     taxonomy_path: str = "data/reference/property_taxonomy.csv",
                     supplements: list[str] | None = None) -> None:
    """Normalize the wide daily exports; views remain views, never engagements.

    ``supplements`` are further exports in the same layout (earlier or later periods), applied in order.
    Each is reconciled to its own TOTAL row; on overlapping dates the later
    export replaces the earlier one, because Blinkfire restates recent days.
    """
    taxonomy = Path(taxonomy_path)
    with taxonomy.open(encoding="utf-8-sig", newline="") as handle:
        taxonomy_rows = list(csv.DictReader(handle))
    by_label = {row["source_label"]: row["property_id"] for row in taxonomy_rows}

    by_date: dict[date, list[dict[str, Any]]] = {}
    exports: list[dict[str, Any]] = []
    for path in [Path(source_path), *(Path(item) for item in supplements or [])]:
        rows, summary = _normalize_export(path, by_label)
        incoming: dict[date, list[dict[str, Any]]] = {}
        for row in rows:
            incoming.setdefault(row["date"], []).append(row)
        overlap = sorted(set(incoming) & set(by_date))
        restated = []
        for day in overlap:
            before = sum(row["impressions"] for row in by_date[day])
            after = sum(row["impressions"] for row in incoming[day])
            restated.append({"date": day.isoformat(), "impressions_before": before, "impressions_after": after})
        by_date.update(incoming)
        exports.append({**summary, "overlapping_dates_replaced": restated})

    output = [row for day in sorted(by_date) for row in by_date[day]]
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
        "source": str(source_path), "source_sha256": exports[0]["sha256"],
        "exports": exports, "merge_rule": "later export replaces earlier export on overlapping dates",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete_client_scope", "raw_rows": sum(item["raw_rows"] for item in exports),
        "dated_rows": len(by_date), "normalized_rows": len(output),
        "date_min": min(row["date"] for row in output).isoformat(),
        "date_max": max(row["date"] for row in output).isoformat(),
        "properties": len({row["property_id"] for row in output}), "total_row_excluded": True,
        "total_row_validation": "passed", "available_measures": ["impressions", "views"],
        "unavailable_measures": ["engagements", "posts", "platform", "post_metadata"],
        "method_note": "Client confirmed these are the complete available D2 scope; views are not relabelled as engagements.",
    }
    Path(manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/raw/blinkfire/lenovo_sponsorship_exposure_daily_export.csv")
    parser.add_argument("--supplement", action="append",
                        default=["data/raw/blinkfire/impressions_views_by_2024.xlsx",     # Jan-Sep 2024, before the deal
                                 "data/raw/blinkfire/impressions_views_by_wc.xlsx",       # Jun-Jul 2026, World Cup
                                 "data/raw/blinkfire/impressions_views_by_wc_sept.xlsx"], # Jul-Sep 2026, after the final
                        help="further export in the same layout (earlier or later); repeat in order")
    parser.add_argument("--output-dir", default="data/staged/blinkfire")
    parser.add_argument("--manifest", default="data/staged/blinkfire/pull_manifest.json")
    parser.add_argument("--taxonomy", default="data/reference/property_taxonomy.csv")
    args = parser.parse_args()
    ingest_blinkfire(args.source, args.output_dir, args.manifest, args.taxonomy, args.supplement)
