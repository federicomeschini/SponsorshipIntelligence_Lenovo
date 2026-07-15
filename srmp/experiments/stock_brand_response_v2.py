"""No-look-ahead Brand Index-to-stock-return response experiment."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from srmp.experiments.brand_financial_bridge_v1 import _ols, _sha256, _write
from srmp.experiments.sponsorship_counterfactual_v1 import (
    _monday,
    _weekly_event_controls,
)


def _holm_adjust(p_values: list[float]) -> list[float]:
    """Return Holm family-wise adjusted p-values in original order."""
    values = np.asarray(p_values, dtype=float)
    order = np.argsort(values)
    adjusted_sorted = np.maximum.accumulate(
        (len(values) - np.arange(len(values))) * values[order]
    )
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)
    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = adjusted_sorted
    return adjusted.tolist()


def _rolling_factor_returns(
    market_path: str, window: int
) -> pd.DataFrame:
    market = pd.read_parquet(market_path)
    market["date"] = pd.to_datetime(market["date"])
    levels = market.pivot(
        index="date", columns="factor_id", values="adj_close"
    ).sort_index()
    returns = np.log(levels).diff()
    hk = returns[["LENOVO", "HSI"]].dropna().reset_index()
    ndx_hkd_level = levels["NDX"] * levels["USDHKD"].ffill()
    ndx = (
        np.log(ndx_hkd_level).diff().dropna()
        .rename("ndx_hkd_lagged").reset_index()
    )
    aligned = pd.merge_asof(
        hk.sort_values("date"),
        ndx.sort_values("date"),
        on="date",
        direction="backward",
        allow_exact_matches=False,
    ).dropna().reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for position in range(window, len(aligned)):
        history = aligned.iloc[position - window:position]
        x_history = np.column_stack([
            np.ones(len(history)),
            history[["HSI", "ndx_hkd_lagged"]].to_numpy(),
        ])
        beta = (
            np.linalg.pinv(x_history.T @ x_history)
            @ x_history.T
            @ history["LENOVO"].to_numpy()
        )
        current = aligned.iloc[position]
        x_current = np.r_[
            1.0,
            current[["HSI", "ndx_hkd_lagged"]].to_numpy(dtype=float),
        ]
        predicted = float(x_current @ beta)
        rows.append({
            "date": current["date"],
            "lenovo_log_return": float(current["LENOVO"]),
            "hsi_log_return": float(current["HSI"]),
            "ndx_hkd_lagged_log_return": float(current["ndx_hkd_lagged"]),
            "predicted_lenovo_log_return": predicted,
            "abnormal_return": float(current["LENOVO"] - predicted),
            "factor_alpha": float(beta[0]),
            "factor_beta_hsi": float(beta[1]),
            "factor_beta_ndx_hkd_lagged": float(beta[2]),
            "factor_training_start": history.iloc[0]["date"],
            "factor_training_end": history.iloc[-1]["date"],
            "factor_training_observations": int(len(history)),
        })
    return pd.DataFrame(rows)


def _category_demand(config: dict[str, Any]) -> pd.DataFrame:
    trends = pd.read_parquet(config["inputs"]["joint_donor_trends"])
    trends["week"] = _monday(trends["week"])
    queries = config["brand_index_innovation"]["category_demand_queries"]
    pivot = trends[trends["query_id"].isin(queries)].pivot(
        index="week", columns="query_id", values="interest_common_scale"
    ).sort_index()
    missing = sorted(set(queries) - set(pivot.columns))
    if missing:
        raise ValueError(f"Missing category-demand Trends queries: {missing}")
    change = np.log1p(pivot[queries]).diff().mean(axis=1)
    return change.rename("category_demand_change").reset_index()


def _earnings_controls(path: str, carryover_weeks: int) -> pd.DataFrame:
    events = pd.read_csv(path)
    events["event_date"] = pd.to_datetime(events["event_date"])
    events["week"] = _monday(events["event_date"])
    weeks: list[pd.Timestamp] = []
    for week in events["week"]:
        weeks.extend(
            week + pd.to_timedelta(7 * lag, unit="D")
            for lag in range(carryover_weeks + 1)
        )
    return pd.DataFrame({"week": sorted(set(weeks)), "earnings_control": 1.0})


def _add_brand_index_innovations(
    panel: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    result = panel.copy()
    result["lag_delta_brand_index"] = result["delta_brand_index"].shift()
    sequence = np.arange(len(result), dtype=float)
    result["season_sin"] = np.sin(2.0 * np.pi * sequence / 52.18)
    result["season_cos"] = np.cos(2.0 * np.pi * sequence / 52.18)
    regressors = config["brand_index_innovation"]["regressors"]
    window = int(config["brand_index_innovation"]["estimation_window_weeks"])
    minimum = int(config["brand_index_innovation"]["minimum_history_weeks"])
    result["brand_index_expected_change"] = np.nan
    result["innovation_training_observations"] = 0
    result["innovation_beta_lag_delta_brand_index"] = np.nan
    for position in range(len(result)):
        history = result.iloc[max(0, position - window):position].dropna(
            subset=["delta_brand_index"] + regressors
        )
        if len(history) < minimum or result.loc[position, regressors].isna().any():
            continue
        x_history = np.column_stack([
            np.ones(len(history)), history[regressors].to_numpy(dtype=float)
        ])
        beta = (
            np.linalg.pinv(x_history.T @ x_history)
            @ x_history.T
            @ history["delta_brand_index"].to_numpy(dtype=float)
        )
        x_current = np.r_[1.0, result.loc[position, regressors].to_numpy(float)]
        result.loc[position, "brand_index_expected_change"] = float(
            x_current @ beta
        )
        lag_position = regressors.index("lag_delta_brand_index")
        result.loc[
            position, "innovation_beta_lag_delta_brand_index"
        ] = float(beta[1 + lag_position])
        result.loc[position, "innovation_training_observations"] = len(history)
    result["brand_index_innovation"] = (
        result["delta_brand_index"] - result["brand_index_expected_change"]
    )
    return result


def _forward_sum(series: pd.Series, horizon: int) -> pd.Series:
    values = pd.concat(
        [series.shift(-lead) for lead in range(horizon + 1)], axis=1
    )
    return values.sum(axis=1, min_count=horizon + 1)


def _fit_response_family(
    panel: pd.DataFrame,
    config: dict[str, Any],
    shock: str,
    model_prefix: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    base_regressors = config["stock_response"]["regressors"]
    regressors = [shock if term == "brand_index_innovation" else term
                  for term in base_regressors]
    horizons = [int(value) for value in config["stock_response"]["horizons_weeks"]]
    minimum_hac = int(config["stock_response"]["minimum_hac_lags"])
    for horizon in horizons:
        outcome = f"forward_abnormal_return_h{horizon}"
        coefficients, diag, _ = _ols(
            panel,
            outcome,
            regressors,
            f"{model_prefix}_h{horizon}",
            covariance="HAC",
            hac_lags=max(minimum_hac, horizon + 1),
        )
        coefficients["horizon_weeks"] = horizon
        coefficients["shock_definition"] = shock
        rows.append(coefficients)
        diagnostics.append(diag)
    combined = pd.concat(rows, ignore_index=True)
    shock_rows = combined[combined["term"].eq(shock)]
    adjusted = _holm_adjust(shock_rows["p_value_normal_approx"].tolist())
    combined["p_value_holm"] = np.nan
    combined.loc[shock_rows.index, "p_value_holm"] = adjusted
    return combined, diagnostics


def _quarter_jackknife(
    panel: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    regressors = config["stock_response"]["regressors"]
    minimum_hac = int(config["stock_response"]["minimum_hac_lags"])
    rows: list[dict[str, Any]] = []
    working = panel.dropna(subset=["brand_index_innovation"]).copy()
    working["calendar_quarter"] = working["week"].dt.to_period("Q").astype(str)
    for horizon in config["stock_response"]["horizons_weeks"]:
        outcome = f"forward_abnormal_return_h{horizon}"
        for quarter in sorted(working["calendar_quarter"].unique()):
            # Remove every shock whose forward-return window touches the held-out
            # quarter. Merely removing shocks that start in the quarter would
            # leak held-out returns into overlapping long-horizon outcomes.
            touches_held_out = pd.Series(False, index=working.index)
            for lead in range(int(horizon) + 1):
                response_quarter = (
                    working["week"] + pd.to_timedelta(7 * lead, unit="D")
                ).dt.to_period("Q").astype(str)
                touches_held_out |= response_quarter.eq(quarter)
            sample = working[~touches_held_out]
            coefficients, diag, _ = _ols(
                sample,
                outcome,
                regressors,
                f"jackknife_h{horizon}_without_{quarter}",
                covariance="HAC",
                hac_lags=max(minimum_hac, int(horizon) + 1),
            )
            shock = coefficients[
                coefficients["term"].eq("brand_index_innovation")
            ].iloc[0]
            rows.append({
                "horizon_weeks": int(horizon),
                "excluded_calendar_quarter": quarter,
                "estimate": float(shock["estimate"]),
                "robust_se": float(shock["robust_se"]),
                "p_value_normal_approx": float(shock["p_value_normal_approx"]),
                "observations": int(diag["observations"]),
            })
    return pd.DataFrame(rows)


def _endpoint_stability(
    panel: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    regressors = config["stock_response"]["regressors"]
    minimum_hac = int(config["stock_response"]["minimum_hac_lags"])
    configured = [
        pd.Timestamp(value)
        for value in config["stock_response"]["endpoint_stability_dates"]
    ]
    endpoints = configured + [pd.Timestamp(panel["week"].max())]
    rows: list[dict[str, Any]] = []
    for endpoint in endpoints:
        for horizon in config["stock_response"]["horizons_weeks"]:
            # The complete cumulative-return window must be observable by the
            # endpoint; this prevents future returns leaking into an earlier cut.
            complete_by_endpoint = (
                panel["week"] + pd.to_timedelta(7 * int(horizon), unit="D")
                <= endpoint
            )
            sample = panel[complete_by_endpoint]
            outcome = f"forward_abnormal_return_h{horizon}"
            coefficients, diag, _ = _ols(
                sample,
                outcome,
                regressors,
                f"endpoint_{endpoint.date()}_h{horizon}",
                covariance="HAC",
                hac_lags=max(minimum_hac, int(horizon) + 1),
            )
            shock = coefficients[
                coefficients["term"].eq("brand_index_innovation")
            ].iloc[0]
            rows.append({
                "sample_endpoint": endpoint,
                "horizon_weeks": int(horizon),
                "estimate": float(shock["estimate"]),
                "robust_se": float(shock["robust_se"]),
                "p_value_normal_approx": float(shock["p_value_normal_approx"]),
                "observations": int(diag["observations"]),
            })
    return pd.DataFrame(rows)


def build_stock_response(
    config_path: str = "config/experiments/stock_brand_response_v2.yaml",
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    target = Path(config["outputs"]["directory"])
    window = int(config["factor_model"]["estimation_window_trading_days"])
    daily = _rolling_factor_returns(config["inputs"]["market_prices"], window)
    daily["week"] = _monday(daily["date"])
    weekly_returns = daily.groupby("week", as_index=False).agg(
        abnormal_return=("abnormal_return", "sum"),
        lenovo_log_return=("lenovo_log_return", "sum"),
        realized_volatility=(
            "abnormal_return", lambda values: float(np.sqrt(np.square(values).sum()))
        ),
        trading_days=("date", "size"),
    )

    index = pd.read_parquet(config["inputs"]["brand_index"])
    index["week"] = pd.to_datetime(index["week"])
    index = index[["week", "index_level"]].copy()
    index["delta_brand_index"] = index["index_level"].diff()
    events = pd.read_csv(config["inputs"]["product_campaign_events"])
    event_controls = _weekly_event_controls(events, carryover_weeks=1).reset_index()
    earnings = _earnings_controls(
        config["inputs"]["financial_results_events"],
        int(config["stock_response"]["earnings_carryover_weeks"]),
    )
    panel = (
        index.merge(weekly_returns, on="week", how="inner")
        .merge(_category_demand(config), on="week", how="left")
        .merge(event_controls, on="week", how="left")
        .merge(earnings, on="week", how="left")
        .sort_values("week")
        .reset_index(drop=True)
    )
    controls = [
        "product_campaign_control", "promotion_calendar_control",
        "mixed_event_control", "earnings_control",
    ]
    panel[controls] = panel[controls].fillna(0.0)
    panel["lag_abnormal_return"] = panel["abnormal_return"].shift()
    panel["lag_realized_volatility"] = panel["realized_volatility"].shift()
    panel = _add_brand_index_innovations(panel, config)
    for horizon in config["stock_response"]["horizons_weeks"]:
        panel[f"forward_abnormal_return_h{horizon}"] = _forward_sum(
            panel["abnormal_return"], int(horizon)
        )

    primary, primary_diagnostics = _fit_response_family(
        panel, config, "brand_index_innovation", "innovation_response"
    )
    raw, raw_diagnostics = _fit_response_family(
        panel, config, "delta_brand_index", "raw_change_sensitivity"
    )
    coefficients = pd.concat([primary, raw], ignore_index=True)

    placebo_lead = int(config["stock_response"]["reverse_placebo_lead_weeks"])
    panel["future_brand_index_innovation"] = panel[
        "brand_index_innovation"
    ].shift(-placebo_lead)
    placebo_regressors = [
        "future_brand_index_innovation", "lag_abnormal_return",
        "lag_realized_volatility", "category_demand_change",
        "product_campaign_control", "promotion_calendar_control",
        "mixed_event_control", "earnings_control",
    ]
    placebo, placebo_diag, _ = _ols(
        panel,
        "forward_abnormal_return_h0",
        placebo_regressors,
        f"future_innovation_placebo_lead_{placebo_lead}",
        covariance="HAC",
        hac_lags=int(config["stock_response"]["minimum_hac_lags"]),
    )
    placebo["horizon_weeks"] = 0
    placebo["shock_definition"] = "future_brand_index_innovation"
    placebo["p_value_holm"] = np.nan
    coefficients = pd.concat([coefficients, placebo], ignore_index=True)
    jackknife = _quarter_jackknife(panel, config)
    endpoint_stability = _endpoint_stability(panel, config)

    primary_shocks = primary[
        primary["term"].eq("brand_index_innovation")
    ].sort_values("horizon_weeks")
    jackknife_summary = jackknife.groupby("horizon_weeks").agg(
        minimum_estimate=("estimate", "min"),
        maximum_estimate=("estimate", "max"),
        positive_share=("estimate", lambda values: float((values > 0).mean())),
    ).reset_index()
    any_holm_10 = bool((primary_shocks["p_value_holm"] <= 0.10).any())

    _write(daily, target, "rolling_abnormal_returns_daily")
    _write(panel, target, "stock_brand_response_weekly")
    _write(coefficients, target, "stock_response_coefficients")
    _write(jackknife, target, "leave_one_quarter_out_stability")
    _write(endpoint_stability, target, "endpoint_stability")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": (
            "exploratory_familywise_signal_detected"
            if any_holm_10 else "exploratory_no_familywise_signal"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "accepted_for_profit_conversion": False,
        "accepted_for_causal_valuation": False,
        "factor_model": {
            "method": "rolling_prior_120_trading_day_market_model",
            "training_window_trading_days": window,
            "factors": [
                "contemporaneous_HSI_return",
                "latest_Nasdaq100_in_HKD_return_available_before_HK_session",
            ],
            "look_ahead": False,
            "daily_observations": int(len(daily)),
        },
        "brand_index_shock": {
            "definition": (
                "actual weekly Brand Index change minus its prediction from "
                "the preceding rolling history"
            ),
            "training_window_weeks": int(
                config["brand_index_innovation"]["estimation_window_weeks"]
            ),
            "minimum_history_weeks": int(
                config["brand_index_innovation"]["minimum_history_weeks"]
            ),
            "innovation_observations": int(
                panel["brand_index_innovation"].notna().sum()
            ),
            "look_ahead": False,
        },
        "horizon_results": [{
            "horizon_weeks": int(row["horizon_weeks"]),
            "abnormal_return_percentage_points_per_BI_innovation_point": (
                100.0 * float(row["estimate"])
            ),
            "robust_se_percentage_points": 100.0 * float(row["robust_se"]),
            "lower_95_percentage_points": 100.0 * float(row["lower_95"]),
            "upper_95_percentage_points": 100.0 * float(row["upper_95"]),
            "p_value_normal_approx": float(row["p_value_normal_approx"]),
            "p_value_holm": float(row["p_value_holm"]),
        } for _, row in primary_shocks.iterrows()],
        "multiple_testing": {
            "method": "Holm family-wise correction",
            "family": "four frozen response horizons: 0, 1, 4 and 13 weeks",
            "any_adjusted_p_at_or_below_0_10": any_holm_10,
        },
        "reverse_timing_placebo": {
            "lead_weeks": placebo_lead,
            "estimate_percentage_points": 100.0 * float(
                placebo[placebo["term"].eq("future_brand_index_innovation")]
                .iloc[0]["estimate"]
            ),
            "p_value_normal_approx": float(
                placebo[placebo["term"].eq("future_brand_index_innovation")]
                .iloc[0]["p_value_normal_approx"]
            ),
        },
        "leave_one_quarter_out_stability": [
            {
                "horizon_weeks": int(row["horizon_weeks"]),
                "minimum_percentage_points": 100.0 * float(row["minimum_estimate"]),
                "maximum_percentage_points": 100.0 * float(row["maximum_estimate"]),
                "positive_share": float(row["positive_share"]),
            }
            for _, row in jackknife_summary.iterrows()
        ],
        "endpoint_stability": [{
            "sample_endpoint": row["sample_endpoint"].date().isoformat(),
            "horizon_weeks": int(row["horizon_weeks"]),
            "estimate_percentage_points": 100.0 * float(row["estimate"]),
            "robust_se_percentage_points": 100.0 * float(row["robust_se"]),
            "p_value_normal_approx": float(row["p_value_normal_approx"]),
            "observations": int(row["observations"]),
        } for _, row in endpoint_stability.iterrows()],
        "diagnostics": {
            "primary": primary_diagnostics,
            "raw_change_sensitivity": raw_diagnostics,
            "reverse_timing_placebo": placebo_diag,
        },
        "inputs": {
            name: {"path": path, "sha256": _sha256(path)}
            for name, path in config["inputs"].items()
        },
        "interpretation": (
            "The coefficient maps an unexpected Brand Index point to cumulative "
            "factor-adjusted equity return. It is not a profit coefficient. A "
            "market-value translation additionally requires dated market "
            "capitalisation; any cash-flow equivalent requires WACC, growth and "
            "persistence assumptions."
        ),
        "guardrails": [
            "Stock prices are never regressed in levels.",
            "Every factor forecast and Brand Index prediction uses prior data only.",
            "The four horizons are frozen and evaluated as one Holm-adjusted family.",
            "Earnings announcement weeks and two following weeks are controlled.",
            "The Brand Index is a calibrated Lenovo search-salience index, so the shock is unexpected salience, not complete brand equity.",
            "No stock coefficient is accepted as a profit or causal sponsorship conversion.",
        ],
    }
    (target / "stock_response_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default="config/experiments/stock_brand_response_v2.yaml"
    )
    args = parser.parse_args()
    build_stock_response(args.config)
