"""Experimental bridge from sponsorship evidence to gated royalty relief.

This path deliberately does not replace C-INDEX, C-EXPOSURE, or C-ROI. It
combines the confirmed impressions/views exposure, observational survey lift,
and canonical Brand Index context. Monetary output is produced only when every
required valuation assumption is explicitly configured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import yaml

from srmp.exposure.adstock import geometric_adstock
from srmp.roi.royalty_schedule import resolve_royalty_schedule


VALUATION_INPUTS = (
    "delta_index_attrib",
    "royalty_bps_per_index_point",
    "brand_attributable_revenue",
    "sponsorship_fee",
    "discount_rate",
    "persistence_years",
)


def _load_parquet(path: str) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Experimental monetization input unavailable: {source}")
    return pq.read_table(source).to_pandas()


def _write_frame(frame: pd.DataFrame, stem: Path, schema: pa.Schema | None = None) -> None:
    table = (
        pa.Table.from_pandas(frame, schema=schema, preserve_index=False)
        if len(frame) or schema is None
        else pa.Table.from_pylist([], schema=schema)
    )
    pq.write_table(table, stem.with_suffix(".parquet"))
    pacsv.write_csv(table, stem.with_suffix(".csv"))


def _assumptions_hash(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_adstock_exposure(exposure: pd.DataFrame, delta: float) -> pd.DataFrame:
    """Complete each property-week grid and compute scenario adstock."""
    if not 0 < delta < 1:
        raise ValueError("Experimental exposure delta must be strictly between zero and one.")
    required = {"property_id", "week", "impressions", "views", "days_observed"}
    missing = sorted(required - set(exposure.columns))
    if missing:
        raise ValueError(f"Experimental exposure missing columns: {missing}")

    exposure = exposure.copy()
    exposure["week"] = pd.to_datetime(exposure["week"])
    start, end = exposure["week"].min(), exposure["week"].max()
    grid = pd.date_range(start, end, freq="W-MON")
    completed: list[pd.DataFrame] = []
    for property_id, rows in exposure.groupby("property_id", sort=True):
        rows = rows.sort_values("week").set_index("week")
        observed_weeks = set(rows.index)
        rows = rows.reindex(grid)
        rows["property_id"] = property_id
        rows["impressions"] = rows["impressions"].fillna(0).astype("int64")
        rows["views"] = rows["views"].fillna(0).astype("int64")
        rows["days_observed"] = rows["days_observed"].fillna(0).astype("int64")
        rows["view_rate"] = np.where(
            rows["impressions"] > 0, rows["views"] / rows["impressions"], np.nan
        )
        rows["source_row_present"] = rows.index.isin(observed_weeks)
        rows["adstock_impressions"] = geometric_adstock(rows["impressions"], delta)
        rows["delta_used"] = delta
        rows["measurement_scope"] = "impressions_views_only_experimental"
        completed.append(rows.reset_index(names="week"))
    return pd.concat(completed, ignore_index=True).sort_values(["week", "property_id"])


def _asof_value(rows: pd.DataFrame, date: pd.Timestamp, column: str) -> float | None:
    eligible = rows[rows["week"] <= date]
    if eligible.empty:
        return None
    return float(eligible.iloc[-1][column])


def build_evidence_panel(
    lift: pd.DataFrame,
    adstock: pd.DataFrame,
    brand_index: pd.DataFrame,
    stages: tuple[str, ...],
    comparable_scale: str,
    trailing_weeks: int,
) -> pd.DataFrame:
    """Join survey lift to trailing exposure and Brand Index context."""
    lift = lift[lift["funnel_stage"].isin(stages)].copy()
    grouped: list[dict[str, Any]] = []
    for (period, property_id), rows in lift.groupby(["reported_period", "property_id"]):
        by_stage = rows.set_index("funnel_stage")
        if not set(stages).issubset(by_stage.index):
            continue
        scale_versions = sorted(set(by_stage.loc[list(stages), "scale_version"]))
        grouped.append({
            "reported_period": period,
            "property_id": property_id,
            **{f"{stage}_lift": float(by_stage.loc[stage, "lift"]) for stage in stages},
            "funnel_lift_composite": float(by_stage.loc[list(stages), "lift"].mean()),
            "scale_version": scale_versions[0] if len(scale_versions) == 1 else "mixed",
        })

    brand_index = brand_index.copy()
    brand_index["week"] = pd.to_datetime(brand_index["week"])
    brand_index = brand_index.sort_values("week")
    adstock = adstock.copy().sort_values(["property_id", "week"])
    output: list[dict[str, Any]] = []
    for row in grouped:
        month_end = pd.Period(row["reported_period"], freq="M").end_time.normalize()
        property_exposure = adstock[adstock["property_id"].eq(row["property_id"])]
        aligned = property_exposure[property_exposure["week"] <= month_end]
        has_exposure = not aligned.empty
        aligned_week = aligned.iloc[-1]["week"] if has_exposure else pd.NaT
        if has_exposure:
            window_start = aligned_week - pd.Timedelta(weeks=trailing_weeks - 1)
            window = property_exposure[
                property_exposure["week"].between(window_start, aligned_week)
            ]
            trailing_impressions = float(window["impressions"].sum())
            trailing_adstock_mean = float(window["adstock_impressions"].mean())
            adstock_at_wave = float(aligned.iloc[-1]["adstock_impressions"])
        else:
            trailing_impressions = trailing_adstock_mean = adstock_at_wave = np.nan

        index_level = _asof_value(brand_index, month_end, "index_level")
        prior_level = _asof_value(
            brand_index, month_end - pd.Timedelta(weeks=trailing_weeks), "index_level"
        )
        output.append({
            **row,
            "alignment_date": month_end,
            "aligned_exposure_week": aligned_week,
            "fieldwork_date_status": "reported_month_end_proxy",
            f"trailing_{trailing_weeks}w_impressions": trailing_impressions,
            f"trailing_{trailing_weeks}w_adstock_mean": trailing_adstock_mean,
            "adstock_at_wave": adstock_at_wave,
            "brand_index_level_context": index_level,
            f"brand_index_change_{trailing_weeks}w": (
                index_level - prior_level
                if index_level is not None and prior_level is not None else np.nan
            ),
            "model_eligible": bool(has_exposure and row["scale_version"] == comparable_scale),
            "is_causal_effect": False,
        })
    return pd.DataFrame(output).sort_values(["reported_period", "property_id"])


def build_property_allocation(
    panel: pd.DataFrame,
    adstock: pd.DataFrame,
) -> pd.DataFrame:
    """Create an exposure-times-lift allocation scenario, never an effect estimate."""
    eligible = panel[panel["model_eligible"]].copy()
    adstock_columns = [
        column for column in eligible.columns
        if column.startswith("trailing_") and column.endswith("w_adstock_mean")
    ]
    if len(adstock_columns) != 1:
        raise ValueError("Experimental panel must contain one trailing adstock mean column.")
    wave_adstock = adstock_columns[0]
    # Score each survey wave only from exposure observed before that wave. The
    # property mean avoids rewarding a property merely for having more surveys.
    eligible["wave_allocation_evidence_score"] = (
        eligible[wave_adstock]
        * eligible["funnel_lift_composite"].clip(lower=0)
    )
    lift_summary = eligible.groupby("property_id").agg(
        survey_waves=("reported_period", "nunique"),
        mean_funnel_lift=("funnel_lift_composite", "mean"),
        min_funnel_lift=("funnel_lift_composite", "min"),
        max_funnel_lift=("funnel_lift_composite", "max"),
        mean_trailing_adstock=(wave_adstock, "mean"),
        allocation_evidence_score=("wave_allocation_evidence_score", "mean"),
    )
    exposure_summary = adstock.groupby("property_id").agg(
        total_impressions=("impressions", "sum"),
        cumulative_adstock_impressions=("adstock_impressions", "sum"),
    )
    allocation = lift_summary.join(exposure_summary, how="left").reset_index()
    total = float(allocation["allocation_evidence_score"].sum())
    if total <= 0:
        raise ValueError("Experimental allocation has no positive exposure-times-lift evidence.")
    allocation["allocation_share"] = allocation["allocation_evidence_score"] / total
    allocation["allocation_role"] = "scenario_only_not_causal_attribution"
    return allocation.sort_values("allocation_share", ascending=False).reset_index(drop=True)


def calculate_valuation(
    valuation: dict[str, Any],
    allocation: pd.DataFrame,
    assumptions_hash: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Calculate royalty relief only when all explicit inputs are present."""
    missing = [name for name in VALUATION_INPUTS if valuation.get(name) is None]
    columns = [
        "scenario_id", "property_id", "delta_index_attrib", "delta_royalty_bps",
        "incremental_value", "sponsorship_fee", "value_multiple", "net_roi",
        "allocation_share", "assumptions_hash",
    ]
    if missing:
        return pd.DataFrame(columns=columns), missing

    delta_index = float(valuation["delta_index_attrib"])
    bps = delta_index * float(valuation["royalty_bps_per_index_point"])
    revenue = float(valuation["brand_attributable_revenue"])
    fee = float(valuation["sponsorship_fee"])
    discount = float(valuation["discount_rate"])
    years = int(valuation["persistence_years"])
    if fee <= 0 or revenue < 0 or discount <= -1 or years < 1:
        raise ValueError("Experimental valuation assumptions are outside valid bounds.")
    annual_value = revenue * bps / 10_000.0
    incremental_value = sum(annual_value / ((1 + discount) ** year) for year in range(1, years + 1))
    total_row = {
        "scenario_id": valuation.get("scenario_id", "experimental_base"),
        "property_id": "TOTAL",
        "delta_index_attrib": delta_index,
        "delta_royalty_bps": bps,
        "incremental_value": incremental_value,
        "sponsorship_fee": fee,
        "value_multiple": incremental_value / fee,
        "net_roi": (incremental_value - fee) / fee,
        "allocation_share": 1.0,
        "assumptions_hash": assumptions_hash,
    }
    rows = [total_row]
    for item in allocation.to_dict("records"):
        share = float(item["allocation_share"])
        rows.append({
            **total_row,
            "property_id": item["property_id"],
            "delta_index_attrib": delta_index * share,
            "delta_royalty_bps": bps * share,
            "incremental_value": incremental_value * share,
            "sponsorship_fee": np.nan,
            "value_multiple": np.nan,
            "net_roi": np.nan,
            "allocation_share": share,
        })
    return pd.DataFrame(rows, columns=columns), []


