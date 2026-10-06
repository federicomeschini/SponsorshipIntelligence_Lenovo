"""Compare sponsorship valuation routes on evidence, value and breakeven (ADR-0030).

Each route maps the same sustained Brand Index level to money through a
different link. While no link is statistically identified, the decision-useful
output is the breakeven: the sustained lift each route would need to cover a
given cost, set against the lift actually measured.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from srmp.experiments.brand_financial_bridge_v1 import _sha256, _write


def _json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_valuation_routes(
    config_path: str = "config/experiments/valuation_routes_v1.yaml",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs = config["inputs"]
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)
    alpha = float(config["assumptions"]["significance_level"])

    v3 = _json(inputs["total_return_v3_manifest"])
    level = float(v3["primary_result"]["sustained_gap_index_points"])
    conversion = float(v3["innovation_conversion"]["factor"])
    cap = float(v3["market_cap_usd_m"][v3["valuation_base"]])
    response = v3["evidence"]["base_13_week_response"]
    scenarios = pd.read_parquet(inputs["total_return_v3_scenarios"])
    base = scenarios[scenarios["is_primary_level"] & scenarios["scenario"].eq("base")].iloc[0]
    multiplier = float(base["contract_multiplier"])

    earnings = _json(inputs["market_implied_manifest"])
    mapping = earnings["operational_unit_mapping"]
    selected = earnings["selected_stock_response"]
    stock = _json(inputs["stock_response_manifest"])
    h13 = next(row for row in stock["horizon_results"] if row["horizon_weeks"] == 13)
    bridge = _json(inputs["financial_bridge_manifest"])["primary_profit_mapping"]
    financials = pd.read_csv(inputs["quarterly_financials"])
    ttm_revenue = float(financials["revenue_usd_m"].tail(4).sum())
    events = pd.read_parquet(inputs["event_triangulation"])
    announcement = events[events["event"].eq("fifa_tech_world_announcement")]
    world_cup = _json(inputs["world_cup_estimate_manifest"])
    media = _json(inputs["media_values_manifest"])
    royalty = yaml.safe_load(Path(inputs["royalty_schedule"]).read_text(encoding="utf-8"))
    tax = float(config["assumptions"]["royalty_relief_tax_rate"])

    margin_per_point = float(bridge["estimate"]) / 100.0
    routes = [
        {
            "route": "market_implied_equity_v3",
            "link": "13-week abnormal equity return per unexpected BI point (2025 endpoint)",
            "link_estimate": response["estimate"], "link_lower_95": response["lower_95"],
            "link_upper_95": response["upper_95"],
            "link_identified": response["lower_95"] > 0,
            "value_unit": "full-contract equity value, US$m",
            "value_at_measured_level": float(base["full_contract_value_usd_m"]),
            "value_lower_95": v3["primary_result"]["empirical_95_full_contract_usd_m"]["lower"],
            "value_upper_95": v3["primary_result"]["empirical_95_full_contract_usd_m"]["upper"],
            "missing_for_decision_grade": "accepted attribution; a response whose interval excludes zero",
        },
        {
            "route": "market_implied_annual_earnings",
            "link": "immediate abnormal return per BI point x FY adjusted earnings (ADR-0025)",
            "link_estimate": selected["empirical_return_percent_per_BI_point"] / 100,
            "link_lower_95": selected["empirical_lower_95_percent"] / 100,
            "link_upper_95": selected["empirical_upper_95_percent"] / 100,
            "link_identified": selected["p_value_normal_approx"] < alpha,
            "value_unit": "annual earnings-equivalent, US$m",
            "value_at_measured_level": level * mapping["annual_adjusted_earnings_usd_m_per_BI_point"],
            "value_lower_95": level * mapping["annual_adjusted_earnings_base_usd_m"] * selected["empirical_lower_95_percent"] / 100,
            "value_upper_95": level * mapping["annual_adjusted_earnings_base_usd_m"] * selected["empirical_upper_95_percent"] / 100,
            "missing_for_decision_grade": "a significant stock response; same caveat as the equity route",
        },
        {
            "route": "direct_profit_margin",
            "link": "adjusted net margin pp per BI point, quarterly first differences with macro controls",
            "link_estimate": float(bridge["estimate"]), "link_lower_95": float(bridge["lower_95"]),
            "link_upper_95": float(bridge["upper_95"]),
            "link_identified": float(bridge["p_value_normal_approx"]) < alpha,
            "value_unit": "annual adjusted net income, US$m (trailing-four-quarter revenue)",
            "value_at_measured_level": level * margin_per_point * ttm_revenue,
            "value_lower_95": level * float(bridge["lower_95"]) / 100 * ttm_revenue,
            "value_upper_95": level * float(bridge["upper_95"]) / 100 * ttm_revenue,
            "missing_for_decision_grade": "more quarters or product-level data; 16 first differences cannot separate brand from category demand",
        },
        {
            "route": "relief_from_royalty",
            "link": "royalty-rate uplift per BI point from an approved schedule",
            "link_estimate": None, "link_lower_95": None, "link_upper_95": None,
            "link_identified": bool(royalty.get("schedule")),
            "value_unit": "annual after-tax royalty saving per 1bp of royalty rate, US$m",
            "value_at_measured_level": None,
            "value_lower_95": None, "value_upper_95": None,
            "value_per_basis_point": ttm_revenue * 1e-4 * (1 - tax),
            "missing_for_decision_grade": f"royalty schedule status: {royalty.get('status')}",
        },
        {
            "route": "announcement_event_study",
            "link": "cumulative abnormal return around the 2024-10-15 announcement",
            "link_estimate": float(announcement["log_car"].min()),
            "link_lower_95": None, "link_upper_95": float(announcement["log_car"].max()),
            "link_identified": False,
            "value_unit": "gross event equity value, US$m",
            "value_at_measured_level": float(announcement["gross_event_value_usd_m"].min()),
            "value_lower_95": None,
            "value_upper_95": float(announcement["gross_event_value_usd_m"].max()),
            "missing_for_decision_grade": "FIFA is confounded with Tech World news on the same day",
        },
        {
            "route": "industry_claimed_media_value",
            "link": "AVE (P1): comparison line only, never a model value",
            "link_estimate": None, "link_lower_95": None, "link_upper_95": None,
            "link_identified": False,
            "value_unit": f"media value {media['date_min']} to {media['date_max']}, currency not stated",
            "value_at_measured_level": media["totals"]["media_value_qi"] / 1e6,
            "value_lower_95": None,
            "value_upper_95": media["totals"]["media_value_full"] / 1e6,
            "missing_for_decision_grade": "not a value measure under P1",
        },
    ]
    route_frame = pd.DataFrame(routes)

    # Breakeven: the sustained BI lift each identified-in-form route needs.
    response_mature = float(base["mature_13_week_response"])
    rows = []
    for total in config["cost_grid_usd_m"]["total_contract"]:
        needed_log = -np.log(1 - total / cap)
        rows.append({
            "route": "market_implied_equity_v3", "cost_basis": "total contract", "cost_usd_m": total,
            "required_sustained_lift_index_points": needed_log / (conversion * response_mature * multiplier)
            if response_mature > 0 else None,
        })
    for annual in config["cost_grid_usd_m"]["annual"]:
        per_point = mapping["annual_adjusted_earnings_usd_m_per_BI_point"]
        rows.append({
            "route": "market_implied_annual_earnings", "cost_basis": "annual", "cost_usd_m": annual,
            "required_sustained_lift_index_points": annual / per_point if per_point > 0 else None,
        })
        rows.append({
            "route": "direct_profit_margin", "cost_basis": "annual", "cost_usd_m": annual,
            "required_sustained_lift_index_points": (
                annual / (margin_per_point * ttm_revenue) if margin_per_point > 0 else None),
        })
        rows.append({
            "route": "relief_from_royalty", "cost_basis": "annual", "cost_usd_m": annual,
            "required_royalty_uplift_basis_points": annual / (ttm_revenue * 1e-4 * (1 - tax)),
        })
    breakeven = pd.DataFrame(rows)
    breakeven["measured_sustained_lift_index_points"] = level
    breakeven["measured_lift_distinguishable"] = False

    world_cup_primary = world_cup["primary"]
    _write(route_frame, target, "valuation_routes")
    _write(breakeven, target, "breakeven")
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "measured_lift": {
            "announcement_sustained_level_index_points": level,
            "announcement_attribution_status": v3["evidence"]["attribution_status"],
            "world_cup_incremental_primary_index_points": world_cup_primary["primary_exposure_weighted_gap"],
            "world_cup_status": world_cup["status"],
        },
        "routes_identified": [row["route"] for row in routes if row["link_identified"]],
        "trailing_four_quarter_revenue_usd_m": ttm_revenue,
        "cost_grid_usd_m": config["cost_grid_usd_m"],
        "assumptions": config["assumptions"],
        "reading": (
            "No route has both an identified brand-to-money link and an accepted "
            "attribution. Breakeven lifts show what the sponsorship would have to "
            "deliver under each route; compare them with the measured lift and its "
            "placebo distribution, not with a point value."
        ),
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
    }
    (target / "valuation_routes_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/valuation_routes_v1.yaml")
    args = parser.parse_args()
    build_valuation_routes(args.config)
