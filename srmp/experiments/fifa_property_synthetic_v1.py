"""Retired Brand-Index path; property co-search mechanism diagnostic only.

F1, MotoGP, and Ducati are sponsored properties, not untreated brands. Their
co-branded search series must never be used as Lenovo's no-FIFA Brand Index
counterfactual or as an input to valuation.
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

from srmp.experiments.sponsorship_counterfactual_v1 import (
    _donor_placebos,
    _fit_simplex,
    _monday,
    _rmspe,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(frame: pd.DataFrame, stem: Path) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, stem.with_suffix(".parquet"))
    pacsv.write_csv(table, stem.with_suffix(".csv"))


def _load_parquet(path: str) -> pd.DataFrame:
    return pq.read_table(path).to_pandas()


def _aggregate_exposure(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    exposure = _load_parquet(config["inputs"]["exposure"])
    exposure["week"] = pd.to_datetime(exposure["week"])
    taxonomy = pd.read_csv(config["inputs"]["property_taxonomy"])
    group = config["treated_unit"]["exposure_property_group"]
    fifa_ids = sorted(taxonomy.loc[taxonomy["property_group"].eq(group), "property_id"])
    fifa = exposure[exposure["property_id"].isin(fifa_ids)].groupby("week", as_index=False).agg(
        impressions=("impressions", "sum"),
        views=("views", "sum"),
        adstock_impressions=("adstock_impressions", "sum"),
        contributing_property_rows=("property_id", "size"),
        positive_exposure_properties=("impressions", lambda values: int((values > 0).sum())),
    )
    fifa.insert(0, "property_id", "fifa_aggregate")
    fifa["view_rate"] = np.where(
        fifa["impressions"] > 0, fifa["views"] / fifa["impressions"], np.nan
    )
    return fifa, fifa_ids


def _outcome_panel(config: dict[str, Any], fill_value: float) -> pd.DataFrame:
    trends = _load_parquet(config["inputs"]["trends"])
    trends["week"] = _monday(trends["week"])
    query_ids = [config["treated_unit"]["primary_outcome_query"]] + [
        row["outcome_query"] for row in config["donor_units"]
    ]
    secondary = config["treated_unit"].get("secondary_post_only_query")
    if secondary:
        query_ids.append(secondary)
    panel = trends[trends["query_id"].isin(query_ids)].pivot(
        index="week", columns="query_id", values="interest_mean"
    ).sort_index()
    return panel.reindex(columns=query_ids).fillna(float(fill_value))


def _estimate(
    config: dict[str, Any],
    fifa_exposure: pd.DataFrame,
    fill_value: float,
) -> dict[str, Any]:
    panel = _outcome_panel(config, fill_value)
    treated_query = config["treated_unit"]["primary_outcome_query"]
    donor_queries = [row["outcome_query"] for row in config["donor_units"]]
    treatment = pd.Timestamp(config["treatment"]["first_full_post_week"])
    pre = pd.Series(panel.index < treatment, index=panel.index)
    post = pd.Series(panel.index >= treatment, index=panel.index)
    fit = _fit_simplex(panel[treated_query], panel[donor_queries], pre)
    gap = fit["target_z"] - fit["synthetic_z"]
    pre_rmspe, post_rmspe = _rmspe(gap[pre]), _rmspe(gap[post])
    placebo = _donor_placebos(panel[donor_queries], pre, post)
    ratio = post_rmspe / pre_rmspe
    placebo_p = float(
        (1 + (placebo["post_pre_rmspe_ratio"] >= ratio).sum())
        / (1 + len(placebo))
    )
    exposure = fifa_exposure.set_index("week")[["adstock_impressions"]]
    paired = pd.DataFrame({"gap_z": gap}).join(exposure, how="inner")
    paired = paired[paired.index >= treatment]
    total_adstock = float(paired["adstock_impressions"].sum())
    weighted_gap = float(
        (paired["gap_z"] * paired["adstock_impressions"]).sum() / total_adstock
    )
    return {
        "panel": panel,
        "fit": fit,
        "gap": gap,
        "pre": pre,
        "post": post,
        "placebo": placebo,
        "pre_rmspe_z": pre_rmspe,
        "post_rmspe_z": post_rmspe,
        "post_pre_rmspe_ratio": ratio,
        "placebo_p_value": placebo_p,
        "all_post_mean_gap_z": float(gap[post].mean()),
        "exposure_weighted_gap_z": weighted_gap,
    }


def build_fifa_property_synthetic(
    config_path: str = "config/experiments/fifa_property_synthetic_v1.yaml",
    output_dir: str = "data/curated/experimental/fifa_property_synthetic_v1",
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    fifa_exposure, fifa_ids = _aggregate_exposure(config)
    base_fill = float(config["suppression"]["base_fill_value"])
    result = _estimate(config, fifa_exposure, base_fill)

    weekly = pd.DataFrame({
        "week": result["panel"].index,
        "actual_fifa_cobrand_z": result["fit"]["target_z"].to_numpy(),
        "synthetic_donor_z": result["fit"]["synthetic_z"].to_numpy(),
        "property_search_gap_z": result["gap"].to_numpy(),
        "period": np.where(result["pre"], "pre", "post"),
        "fcwc_cobrand_interest_secondary": result["panel"][
            config["treated_unit"]["secondary_post_only_query"]
        ].to_numpy(),
    }).merge(
        fifa_exposure[["week", "impressions", "views", "adstock_impressions"]],
        on="week", how="left",
    )
    weights = pd.DataFrame({
        "outcome_query": list(result["fit"]["weights"]),
        "weight": list(result["fit"]["weights"].values()),
    }).merge(
        pd.DataFrame(config["donor_units"]), on="outcome_query", how="left"
    ).sort_values("weight", ascending=False)
    sensitivity_rows = []
    for fill in config["suppression"]["sensitivity_fill_values"]:
        alternate = _estimate(config, fifa_exposure, float(fill))
        sensitivity_rows.append({
            "suppressed_value_fill": float(fill),
            "pre_rmspe_z": alternate["pre_rmspe_z"],
            "all_post_mean_gap_z": alternate["all_post_mean_gap_z"],
            "exposure_weighted_gap_z": alternate["exposure_weighted_gap_z"],
            "placebo_p_value": alternate["placebo_p_value"],
        })
    sensitivity = pd.DataFrame(sensitivity_rows)

    _write(fifa_exposure, target / "fifa_aggregate_exposure_weekly")
    _write(weekly, target / "fifa_property_outcome_weekly")
    _write(weights, target / "synthetic_donor_weights")
    _write(result["placebo"], target / "donor_placebos")
    _write(sensitivity, target / "suppression_sensitivity")

    screen = config["quality_screen"]
    donor_count = len(config["donor_units"])
    checks = {
        "pre_fit_pass": result["pre_rmspe_z"] <= float(screen["maximum_pre_rmspe_z"]),
        "donor_pool_pass": donor_count >= int(screen["target_minimum_donors"]),
        "placebo_pass": result["placebo_p_value"] <= float(screen["maximum_placebo_p_value"]),
    }
    quality_status = (
        "mechanism_candidate_low_confidence"
        if not all(checks.values())
        else "mechanism_candidate_passes_screen"
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "quality_status": quality_status,
        "permitted_use": "mechanism_diagnostic_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_contracts_replaced": [],
        "treated_exposure_unit": {
            "property_id": "fifa_aggregate",
            "included_property_ids": fifa_ids,
            "property_count": len(fifa_ids),
            "total_impressions": int(fifa_exposure["impressions"].sum()),
            "total_views": int(fifa_exposure["views"].sum()),
        },
        "outcome": {
            "primary": "Lenovo FIFA co-branded Google Trends, pre-standardized",
            "secondary": "Lenovo Club World Cup search; post-only diagnostic because pre variation is insufficient",
            "unit": "pre-treatment standard deviations of property-attributed search salience",
            "not": ["Brand Index points", "causal sponsorship effect", "monetary value"],
        },
        "donor_pool": config["donor_units"],
        "donor_weights": {key: float(value) for key, value in result["fit"]["weights"].items()},
        "diagnostics": {
            "pre_rmspe_z": result["pre_rmspe_z"],
            "post_rmspe_z": result["post_rmspe_z"],
            "post_pre_rmspe_ratio": result["post_pre_rmspe_ratio"],
            "placebo_p_value": result["placebo_p_value"],
            "placebo_resolution_floor": 1.0 / (donor_count + 1),
            **checks,
        },
        "candidate": {
            "all_post_mean_gap_z": result["all_post_mean_gap_z"],
            "fifa_exposure_weighted_gap_z": result["exposure_weighted_gap_z"],
            "suppression_sensitivity_range": [
                float(sensitivity["exposure_weighted_gap_z"].min()),
                float(sensitivity["exposure_weighted_gap_z"].max()),
            ],
        },
        "inputs": {
            name: {"path": path, "sha256": _sha256(Path(path))}
            for name, path in config["inputs"].items()
        },
        "limitations": [
            "Only F1, MotoGP and Ducati currently have both Blinkfire exposure and matching Lenovo co-brand search outcomes.",
            "Google Trends suppression is interval-censored; base fill 0.5 is bracketed by 0 and 1 sensitivity runs.",
            "The pre-period synthetic fit is weak and the three-donor placebo test cannot attain p below 0.25.",
            "The result measures property-attributed search salience and cannot be inserted into the Brand Index or monetization.",
        ],
    }
    (target / "experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/fifa_property_synthetic_v1.yaml")
    parser.add_argument("--output-dir", default="data/curated/experimental/fifa_property_synthetic_v1")
    args = parser.parse_args()
    build_fifa_property_synthetic(args.config, args.output_dir)