def build_experiment(
    config_path: str = "config/experiments/sponsorship_monetization_v1.yaml",
    output_dir: str = "data/curated/experimental/sponsorship_monetization_v1",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    paths = config["inputs"]
    exposure = _load_parquet(paths["exposure"])
    lift = _load_parquet(paths["survey_lift"])
    brand_index = _load_parquet(paths["brand_index"])
    delta = float(config["exposure"]["delta"])
    trailing_weeks = int(config["alignment"]["trailing_weeks"])

    adstock = build_adstock_exposure(exposure, delta)
    panel = build_evidence_panel(
        lift, adstock, brand_index,
        tuple(config["survey"]["stages"]),
        config["survey"]["comparable_scale_version"],
        trailing_weeks,
    )
    allocation = build_property_allocation(panel, adstock)
    valuation = dict(config["valuation"])
    counterfactual_path = Path(valuation["counterfactual_manifest"])
    counterfactual = (
        json.loads(counterfactual_path.read_text(encoding="utf-8"))
        if counterfactual_path.exists() else None
    )
    counterfactual_gate = {
        "status": "blocked_counterfactual_manifest_missing",
        "path": str(counterfactual_path),
        "candidate_delta_index_attrib": None,
        "used_for_valuation": False,
    }
    if counterfactual is not None:
        # Headline total sponsorship effect on the Brand Index (ADR-0038, ADR-0040).
        candidate = counterfactual["total_effect"]["lift_index_points"]
        accepted = bool(counterfactual["passes_primary_test"])
        use_candidate = bool(valuation.get("use_counterfactual_candidate"))
        counterfactual_gate = {
            "status": "passes_primary_placebo_test" if accepted else "does_not_pass_primary_placebo_test",
            "path": str(counterfactual_path),
            "candidate_delta_index_attrib": candidate,
            "donor_placebo_p_value": counterfactual["primary"]["p_value"],
            "use_counterfactual_candidate": use_candidate,
            "used_for_valuation": bool(accepted and use_candidate),
        }
        if accepted and use_candidate and valuation.get("delta_index_attrib") is None:
            valuation["delta_index_attrib"] = candidate

    reference_index = valuation.get("royalty_reference_index")
    if reference_index is None and counterfactual is not None:
        reference_index = counterfactual["total_effect"]["synthetic_post_mean_index"]
    royalty_resolution = resolve_royalty_schedule(
        valuation["royalty_schedule_path"], reference_index
    )
    if (
        valuation.get("royalty_bps_per_index_point") is None
        and royalty_resolution.get("royalty_bps_per_index_point") is not None
    ):
        valuation["royalty_bps_per_index_point"] = royalty_resolution["royalty_bps_per_index_point"]

    assumptions_hash = _assumptions_hash(config)
    valuation_rows, missing = calculate_valuation(
        valuation, allocation, assumptions_hash
    )

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write_frame(adstock, target / "exposure_adstock_weekly")
    _write_frame(panel, target / "funnel_lift_exposure_panel")
    _write_frame(allocation, target / "property_allocation_scenario")
    valuation_schema = pa.schema([
        ("scenario_id", pa.string()), ("property_id", pa.string()),
        ("delta_index_attrib", pa.float64()), ("delta_royalty_bps", pa.float64()),
        ("incremental_value", pa.float64()), ("sponsorship_fee", pa.float64()),
        ("value_multiple", pa.float64()), ("net_roi", pa.float64()),
        ("allocation_share", pa.float64()), ("assumptions_hash", pa.string()),
    ])
    _write_frame(valuation_rows, target / "monetization_scenarios", valuation_schema)

    eligible = panel[panel["model_eligible"]]
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": "valuation_ready" if not missing else "attribution_bridge_built_valuation_blocked",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_contracts_replaced": [],
        "purpose": "Connect property exposure and observational funnel lift to an allocation scenario, then conditionally apply royalty relief.",
        "inputs": {
            name: {"path": path, "sha256": _file_sha256(path)}
            for name, path in paths.items()
        },
        "outputs": {
            "exposure_adstock_weekly_rows": int(len(adstock)),
            "funnel_lift_exposure_panel_rows": int(len(panel)),
            "model_eligible_panel_rows": int(len(eligible)),
            "property_allocation_rows": int(len(allocation)),
            "monetization_rows": int(len(valuation_rows)),
        },
        "method": {
            "adstock_delta": delta,
            "delta_status": config["exposure"]["delta_status"],
            "survey_stages": config["survey"]["stages"],
            "excluded_survey_stage": "awareness (mechanical by segment definition)",
            "fieldwork_alignment": "reported month end proxy; exact dates unavailable",
            "allocation_formula": "property mean across survey waves of trailing_adstock_mean * positive_appeal_purchase_intent_lift",
            "allocation_interpretation": "scenario share, not causal effect and not a Brand Index weight",
        },
        "association_model": {
            "status": "not_estimable_with_current_sample",
            "eligible_observations": int(len(eligible)),
            "reason": "Only five comparable exposure-linked property-wave observations; no credible fixed-effects exposure-lift regression.",
        },
        "valuation_gate": {
            "status": "open" if not missing else "blocked_missing_explicit_inputs",
            "missing_inputs": missing,
            "rule": "No monetary values are emitted until all required inputs are explicit.",
        },
        "counterfactual_gate": counterfactual_gate,
        "royalty_schedule_gate": royalty_resolution,
        "assumptions_hash": assumptions_hash,
        "caveats": [
            "Aware-minus-unaware lift is observational and affected by self-selection.",
            "Blinkfire covers confirmed impressions/views only; broadcast exposure is absent.",
            "The 2024 survey scale is retained descriptively but excluded from the comparable panel.",
            "The property allocation distributes an independently estimated total effect; it cannot create that effect.",
        ],
    }
    (target / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/sponsorship_monetization_v1.yaml")
    parser.add_argument("--output-dir", default="data/curated/experimental/sponsorship_monetization_v1")
    args = parser.parse_args()
    build_experiment(args.config, args.output_dir)
