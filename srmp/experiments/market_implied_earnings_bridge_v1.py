"""Positive planning bridge from BI innovations to earnings-equivalent value."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from srmp.experiments.brand_financial_bridge_v1 import _sha256, _write


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_market_implied_earnings_bridge(
    config_path: str = (
        "config/experiments/market_implied_earnings_bridge_v1.yaml"
    ),
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    stock = _read_json(config["inputs"]["stock_response_manifest"])
    horizon = int(config["calibration"]["selected_horizon_weeks"])
    response = next(
        row for row in stock["horizon_results"]
        if int(row["horizon_weeks"]) == horizon
    )
    beta = (
        float(
            response[
                "abnormal_return_percentage_points_per_BI_innovation_point"
            ]
        )
        / 100.0
    )
    empirical_lower = float(response["lower_95_percentage_points"]) / 100.0
    empirical_upper = float(response["upper_95_percentage_points"]) / 100.0
    if config["calibration"]["nonnegative_coefficient_floor"]:
        planning_beta = max(0.0, beta)
        planning_lower = max(0.0, empirical_lower)
        planning_upper = max(0.0, empirical_upper)
    else:
        planning_beta = beta
        planning_lower = empirical_lower
        planning_upper = empirical_upper

    financials = pd.read_csv(config["inputs"]["quarterly_financials"])
    latest_year = financials.iloc[-1]["fiscal_year"]
    latest_four = financials[financials["fiscal_year"].eq(latest_year)]
    if len(latest_four) != 4:
        raise ValueError(
            "Latest fiscal year must contain four quarters for the earnings bridge"
        )
    adjusted_earnings_usd_m = float(
        latest_four["adjusted_net_income_usd_m"].sum()
    )
    market = pd.read_csv(config["inputs"]["market_valuation_reference"]).iloc[-1]
    market_cap_usd_m = float(market["market_cap_usd_m"])
    adjusted_earnings_multiple = market_cap_usd_m / adjusted_earnings_usd_m

    announcement = _read_json(
        config["inputs"]["announcement_counterfactual_manifest"]
    )
    world_cup = _read_json(config["inputs"]["world_cup_simulation_manifest"])
    world_cup_base = next(
        row for row in world_cup["scenario_results"]
        if row["scenario"] == "base"
    )
    cases = [
        ("one_brand_index_point", 1.0, "unit_mapping"),
        (
            "announcement_period_candidate",
            float(
                announcement["candidate_attribution"][
                    "exposure_weighted_delta_index"
                ]
            ),
            "attribution_not_accepted",
        ),
        (
            "world_cup_total_path_simulation",
            float(
                world_cup_base[
                    "frozen_preannouncement_exposure_weighted_gap_index_points"
                ]
            ),
            "simulation_not_accepted",
        ),
        (
            "world_cup_incremental_simulation",
            float(world_cup_base["exposure_weighted_gap_index_points"]),
            "simulation_not_accepted",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for case, delta_index, role in cases:
        candidate_values = [
            delta_index * planning_lower * adjusted_earnings_usd_m,
            delta_index * planning_upper * adjusted_earnings_usd_m,
        ]
        rows.append({
            "case": case,
            "role": role,
            "delta_brand_index_points": delta_index,
            "annual_adjusted_earnings_percent_equivalent": (
                100.0 * delta_index * planning_beta
            ),
            "annual_adjusted_earnings_usd_m_central": (
                delta_index * planning_beta * adjusted_earnings_usd_m
            ),
            "annual_adjusted_earnings_usd_m_planning_lower": min(
                candidate_values
            ),
            "annual_adjusted_earnings_usd_m_planning_upper": max(
                candidate_values
            ),
            "calibration_accepted_for_planning": bool(
                config["calibration"]["planning_use_accepted"]
            ),
            "attribution_accepted": case == "one_brand_index_point",
            "accepted_for_accounting_or_causal_claim": False,
        })
    scenarios = pd.DataFrame(rows)
    _write(scenarios, target, "market_implied_earnings_scenarios")

    central_equity_value_usd_m = planning_beta * market_cap_usd_m
    central_earnings_usd_m = (
        central_equity_value_usd_m / adjusted_earnings_multiple
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_for_planning": bool(
            config["calibration"]["planning_use_accepted"]
        ),
        "accepted_for_total_sponsorship_valuation": False,
        "superseded_for_total_return_by": "sponsorship_total_return_v2",
        "accepted_for_accounting_or_causal_claim": False,
        "selected_stock_response": {
            "horizon_weeks": horizon,
            "empirical_return_percent_per_BI_point": 100.0 * beta,
            "planning_return_percent_per_BI_point": 100.0 * planning_beta,
            "empirical_lower_95_percent": 100.0 * empirical_lower,
            "empirical_upper_95_percent": 100.0 * empirical_upper,
            "planning_lower_percent": 100.0 * planning_lower,
            "planning_upper_percent": 100.0 * planning_upper,
            "p_value_normal_approx": float(
                response["p_value_normal_approx"]
            ),
            "p_value_holm": float(response["p_value_holm"]),
            "monotonicity_rule": (
                "Coefficient is floored at zero for commercial planning; "
                "the empirical estimate and interval remain reported."
            ),
        },
        "operational_unit_mapping": {
            "statement": (
                "One BI point maps to a 0.305% increase in market-implied "
                "annual adjusted earnings under a constant earnings multiple."
            ),
            "annual_adjusted_earnings_base_usd_m": adjusted_earnings_usd_m,
            "fiscal_year": latest_year,
            "annual_adjusted_earnings_usd_m_per_BI_point": (
                central_earnings_usd_m
            ),
            "planning_lower_usd_m_per_BI_point": (
                planning_lower * adjusted_earnings_usd_m
            ),
            "planning_upper_usd_m_per_BI_point": (
                planning_upper * adjusted_earnings_usd_m
            ),
        },
        "market_value_cross_check": {
            "reference_date": str(market["reference_date"]),
            "ordinary_shares_outstanding": int(
                market["ordinary_shares_outstanding"]
            ),
            "official_market_cap_usd_m": market_cap_usd_m,
            "official_market_cap_hkd_m": float(market["market_cap_hkd_m"]),
            "adjusted_earnings_multiple": adjusted_earnings_multiple,
            "equity_value_usd_m_per_BI_point": central_equity_value_usd_m,
            "equity_value_divided_by_multiple_usd_m": (
                central_earnings_usd_m
            ),
        },
        "scenarios_artifact": "market_implied_earnings_scenarios.parquet",
        "inputs": {
            name: {"path": path, "sha256": _sha256(path)}
            for name, path in config["inputs"].items()
        },
        "guardrails": [
            "This is an operational positive planning calibration.",
            "The zero floor is an explicit monotonicity assumption, not a statistical finding.",
            "The constant earnings multiple makes the percent equity response equal the percent earnings-equivalent response.",
            "The immediate stock response is used because market news should be capitalized when observed.",
            "No inaccessible client operating data or external WACC is required.",
            "Sponsorship attribution remains separate and must not be accepted merely because the monetization coefficient is positive.",
        ],
    }
    (target / "market_implied_earnings_bridge_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/experiments/market_implied_earnings_bridge_v1.yaml",
    )
    args = parser.parse_args()
    build_market_implied_earnings_bridge(args.config)
