"""Exploratory Brand Index-to-profit bridge with stock returns as corroboration."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import norm

from srmp.experiments.sponsorship_counterfactual_v1 import (
    _monday,
    _weekly_event_controls,
)
from srmp.experiments.world_cup_impact_v1_estimator import interim_world_cup_gaps


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(frame: pd.DataFrame, target: Path, name: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target / f"{name}.parquet", index=False)
    frame.to_csv(target / f"{name}.csv", index=False)


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ols(
    frame: pd.DataFrame,
    outcome: str,
    regressors: list[str],
    model: str,
    covariance: str = "HC3",
    hac_lags: int = 0,
) -> tuple[pd.DataFrame, dict[str, Any], np.ndarray]:
    selected = frame[[outcome] + regressors].dropna().astype(float)
    y = selected[outcome].to_numpy()
    x = np.column_stack([np.ones(len(selected)), selected[regressors].to_numpy()])
    names = ["intercept"] + regressors
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    residual = y - x @ beta
    if covariance == "HC3":
        leverage = np.einsum("ij,jk,ik->i", x, xtx_inv, x)
        adjusted = residual / np.clip(1.0 - leverage, 1e-8, None)
        scores = x * adjusted[:, None]
        meat = scores.T @ scores
    elif covariance == "HAC":
        scores = x * residual[:, None]
        meat = scores.T @ scores
        for lag in range(1, hac_lags + 1):
            weight = 1.0 - lag / (hac_lags + 1.0)
            gamma = scores[lag:].T @ scores[:-lag]
            meat += weight * (gamma + gamma.T)
    else:
        raise ValueError(f"Unknown covariance estimator: {covariance}")
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    z = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)
    p = 2.0 * norm.sf(np.abs(z))
    rows = pd.DataFrame({
        "model": model,
        "outcome": outcome,
        "term": names,
        "estimate": beta,
        "robust_se": se,
        "lower_95": beta - 1.96 * se,
        "upper_95": beta + 1.96 * se,
        "p_value_normal_approx": p,
        "covariance": covariance,
    })
    tss = float(np.square(y - y.mean()).sum())
    diagnostics = {
        "model": model,
        "outcome": outcome,
        "regressors": regressors,
        "observations": int(len(selected)),
        "parameters": int(x.shape[1]),
        "r_squared": 1.0 - float(residual @ residual) / tss if tss > 0 else np.nan,
        "covariance": covariance,
        "hac_lags": hac_lags if covariance == "HAC" else None,
    }
    return rows, diagnostics, residual


def _build_quarterly_panel(config: dict[str, Any]) -> pd.DataFrame:
    financials = pd.read_csv(config["inputs"]["quarterly_financials"])
    financials["calendar_quarter"] = pd.PeriodIndex(
        financials["calendar_quarter"], freq="Q"
    )
    index = pd.read_parquet(config["inputs"]["brand_index"])
    index["week"] = pd.to_datetime(index["week"])
    index["calendar_quarter"] = index["week"].dt.to_period("Q")
    index_q = index.groupby("calendar_quarter", as_index=True).agg(
        brand_index=("index_level", "mean"),
        brand_index_weeks=("week", "nunique"),
    )

    trends = pd.read_parquet(config["inputs"]["joint_donor_trends"])
    trends["week"] = _monday(trends["week"])
    query_ids = config["category_demand_queries"]
    demand = trends[trends["query_id"].isin(query_ids)].pivot(
        index="week", columns="query_id", values="interest_common_scale"
    )
    demand_z = (demand - demand.mean()) / demand.std(ddof=0)
    demand_z["calendar_quarter"] = demand_z.index.to_period("Q")
    demand_q = (
        demand_z.groupby("calendar_quarter")[query_ids].mean().mean(axis=1)
        .rename("category_demand_z")
    )

    market = pd.read_parquet(config["inputs"]["market_prices"])
    market["date"] = pd.to_datetime(market["date"])
    market["calendar_quarter"] = market["date"].dt.to_period("Q")
    market_q = market.sort_values("date").groupby(
        ["factor_id", "calendar_quarter"]
    ).agg(first=("adj_close", "first"), last=("adj_close", "last"))
    market_q["log_return"] = np.log(market_q["last"] / market_q["first"])
    market_q = market_q["log_return"].unstack("factor_id")
    market_q["ndx_hkd_log_return"] = market_q["NDX"] + market_q["USDHKD"]
    market_q = market_q.rename(columns={"HSI": "hsi_log_return"})

    events = pd.read_csv(config["inputs"]["product_campaign_events"])
    events["event_timestamp_utc"] = pd.to_datetime(
        events["event_timestamp_utc"], utc=True
    )
    events["calendar_quarter"] = (
        events["event_timestamp_utc"].dt.tz_convert(None).dt.to_period("Q")
    )
    event_q = events.groupby("calendar_quarter").agg(
        lenovo_event_count=("event_id", "size"),
        confirmed_event_count=("evidence_status", lambda x: int((x == "confirmed").sum())),
    )

    panel = (
        financials.set_index("calendar_quarter")
        .join(index_q)
        .join(demand_q)
        .join(market_q[["hsi_log_return", "ndx_hkd_log_return"]])
        .join(event_q)
        .reset_index()
    )
    panel[["lenovo_event_count", "confirmed_event_count"]] = panel[
        ["lenovo_event_count", "confirmed_event_count"]
    ].fillna(0)
    panel["adjusted_net_margin_pp"] = (
        100.0 * panel["adjusted_net_income_usd_m"] / panel["revenue_usd_m"]
    )
    panel["delta_brand_index"] = panel["brand_index"].diff()
    panel["delta_category_demand_z"] = panel["category_demand_z"].diff()
    panel["delta_adjusted_net_margin_pp"] = panel["adjusted_net_margin_pp"].diff()
    panel["delta_log_adjusted_net_income"] = np.log(
        panel["adjusted_net_income_usd_m"]
    ).diff()
    panel["delta_log_revenue"] = np.log(panel["revenue_usd_m"]).diff()
    for quarter in ("Q2", "Q3", "Q4"):
        panel[f"fiscal_{quarter.lower()}"] = panel["fiscal_quarter"].eq(quarter).astype(float)
    panel["calendar_quarter"] = panel["calendar_quarter"].astype(str)
    return panel


def _build_stock_bridge(
    config: dict[str, Any],
    index: pd.DataFrame,
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    market = pd.read_parquet(config["inputs"]["market_prices"])
    market["date"] = pd.to_datetime(market["date"])
    levels = market.pivot(index="date", columns="factor_id", values="adj_close").sort_index()
    returns = np.log(levels).diff()
    hk = returns[["LENOVO", "HSI"]].dropna().reset_index()
    ndx_hkd_level = levels["NDX"] * levels["USDHKD"].ffill()
    ndx = np.log(ndx_hkd_level).diff().dropna().rename("ndx_hkd_lagged").reset_index()
    daily = pd.merge_asof(
        hk.sort_values("date"),
        ndx.sort_values("date"),
        on="date",
        direction="backward",
        allow_exact_matches=False,
    ).dropna()
    factor_coefficients, factor_diag, residual = _ols(
        daily,
        "LENOVO",
        ["HSI", "ndx_hkd_lagged"],
        "daily_lenovo_factor_model",
        covariance="HAC",
        hac_lags=5,
    )
    daily["abnormal_return"] = residual
    daily["week"] = daily["date"] - pd.to_timedelta(daily["date"].dt.weekday, unit="D")
    weekly = daily.groupby("week", as_index=False).agg(
        abnormal_return=("abnormal_return", "sum"),
        lenovo_log_return=("LENOVO", "sum"),
        trading_days=("date", "size"),
    )
    index_weekly = index[["week", "index_level"]].copy()
    index_weekly["delta_brand_index"] = index_weekly["index_level"].diff()
    event_controls = _weekly_event_controls(events, carryover_weeks=1).reset_index()
    weekly = index_weekly.merge(weekly, on="week", how="inner").merge(
        event_controls, on="week", how="left"
    )
    controls = [
        "product_campaign_control", "promotion_calendar_control", "mixed_event_control"
    ]
    weekly[controls] = weekly[controls].fillna(0.0)
    weekly["lag_abnormal_return"] = weekly["abnormal_return"].shift()
    stock_coefficients, stock_diag, _ = _ols(
        weekly,
        "abnormal_return",
        config["stock_model"]["regressors"],
        "weekly_abnormal_return_brand_index",
        covariance="HAC",
        hac_lags=int(config["stock_model"]["hac_lags"]),
    )
    return daily, weekly, pd.concat(
        [factor_coefficients, stock_coefficients], ignore_index=True
    ), {"factor_model": factor_diag, "brand_index_model": stock_diag}


def build_bridge(
    config_path: str = "config/experiments/brand_financial_bridge_v1.yaml",
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)
    quarterly = _build_quarterly_panel(config)

    coefficient_frames = []
    model_diagnostics = []
    for model, spec in config["profit_models"]["specifications"].items():
        coefficients, diagnostics, _ = _ols(
            quarterly, spec["outcome"], spec["regressors"], model, covariance="HC3"
        )
        coefficient_frames.append(coefficients)
        model_diagnostics.append(diagnostics)
    profit_coefficients = pd.concat(coefficient_frames, ignore_index=True)

    index = pd.read_parquet(config["inputs"]["brand_index"])
    index["week"] = pd.to_datetime(index["week"])
    events = pd.read_csv(config["inputs"]["product_campaign_events"])
    stock_daily, stock_weekly, stock_coefficients, stock_diagnostics = _build_stock_bridge(
        config, index, events
    )

    primary_name = config["profit_models"]["primary"]
    primary = profit_coefficients[
        profit_coefficients["model"].eq(primary_name)
        & profit_coefficients["term"].eq("delta_brand_index")
    ].iloc[0]
    growth = profit_coefficients[
        profit_coefficients["model"].eq("profit_growth_revenue_macro")
        & profit_coefficients["term"].eq("delta_brand_index")
    ].iloc[0]
    stock = stock_coefficients[
        stock_coefficients["model"].eq("weekly_abnormal_return_brand_index")
        & stock_coefficients["term"].eq("delta_brand_index")
    ].iloc[0]
    latest = quarterly.iloc[-1]
    latest_revenue = float(latest["revenue_usd_m"])
    margin_usd = {
        "estimate_usd_m_per_quarter": float(primary["estimate"]) / 100.0 * latest_revenue,
        "lower_95_usd_m_per_quarter": float(primary["lower_95"]) / 100.0 * latest_revenue,
        "upper_95_usd_m_per_quarter": float(primary["upper_95"]) / 100.0 * latest_revenue,
        "reference_quarter": latest["calendar_quarter"],
        "reference_revenue_usd_m": latest_revenue,
    }
    total_effect = _read_json(config["inputs"]["total_effect_manifest"])
    world_cup = interim_world_cup_gaps(
        config["inputs"]["world_cup_estimate_manifest"],
        config["inputs"]["total_effect_weekly"],
    )
    index_cases = [
        {
            "case": "one_brand_index_point",
            "delta_brand_index": 1.0,
            "role": "unit_mapping",
        },
        {
            "case": "total_sponsorship_effect",
            "delta_brand_index": float(total_effect["total_effect"]["lift_index_points"]),
            "role": "headline_total_effect_not_accepted",
        },
        {
            "case": "world_cup_total_sponsorship_path_interim",
            "delta_brand_index": float(world_cup["total_path"]),
            "role": "interim_not_pure_World_Cup_effect",
        },
        {
            "case": "world_cup_incremental_tournament_interim",
            "delta_brand_index": float(world_cup["incremental"]),
            "role": "interim_incremental_tournament_lift",
        },
    ]
    scenario_rows = []
    for case in index_cases:
        delta = case["delta_brand_index"]
        dollar_values = [
            delta * margin_usd["lower_95_usd_m_per_quarter"],
            delta * margin_usd["upper_95_usd_m_per_quarter"],
        ]
        scenario_rows.append({
            **case,
            "delta_adjusted_net_margin_pp_central": delta * float(primary["estimate"]),
            "quarterly_adjusted_profit_usd_m_central": (
                delta * margin_usd["estimate_usd_m_per_quarter"]
            ),
            "quarterly_adjusted_profit_usd_m_lower_95": min(dollar_values),
            "quarterly_adjusted_profit_usd_m_upper_95": max(dollar_values),
            "annualized_run_rate_usd_m_central": (
                4.0 * delta * margin_usd["estimate_usd_m_per_quarter"]
            ),
            "accepted_for_valuation": False,
        })
    monetization_scenarios = pd.DataFrame(scenario_rows)
    sensitivity = profit_coefficients[
        profit_coefficients["term"].eq("delta_brand_index")
        & profit_coefficients["outcome"].eq("delta_adjusted_net_margin_pp")
    ]
    stable_positive = bool((sensitivity["estimate"] > 0).all())
    primary_supported = bool(
        primary["p_value_normal_approx"] <= 0.10 and stable_positive
    )

    _write(quarterly, target, "quarterly_financial_bridge")
    _write(profit_coefficients, target, "profit_model_coefficients")
    _write(stock_daily, target, "stock_abnormal_returns_daily")
    _write(stock_weekly, target, "stock_brand_index_weekly")
    _write(stock_coefficients, target, "stock_model_coefficients")
    _write(monetization_scenarios, target, "illustrative_monetization_scenarios")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": (
            "candidate_financial_mapping_available"
            if primary_supported
            else "exploratory_no_approved_monetization_coefficient"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_contracts_replaced": [],
        "accepted_for_valuation": False,
        "primary_profit_mapping": {
            "model": primary_name,
            "unit": "adjusted_net_income_margin_percentage_points_per_one_Brand_Index_point",
            "estimate": float(primary["estimate"]),
            "robust_se": float(primary["robust_se"]),
            "lower_95": float(primary["lower_95"]),
            "upper_95": float(primary["upper_95"]),
            "p_value_normal_approx": float(primary["p_value_normal_approx"]),
            "equivalent_at_latest_quarter": margin_usd,
        },
        "controlled_profit_growth_sensitivity": {
            "unit": "approximate_percent_adjusted_net_income_per_one_Brand_Index_point",
            "log_coefficient": float(growth["estimate"]),
            "approximate_percent": 100.0 * (np.exp(float(growth["estimate"])) - 1.0),
            "lower_95_percent": 100.0 * (np.exp(float(growth["lower_95"])) - 1.0),
            "upper_95_percent": 100.0 * (np.exp(float(growth["upper_95"])) - 1.0),
            "p_value_normal_approx": float(growth["p_value_normal_approx"]),
        },
        "margin_model_sensitivity": {
            "minimum_coefficient": float(sensitivity["estimate"].min()),
            "maximum_coefficient": float(sensitivity["estimate"].max()),
            "all_signs_positive": stable_positive,
            "models": sensitivity[[
                "model", "estimate", "robust_se", "lower_95", "upper_95",
                "p_value_normal_approx"
            ]].to_dict("records"),
        },
        "stock_corroboration": {
            "unit": "weekly_abnormal_return_percentage_points_per_one_Brand_Index_point",
            "estimate": 100.0 * float(stock["estimate"]),
            "robust_se": 100.0 * float(stock["robust_se"]),
            "lower_95": 100.0 * float(stock["lower_95"]),
            "upper_95": 100.0 * float(stock["upper_95"]),
            "p_value_normal_approx": float(stock["p_value_normal_approx"]),
            "interpretation": "Market corroboration only; abnormal returns are not profit.",
        },
        "illustrative_monetization": {
            "artifact": "illustrative_monetization_scenarios.parquet",
            "reference_revenue_usd_m": latest_revenue,
            "policy": (
                "Mechanical sensitivity only; every row is unaccepted and the "
                "annualized column assumes four identical quarters without "
                "persistence or discounting."
            ),
            "rows": monetization_scenarios.to_dict("records"),
        },
        "model_diagnostics": {
            "profit_models": model_diagnostics,
            "stock_models": stock_diagnostics,
        },
        "inputs": {
            name: {"path": path, "sha256": _sha256(path)}
            for name, path in config["inputs"].items()
        },
        "decision": (
            "No coefficient is approved for sponsorship monetization because the "
            f"quarterly sample has only {quarterly['delta_brand_index'].notna().sum()} first differences and the controlled estimates are imprecise "
            "(every controlled 95% interval includes zero)"
            + ("." if stable_positive else "; model sensitivity also changes sign.")
        ),
        "guardrails": [
            "One Brand Index point is about 1% of Lenovo's brand share of attention relative to its pre-announcement level (ADR-0040).",
            "Profit is measured directly from Lenovo adjusted quarterly net income; stock price is not used as a profit proxy.",
            "Stock prices are converted to returns and factor-adjusted against HSI and lagged Nasdaq-100 in HKD.",
            "All regressions use changes or returns, never levels-on-levels.",
            "Associations are single-company and low-power; reverse causality and omitted variables remain.",
            "With-and-without incremental cash flow is the preferred direct income route when operating inputs exist; royalty relief is an independent cross-check.",
        ],
    }
    (target / "financial_bridge_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + chr(10), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default="config/experiments/brand_financial_bridge_v1.yaml"
    )
    args = parser.parse_args()
    build_bridge(args.config)
