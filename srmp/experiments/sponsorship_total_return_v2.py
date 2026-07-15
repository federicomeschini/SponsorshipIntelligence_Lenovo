"""Dynamic total-return planning valuation for the Lenovo-FIFA sponsorship."""

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


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def build_total_return(
    config_path: str = "config/experiments/sponsorship_total_return_v2.yaml",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    stock_weekly = pd.read_parquet(config["inputs"]["stock_response_weekly"])
    stock_weekly["week"] = pd.to_datetime(stock_weekly["week"])
    counterfactual = pd.read_parquet(
        config["inputs"]["sponsorship_counterfactual_weekly"]
    )
    counterfactual["week"] = pd.to_datetime(counterfactual["week"])
    weekly = stock_weekly.merge(
        counterfactual[["week", "index_gap", "period", "exposure_weight"]],
        on="week",
        how="left",
    ).sort_values("week").reset_index(drop=True)
    weekly["gap_change"] = weekly["index_gap"].diff()
    weekly["lag_gap_change"] = weekly["gap_change"].shift()
    weekly["sponsorship_bi_innovation"] = (
        weekly["gap_change"]
        - weekly["innovation_beta_lag_delta_brand_index"]
        * weekly["lag_gap_change"]
    )
    post = weekly[weekly["period"].eq("post")].copy().reset_index(drop=True)
    if post["sponsorship_bi_innovation"].isna().any():
        raise ValueError("Post-treatment sponsorship BI innovations are incomplete")

    coefficients = pd.read_parquet(
        config["inputs"]["stock_response_coefficients"]
    )
    endpoints = pd.read_parquet(config["inputs"]["endpoint_stability"])
    curve_anchors, curves = _response_curves(
        coefficients, endpoints, config
    )
    curve_weekly_rows: list[dict[str, Any]] = []
    for scenario, cumulative in curves.items():
        incremental = np.r_[cumulative[0], np.diff(cumulative)]
        shocks = post["sponsorship_bi_innovation"].to_numpy(dtype=float)
        attributed = np.convolve(shocks, incremental)[:len(post)]
        post[f"{scenario}_attributed_log_return"] = attributed
        for lag, (cum_value, increment) in enumerate(
            zip(cumulative, incremental)
        ):
            curve_weekly_rows.append({
                "scenario": scenario,
                "lag_weeks": lag,
                "cumulative_response": float(cum_value),
                "incremental_lag_response": float(increment),
            })
    curve_weekly = pd.DataFrame(curve_weekly_rows)

    market = pd.read_parquet(config["inputs"]["market_prices"])
    market["date"] = pd.to_datetime(market["date"])
    reference = pd.read_csv(
        config["inputs"]["market_valuation_reference"]
    ).iloc[-1]
    shares = int(reference["ordinary_shares_outstanding"])
    latest_market_date = market[
        market["factor_id"].eq("LENOVO")
    ]["date"].max()
    latest_cap, cap_date, price_hkd, fx = _market_cap_usd_m(
        market, latest_market_date, shares
    )
    world_cup = _read_json(config["inputs"]["world_cup_simulation_manifest"])
    coverage = float(
        world_cup["counterfactual"]["calendar_match_coverage"]
    )
    shock_sum = float(post["sponsorship_bi_innovation"].sum())

    scenario_rows: list[dict[str, Any]] = []
    for scenario, cumulative in curves.items():
        mature_response = float(cumulative[-1])
        mature_log_return = shock_sum * mature_response
        as_of_log_return = float(
            post[f"{scenario}_attributed_log_return"].sum()
        )
        womens_share = float(
            config["contract_projection"][
                "womens_world_cup_equivalent_mens_impact"
            ][scenario]
        )
        completion_multiplier = (1.0 / coverage) * (1.0 + womens_share)
        contract_log_return = mature_log_return * completion_multiplier
        scenario_rows.append({
            "scenario": scenario,
            "sponsorship_bi_innovation_sum": shock_sum,
            "mature_13_week_response_per_bi_innovation": mature_response,
            "as_of_attributed_log_return": as_of_log_return,
            "as_of_value_usd_m": (
                latest_cap * (1.0 - np.exp(-as_of_log_return))
            ),
            "observed_path_fully_matured_log_return": mature_log_return,
            "observed_path_fully_matured_value_usd_m": (
                latest_cap * (1.0 - np.exp(-mature_log_return))
            ),
            "mens_match_coverage": coverage,
            "womens_equivalent_mens_impact": womens_share,
            "contract_completion_multiplier": completion_multiplier,
            "full_contract_planning_log_return": contract_log_return,
            "full_contract_planning_value_usd_m": (
                latest_cap * (1.0 - np.exp(-contract_log_return))
            ),
            "accepted_for_planning": True,
            "accepted_for_accounting_or_causal_claim": False,
        })
    scenarios = pd.DataFrame(scenario_rows)

    daily = pd.read_parquet(
        config["inputs"]["rolling_abnormal_returns_daily"]
    )
    daily["date"] = pd.to_datetime(daily["date"])
    event_values = _event_triangulation(
        daily, market, shares, config
    )

    _write(post, target, "sponsorship_dynamic_weekly")
    _write(curve_anchors, target, "response_curve_anchors")
    _write(curve_weekly, target, "response_curve_weekly")
    _write(scenarios, target, "total_return_scenarios")
    _write(event_values, target, "event_value_triangulation")

    base = scenarios[scenarios["scenario"].eq("base")].iloc[0]
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_for_planning": True,
        "accepted_for_accounting_or_causal_claim": False,
        "primary_planning_result": {
            "scenario": "base",
            "observed_path_fully_matured_value_usd_m": float(
                base["observed_path_fully_matured_value_usd_m"]
            ),
            "full_contract_planning_value_usd_m": float(
                base["full_contract_planning_value_usd_m"]
            ),
            "latest_market_cap_usd_m": latest_cap,
            "latest_market_cap_date": cap_date.date().isoformat(),
            "interpretation": (
                "Dynamic market-implied sponsorship value using the "
                "pre-tournament endpoint calibration and a scenario extension "
                "for the remaining men's matches and the 2027 Women's World Cup."
            ),
        },
        "scenario_results": scenarios.to_dict("records"),
        "event_triangulation": event_values.to_dict("records"),
        "method": {
            "shock": (
                "weekly change in the actual-minus-synthetic BI gap, adjusted "
                "for the rolling lag coefficient in the BI innovation model"
            ),
            "response": (
                "nonnegative inverse-variance-weighted isotonic cumulative "
                "stock response, interpolated to weekly distributed lags"
            ),
            "base_calibration": (
                "stock-response estimates through 2025-12-31, before the "
                "World Cup outcome and exceptional 2026 rally"
            ),
            "valuation": (
                "compound attributable log returns against the latest dated "
                "Lenovo market capitalization"
            ),
        },
        "market_reference": {
            "ordinary_shares": shares,
            "latest_price_hkd": price_hkd,
            "latest_usdhkd": fx,
            "latest_market_cap_usd_m": latest_cap,
        },
        "inputs": {
            name: {"path": path, "sha256": _sha256(path)}
            for name, path in config["inputs"].items()
        },
        "guardrails": [
            "The old US$45.7m single multiplication is superseded.",
            "The base response is calibrated before the World Cup outcome to avoid circular valuation from the 2026 rally.",
            "The response curve is constrained nonnegative and nondecreasing for planning; raw coefficients remain archived.",
            "The Women's World Cup share is an explicit scenario assumption, not observed data.",
            "Announcement and tournament CARs are triangulation only because material Lenovo news is confounded.",
            "The result is market-implied total value, not accounting profit or causal audit value.",
        ],
    }
    (target / "total_return_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="config/experiments/sponsorship_total_return_v2.yaml",
    )
    args = parser.parse_args()
    build_total_return(args.config)
