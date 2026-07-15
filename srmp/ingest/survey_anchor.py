"""Canonical D1 anchor validation and safe descriptive survey-wave outputs."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

# The client survey measures a marketing funnel, not brand pillars (see base.yaml).
FUNNEL_STAGES = ("awareness", "engagement", "appeal", "consideration", "purchase_intent")
# composite is optional: it was defined as a PCA roll-up of pillars, which no longer
# exists; the anchor now carries the funnel-stage scores and an optional roll-up.
ANCHOR_COLUMNS = (
    "wave_id", "fieldwork_start", "fieldwork_end", *FUNNEL_STAGES,
    "questionnaire_version", "comparability_status", "weighting_scheme",
)
MONTHS = {name: number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"), 1)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_table(rows: list[dict[str, Any]], csv_path: Path, parquet_path: Path) -> None:
    table = pa.Table.from_pylist(rows)
    pacsv.write_csv(table, csv_path)
    pq.write_table(table, parquet_path)


def ingest_survey_anchor(source_path: str, output_dir: str, manifest_path: str) -> None:
    """Validate an approved wave-level anchor; never infer missing fields."""
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"D1 anchor unavailable: {source}")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in ANCHOR_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"D1 anchor contract violation: missing columns {missing}")
        source_rows = list(reader)
    if not source_rows:
        raise ValueError("D1 anchor contract violation: no survey waves")

    output_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, row in enumerate(source_rows, 2):
        wave_id = row["wave_id"].strip()
        if not wave_id or wave_id in seen:
            raise ValueError(f"D1 anchor contract violation at row {number}: blank/duplicate wave_id")
        seen.add(wave_id)
        start, end = date.fromisoformat(row["fieldwork_start"]), date.fromisoformat(row["fieldwork_end"])
        if end < start:
            raise ValueError(f"D1 anchor contract violation at row {number}: fieldwork_end before start")
        scores = {column: float(row[column]) for column in FUNNEL_STAGES}
        if "composite" in (reader.fieldnames or []) and row.get("composite", "").strip():
            scores["composite"] = float(row["composite"])  # optional overall roll-up
        if any(not row[column].strip() for column in ("questionnaire_version", "comparability_status", "weighting_scheme")):
            raise ValueError(f"D1 anchor contract violation at row {number}: incomplete metadata")
        midpoint = datetime.combine(start, datetime.min.time()) + (
            datetime.combine(end, datetime.min.time()) - datetime.combine(start, datetime.min.time())
        ) / 2
        output_rows.append({
            "wave_id": wave_id, "fieldwork_start": start, "fieldwork_end": end,
            "fieldwork_midpoint": midpoint, **scores,
            "questionnaire_version": row["questionnaire_version"].strip(),
            "comparability_status": row["comparability_status"].strip(),
            "weighting_scheme": row["weighting_scheme"].strip(),
        })

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_table(output_rows, target / "brand_index_wave_anchor.csv", target / "brand_index_wave_anchor.parquet")
    manifest = {
        "source": str(source), "source_sha256": _sha256(source),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "canonical_anchor_available", "row_count": len(output_rows),
    }
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def build_segmented_wave_metrics(crosstabs_path: str, output_dir: str) -> dict[str, Any]:
    """Extract safe descriptive wave metrics without creating a canonical anchor."""
    source = Path(crosstabs_path)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["table_id"], row["segment"]), []).append(row)

    output: list[dict[str, Any]] = []
    for (table_id, segment), group in groups.items():
        first = group[0]
        candidates = {
            "brand_awareness": ("Brand Aware - Lenovo FWC", "Q17b Brand Aware Lenovo", "Q17c CWC Brand Aware Lenovo"),
            "appeal": ("T4B", "Like + Love"),
            "purchase_intent": ("T4B", "Next Year NET"),
        }[first["metric"]]
        selected = next((row for label in candidates for row in group
                         if row["statistic"] == "Column %" and row["response_label"] == label), None)
        if selected is None:
            raise ValueError(f"D1 descriptive metric missing for {table_id}/{segment}")
        match = re.search(r"(" + "|".join(MONTHS) + r")\s+(\d{4})", first["filter_text"])
        period = f"{match.group(2)}-{MONTHS[match.group(1)]:02d}" if match else ""
        definition = selected["response_label"]
        property_id = {"cwc": "fcwc"}.get(first["property_label"].lower(), first["property_label"].lower())
        output.append({
            "reported_period": period, "wave_label": first["filter_text"],
            "property_id": property_id, "segment": segment,
            "metric": first["metric"], "positive_definition": definition,
            "positive_share": float(selected["value"]),
            "scale_version": ("awareness_binary" if first["metric"] == "brand_awareness" else
                              ("2024_0_10" if definition == "T4B" else "2025plus_categorical")),
            "source_table_id": table_id, "source_sha256": first["source_sha256"],
            "canonical_anchor_eligible": False,
        })
    output.sort(key=lambda row: (row["reported_period"], row["property_id"], row["metric"], row["segment"]))
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_table(output, target / "segmented_perception_wave_metrics.csv",
                 target / "segmented_perception_wave_metrics.parquet")
    status = {
        "status": "blocked_missing_approved_wave_anchor", "canonical_anchor_created": False,
        "descriptive_rows": len(output),
        "reason": "Available outcomes are conditioned on sponsorship awareness and response scales change after 2024.",
        "required_input": list(ANCHOR_COLUMNS),
    }
    (target / "anchor_status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def _quarter_dates(period_label: str) -> tuple[date, date, date]:
    """Map a GWI 'Q<n> <year> (Survey Waves)' label to quarter start/end/midpoint."""
    match = re.match(r"Q([1-4])\s+(\d{4})", period_label)
    if match is None:
        raise ValueError(f"D1 constructed anchor: unparseable GWI period '{period_label}'")
    quarter, year = int(match.group(1)), int(match.group(2))
    start = date(year, (quarter - 1) * 3 + 1, 1)
    end_month = quarter * 3
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return start, end, start + timedelta(days=(end - start).days // 2)


def construct_wave_anchor(gwi_candidates_path: str, output_dir: str) -> dict[str, Any]:
    """Build a NON-CANONICAL funnel anchor from the client's GWI waves (ADR-0011).

    The GWI export gives population-level quarterly ``engagement`` and
    ``consideration``. Those two funnel stages are populated; ``awareness``,
    ``appeal`` and ``purchase_intent`` stay null because the only source for them
    (the consumer-research crosstabs) is sponsorship-segmented and scale-broken,
    not a population wave score. Every row is ``canonical_anchor_eligible: false``
    and a deviations register records each departure from the anchor contract.
    """
    source = Path(gwi_candidates_path)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_wave: dict[tuple[date, date, date, str], dict[str, float]] = {}
    for row in rows:
        start, end, midpoint = _quarter_dates(row["period_label"])
        wave_id = f"gwi_{start.year}Q{(start.month - 1) // 3 + 1}"
        by_wave.setdefault((start, end, midpoint, wave_id), {})[row["proxy_construct"]] = float(row["value"])

    anchor_rows: list[dict[str, Any]] = []
    for (start, end, midpoint, wave_id), constructs in sorted(by_wave.items()):
        anchor_rows.append({
            "wave_id": wave_id, "source": "gwi",
            "fieldwork_start": start, "fieldwork_end": end, "fieldwork_midpoint": midpoint,
            "awareness": None, "engagement": constructs.get("engagement"),
            "appeal": None, "consideration": constructs.get("consideration"),
            "purchase_intent": None,
            "questionnaire_version": "gwi_core_tech_brands",
            "comparability_status": "gwi_consistent_quarterly",
            "weighting_scheme": "gwi_syndicated_global",
            "canonical_anchor_eligible": False,
        })

    schema = pa.schema([
        ("wave_id", pa.string()), ("source", pa.string()),
        ("fieldwork_start", pa.date32()), ("fieldwork_end", pa.date32()),
        ("fieldwork_midpoint", pa.date32()),
        ("awareness", pa.float64()), ("engagement", pa.float64()), ("appeal", pa.float64()),
        ("consideration", pa.float64()), ("purchase_intent", pa.float64()),
        ("questionnaire_version", pa.string()), ("comparability_status", pa.string()),
        ("weighting_scheme", pa.string()), ("canonical_anchor_eligible", pa.bool_()),
    ])
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(anchor_rows, schema=schema)
    pacsv.write_csv(table, target / "brand_index_wave_anchor_constructed.csv")
    pq.write_table(table, target / "brand_index_wave_anchor_constructed.parquet")

    populated = [stage for stage in FUNNEL_STAGES
                 if any(row[stage] is not None for row in anchor_rows)]
    deviations = [
        "Not the client-approved analytical extract: canonical_anchor_eligible=false for every row.",
        "composite absent: the funnel is an ordered sequence, not a PCA factor structure (ADR-0011).",
        f"Only {', '.join(populated)} are populated; awareness/appeal/purchase_intent are null because "
        "their only source (consumer-research crosstabs) is sponsorship-segmented and scale-broken "
        "(2024->2025), not a population wave score.",
        "fieldwork dates approximated as calendar-quarter boundaries with the midpoint as the anchor "
        "point; GWI fields continuously and does not publish exact wave dates.",
        "GWI is syndicated global; its geo/weighting composition need not match a Lenovo-commissioned "
        "national extract.",
    ]
    status = {
        "status": "constructed_noncanonical_anchor_available",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(source), "source_sha256": _sha256(source),
        "canonical_anchor_created": False, "funnel_stages": list(FUNNEL_STAGES),
        "populated_stages": populated, "wave_count": len(anchor_rows),
        "wave_span": [anchor_rows[0]["wave_id"], anchor_rows[-1]["wave_id"]] if anchor_rows else [],
        "deviations_from_contract": deviations,
        "still_required_for_canonical": list(ANCHOR_COLUMNS),
    }
    (target / "constructed_anchor_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


_LIFT_STAGE = {"brand_awareness": "awareness", "appeal": "appeal", "purchase_intent": "purchase_intent"}


def build_sponsorship_lift(segmented_metrics_path: str, output_dir: str) -> dict[str, Any]:
    """Companion to the index: the sponsorship-associated funnel lift (ADR-0012).

    For each funnel stage x property x wave, ``lift = aware - unaware`` — how much
    higher Lenovo's awareness/appeal/purchase_intent runs among respondents who
    know about the FIFA sponsorship. Differencing cancels the wave's response
    scale, so the lift is comparable within a wave even where the levels are not.

    OBSERVATIONAL, NOT CAUSAL: sponsorship-aware respondents self-select, so the
    gap upper-bounds the true effect; the causal estimate is the job of the L4b
    panel / event study / SCM identification stack (W-04). This artifact is a
    companion signal and is never folded into the population brand-index anchor.
    """
    source = Path(segmented_metrics_path)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    paired: dict[tuple[str, str, str, str], dict[str, float]] = {}
    for row in rows:
        segment = "unaware" if row["segment"].endswith("Unaware") else "aware"
        key = (row["reported_period"], row["property_id"], row["metric"], row["scale_version"])
        paired.setdefault(key, {})[segment] = float(row["positive_share"])

    lift_rows: list[dict[str, Any]] = []
    for (period, property_id, metric, scale_version), pair in sorted(paired.items()):
        if "aware" not in pair or "unaware" not in pair:
            continue
        lift_rows.append({
            "reported_period": period, "property_id": property_id,
            "funnel_stage": _LIFT_STAGE.get(metric, metric),
            "aware": pair["aware"], "unaware": pair["unaware"],
            "lift": round(pair["aware"] - pair["unaware"], 6),
            "scale_version": scale_version,
            "measure_type": "observational_sponsorship_awareness_gap",
            "is_causal_effect": False, "canonical_anchor_eligible": False,
        })

    schema = pa.schema([
        ("reported_period", pa.string()), ("property_id", pa.string()),
        ("funnel_stage", pa.string()), ("aware", pa.float64()), ("unaware", pa.float64()),
        ("lift", pa.float64()), ("scale_version", pa.string()),
        ("measure_type", pa.string()), ("is_causal_effect", pa.bool_()),
        ("canonical_anchor_eligible", pa.bool_()),
    ])
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(lift_rows, schema=schema)
    pacsv.write_csv(table, target / "sponsorship_funnel_lift.csv")
    pq.write_table(table, target / "sponsorship_funnel_lift.parquet")
    status = {
        "status": "sponsorship_lift_available",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(lift_rows),
        "funnel_stages": sorted({row["funnel_stage"] for row in lift_rows}),
        "properties": sorted({row["property_id"] for row in lift_rows}),
        "periods": sorted({row["reported_period"] for row in lift_rows}),
        "interpretation": "aware-minus-unaware gap in each funnel stage; companion to the "
                          "GWI population index, NOT part of its anchor.",
        "causal_caveat": "Observational: sponsorship-aware respondents self-select, so the gap "
                         "upper-bounds the true effect. Causal estimation is deferred to the "
                         "L4b panel / event study / SCM stack (W-04).",
    }
    (target / "sponsorship_lift_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosstabs", default="data/staged/survey/consumer_research_crosstabs.csv")
    parser.add_argument("--gwi-candidates", default="data/staged/survey/gwi_lenovo_proxy_candidates.csv")
    parser.add_argument("--segmented", default="data/staged/survey/segmented_perception_wave_metrics.csv")
    parser.add_argument("--output-dir", default="data/staged/survey")
    args = parser.parse_args()
    build_segmented_wave_metrics(args.crosstabs, args.output_dir)
    construct_wave_anchor(args.gwi_candidates, args.output_dir)
    build_sponsorship_lift(args.segmented, args.output_dir)
