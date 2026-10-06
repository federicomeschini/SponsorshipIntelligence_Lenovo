"""Sustained-level market-implied valuation of the Lenovo-FIFA sponsorship (ADR-0030).

The retired v2 summed weekly changes in the actual-minus-synthetic gap. Those
changes telescope, so v2 effectively valued the gap in the final (provisional)
week. v3 values a sustained gap level under rule-fixed definitions, with the
market capitalisation base also fixed by rule, and keeps the announcement and
tournament event-study triangulation (ADR-0036).
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


def _weighted_isotonic_nonnegative(
    values: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    """Weighted pool-adjacent-violators projection onto nondecreasing values."""
    blocks: list[dict[str, Any]] = []
    for position, (value, weight) in enumerate(zip(values, weights)):
        blocks.append({
            "value": float(value),
            "weight": float(weight),
            "positions": [position],
        })
        while (
            len(blocks) >= 2
            and blocks[-2]["value"] > blocks[-1]["value"]
        ):
            right = blocks.pop()
            left = blocks.pop()
            total_weight = left["weight"] + right["weight"]
            pooled = (
                left["value"] * left["weight"]
                + right["value"] * right["weight"]
            ) / total_weight
            blocks.append({
                "value": pooled,
                "weight": total_weight,
                "positions": left["positions"] + right["positions"],
            })
    result = np.zeros(len(values), dtype=float)
    for block in blocks:
        result[block["positions"]] = max(0.0, block["value"])
    return result


def _response_curves(
    coefficients: pd.DataFrame,
    endpoints: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    horizons = np.asarray(config["response"]["horizons_weeks"], dtype=int)
    primary = coefficients[
        coefficients["term"].eq("brand_index_innovation")
        & coefficients["model"].str.startswith("innovation_response")
    ].sort_values("horizon_weeks")
    if primary["horizon_weeks"].astype(int).tolist() != horizons.tolist():
        raise ValueError("Frozen stock-response horizons are incomplete")

    curve_rows: list[dict[str, Any]] = []
    curves: dict[str, np.ndarray] = {}
    for scenario, specification in config["response"]["scenarios"].items():
        if specification["source"] == "full_sample_immediate_response_held_constant":
            raw = np.repeat(float(primary.iloc[0]["estimate"]), len(horizons))
            standard_errors = np.repeat(
                float(primary.iloc[0]["robust_se"]), len(horizons)
            )
            regularized = np.maximum(raw, 0.0)
            source_label = "full_sample_h0_held_constant"
        elif specification["source"] == "endpoint_stability":
            endpoint = pd.Timestamp(specification["calibration_endpoint"])
            selected = endpoints[
                pd.to_datetime(endpoints["sample_endpoint"]).eq(endpoint)
            ].sort_values("horizon_weeks")
            if selected["horizon_weeks"].astype(int).tolist() != horizons.tolist():
                raise ValueError(f"Missing endpoint calibration: {endpoint}")
            raw = selected["estimate"].to_numpy(dtype=float)
            standard_errors = selected["robust_se"].to_numpy(dtype=float)
            regularized = _weighted_isotonic_nonnegative(
                raw, 1.0 / np.square(standard_errors)
            )
            source_label = f"endpoint_{endpoint.date().isoformat()}"
        elif specification["source"] == "full_sample_all_horizons":
            raw = primary["estimate"].to_numpy(dtype=float)
            standard_errors = primary["robust_se"].to_numpy(dtype=float)
            regularized = _weighted_isotonic_nonnegative(
                raw, 1.0 / np.square(standard_errors)
            )
            source_label = "full_sample_all_horizons"
        else:
            raise ValueError(f"Unknown response source: {specification['source']}")

        weekly_curve = np.interp(np.arange(14), horizons, regularized)
        curves[scenario] = weekly_curve
        for horizon, raw_value, standard_error, constrained in zip(
            horizons, raw, standard_errors, regularized
        ):
            curve_rows.append({
                "scenario": scenario,
                "source": source_label,
                "horizon_weeks": int(horizon),
                "raw_cumulative_response": float(raw_value),
                "raw_robust_se": float(standard_error),
                "regularized_cumulative_response": float(constrained),
            })
    return pd.DataFrame(curve_rows), curves


def _market_cap_usd_m(
    market: pd.DataFrame, date: pd.Timestamp, shares: int
) -> tuple[float, pd.Timestamp, float, float]:
    lenovo = market[
        market["factor_id"].eq("LENOVO") & market["date"].le(date)
    ].sort_values("date").iloc[-1]
    fx = market[
        market["factor_id"].eq("USDHKD")
        & market["date"].le(lenovo["date"])
    ].sort_values("date").iloc[-1]
    cap = float(lenovo["close"]) * shares / float(fx["close"]) / 1_000_000.0
    return cap, pd.Timestamp(lenovo["date"]), float(lenovo["close"]), float(fx["close"])


def _event_triangulation(
    daily: pd.DataFrame,
    market: pd.DataFrame,
    shares: int,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    start = pd.Timestamp(
        config["event_triangulation"]["announcement_first_hk_session"]
    )
    before = daily[daily["date"] < start]["date"].max()
    pre_cap, cap_date, _, _ = _market_cap_usd_m(market, before, shares)
    post = daily[daily["date"] >= start].sort_values("date")
    for days in config["event_triangulation"]["announcement_windows_trading_days"]:
        selected = post.head(int(days))
        log_car = float(selected["abnormal_return"].sum())
        simple_car = float(np.exp(log_car) - 1.0)
        rows.append({
            "event": "fifa_tech_world_announcement",
            "window": f"0_to_{int(days)-1}_trading_days",
            "start": selected.iloc[0]["date"],
            "end": selected.iloc[-1]["date"],
            "log_car": log_car,
            "simple_car": simple_car,
            "pre_event_market_cap_usd_m": pre_cap,
            "gross_event_value_usd_m": pre_cap * simple_car,
            "interpretation": "gross Lenovo event; FIFA is confounded with Tech World",
            "market_cap_reference_date": cap_date,
        })

    tournament_start = pd.Timestamp(
        config["event_triangulation"]["tournament_start"]
    )
    selected = daily[daily["date"] >= tournament_start].sort_values("date")
    before = daily[daily["date"] < tournament_start]["date"].max()
    pre_cap, cap_date, _, _ = _market_cap_usd_m(market, before, shares)
    log_car = float(selected["abnormal_return"].sum())
    simple_car = float(np.exp(log_car) - 1.0)
    rows.append({
        "event": "world_cup_observed_to_latest_market_date",
        "window": "tournament_start_to_latest",
        "start": selected.iloc[0]["date"],
        "end": selected.iloc[-1]["date"],
        "log_car": log_car,
        "simple_car": simple_car,
        "pre_event_market_cap_usd_m": pre_cap,
        "gross_event_value_usd_m": pre_cap * simple_car,
        "interpretation": (
            "gross period value; FIFA is confounded with financing, buyback "
            "and other corporate news"
        ),
        "market_cap_reference_date": cap_date,
    })
    return pd.DataFrame(rows)


def _levels(weekly: pd.DataFrame, config: dict[str, Any]) -> dict[str, float]:
    """Sustained gap levels from the total-effect path (provisional weeks already excluded)."""
    post = weekly[weekly["period"].eq("post")].sort_values("week")
    tournament = pd.Timestamp(config["sustained_level"]["tournament_start_week"])
    return {
        "all_post_mean": float(post["index_gap"].mean()),
        "pre_tournament_post_mean": float(post.loc[post["week"] < tournament, "index_gap"].mean()),
        "trailing_26_week_mean": float(post["index_gap"].tail(26).mean()),
    }


def _value(cap: float, log_return: float) -> float:
    """Value attributable to a log return, against the with-sponsorship capitalisation."""
    return cap * (1.0 - np.exp(-log_return))


def build_total_return_v3(
    config_path: str = "config/experiments/sponsorship_total_return_v3.yaml",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs = config["inputs"]
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    counterfactual = pd.read_parquet(inputs["total_effect_weekly"])
    counterfactual["week"] = pd.to_datetime(counterfactual["week"])
    effect = json.loads(Path(inputs["total_effect_manifest"]).read_text(encoding="utf-8"))
    levels = _levels(counterfactual, config)

    stock_weekly = pd.read_parquet(inputs["stock_response_weekly"])
    stock_weekly["week"] = pd.to_datetime(stock_weekly["week"])
    post_weeks = counterfactual.loc[counterfactual["period"].eq("post"), "week"]
    beta = float(stock_weekly.loc[stock_weekly["week"].isin(post_weeks),
                                  "innovation_beta_lag_delta_brand_index"].mean())
    conversion = 1.0 - beta

    coefficients = pd.read_parquet(inputs["stock_response_coefficients"])
    endpoints = pd.read_parquet(inputs["endpoint_stability"])
    anchors, curves = _response_curves(coefficients, endpoints, config)
    endpoint = pd.Timestamp(config["response"]["scenarios"]["base"]["calibration_endpoint"])
    base_13 = endpoints[pd.to_datetime(endpoints["sample_endpoint"]).eq(endpoint)
                        & endpoints["horizon_weeks"].eq(13)].iloc[0]
    empirical = {
        "estimate": float(base_13["estimate"]),
        "lower_95": float(base_13["estimate"] - 1.96 * base_13["robust_se"]),
        "upper_95": float(base_13["estimate"] + 1.96 * base_13["robust_se"]),
    }

    market = pd.read_parquet(inputs["market_prices"])
    market["date"] = pd.to_datetime(market["date"])
    shares = int(pd.read_csv(inputs["market_valuation_reference"]).iloc[-1]["ordinary_shares_outstanding"])
    announcement = config["announcement_date"]
    lenovo_dates = market.loc[market["factor_id"].eq("LENOVO"), "date"]
    post_dates = lenovo_dates[lenovo_dates > pd.Timestamp(announcement)]
    caps = {
        "pre_announcement_market_cap": _market_cap_usd_m(market, pd.Timestamp(announcement), shares)[0],
        "latest_market_cap": _market_cap_usd_m(market, lenovo_dates.max(), shares)[0],
        "mean_post_announcement_market_cap": float(np.mean([
            _market_cap_usd_m(market, day, shares)[0] for day in post_dates.iloc[::5]
        ])),
    }
    cap = caps[config["valuation_base"]["primary"]]

    rows = []
    for definition, level in levels.items():
        innovations = level * conversion
        for scenario, curve in curves.items():
            mature = float(curve[-1])
            womens = float(config["contract_projection"]["womens_world_cup_equivalent_mens_impact"][scenario])
            log_return = innovations * mature
            rows.append({
                "level_definition": definition,
                "is_primary_level": definition == config["sustained_level"]["primary"],
                "scenario": scenario,
                "sustained_gap_index_points": level,
                "cumulative_innovations": innovations,
                "mature_13_week_response": mature,
                "observed_value_usd_m": _value(cap, log_return),
                "contract_multiplier": 1.0 + womens,
                "full_contract_value_usd_m": _value(cap, log_return * (1.0 + womens)),
            })
    scenarios = pd.DataFrame(rows)

    primary_level = levels[config["sustained_level"]["primary"]]
    primary_innovations = primary_level * conversion
    base_row = scenarios[scenarios["is_primary_level"] & scenarios["scenario"].eq("base")].iloc[0]
    empirical_values = {
        key: _value(cap, primary_innovations * value * base_row["contract_multiplier"])
        for key, value in empirical.items()
    }
    sensitivity = pd.read_parquet(inputs["donor_sensitivity"])
    donor_levels = sensitivity["post_mean_gap"]
    donor_range = {
        "min_level": float(donor_levels.min()), "max_level": float(donor_levels.max()),
        "min_value_usd_m": _value(cap, float(donor_levels.min()) * conversion * float(base_row["mature_13_week_response"]) * base_row["contract_multiplier"]),
        "max_value_usd_m": _value(cap, float(donor_levels.max()) * conversion * float(base_row["mature_13_week_response"]) * base_row["contract_multiplier"]),
    }
    cap_sensitivity = {
        name: _value(value, primary_innovations * float(base_row["mature_13_week_response"]) * base_row["contract_multiplier"])
        for name, value in caps.items()
    }

    attribution_accepted = bool(effect["passes_primary_test"])
    response_identified = empirical["lower_95"] > 0
    daily = pd.read_parquet(inputs["rolling_abnormal_returns_daily"])
    daily["date"] = pd.to_datetime(daily["date"])
    event_values = _event_triangulation(daily, market, shares, config)
    _write(event_values, target, "event_value_triangulation")
    _write(scenarios, target, "total_return_v3_scenarios")
    _write(anchors, target, "response_curve_anchors")
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_for_planning": bool(attribution_accepted and response_identified),
        "accepted_for_accounting_or_causal_claim": False,
        "evidence": {
            "attribution_status": ("total_effect_passes_placebo_test" if attribution_accepted
                                   else "total_effect_not_distinguishable"),
            "total_effect_p_value": effect["primary"]["p_value"],
            "attribution_accepted": attribution_accepted,
            "base_13_week_response": empirical,
            "response_identified": response_identified,
        },
        "sustained_levels_index_points": levels,
        "innovation_conversion": {"mean_lag_coefficient": beta, "factor": conversion},
        "market_cap_usd_m": caps,
        "valuation_base": config["valuation_base"]["primary"],
        "primary_result": {
            "level_definition": config["sustained_level"]["primary"],
            "sustained_gap_index_points": primary_level,
            "observed_value_usd_m": float(base_row["observed_value_usd_m"]),
            "full_contract_value_usd_m": float(base_row["full_contract_value_usd_m"]),
            "empirical_95_full_contract_usd_m": {
                "lower": empirical_values["lower_95"], "upper": empirical_values["upper_95"]},
            "donor_leave_one_out_full_contract_usd_m": donor_range,
            "market_cap_base_sensitivity_full_contract_usd_m": cap_sensitivity,
        },
        "event_triangulation": event_values.to_dict("records"),
        "comparison_with_v2": (
            "v2 sums weekly gap changes, which telescope to the final-week gap; "
            "v3 values a rule-fixed sustained level and a rule-fixed market-cap base."
        ),
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
        "guardrails": [
            "Planning acceptance requires both an accepted attribution and a base response whose 95% interval excludes zero.",
            "The response curve is constrained nonnegative for the scenario values; the empirical interval is unconstrained.",
            "The Women's World Cup share is an explicit scenario assumption.",
            "Market-implied value, not accounting profit or a causal audit value.",
        ],
    }
    (target / "total_return_v3_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/sponsorship_total_return_v3.yaml")
    args = parser.parse_args()
    build_total_return_v3(args.config)
