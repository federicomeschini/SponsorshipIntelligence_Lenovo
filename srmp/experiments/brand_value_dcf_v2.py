"""Brand value by discounted branded earnings (ISO 10668 income approach, earnings split; ADR-0045).

Economic profit (NOPAT less a capital charge on invested capital) is forecast
from Lenovo's latest audited year; the brand contribution factor, the brand's
share of the Lenovo-specific explained share-price movement (ADR-0044), is the
role of brand, so branded earnings = factor x economic profit. They are
discounted at a CAPM WACC with a Gordon terminal value. The FIFA-added brand
value applies the FIFA-specific uplift (ADR-0043) to this brand value.
Successor of brand_value_dcf_v1 (ADR-0033, retired by ADR-0040).
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
from srmp.experiments.sponsorship_total_return_v3 import _market_cap_usd_m


def _fiscal_revenue(quarterly: pd.DataFrame) -> pd.Series:
    totals = quarterly.groupby("fiscal_year", sort=False).agg(
        revenue=("revenue_usd_m", "sum"), quarters=("fiscal_quarter", "nunique"))
    return totals.loc[totals["quarters"].eq(4), "revenue"]


def _wacc(config: dict[str, Any], market: pd.DataFrame, shares: int, debt: float, tax: float) -> dict[str, float]:
    spec = config["discount_rate"]
    rates = market[market["factor_id"].eq("UST10Y")].sort_values("date")
    risk_free = float(rates["close"].iloc[-1]) / 100.0
    risk_free_date = str(pd.Timestamp(rates["date"].iloc[-1]).date())
    prices = market[market["factor_id"].isin(["LENOVO", "USDHKD", spec["beta_benchmark"]])].pivot_table(
        index="date", columns="factor_id", values="close").ffill().dropna()
    weekly = prices.resample("W-FRI").last()
    lenovo_usd = weekly["LENOVO"] / weekly["USDHKD"]
    returns = pd.DataFrame({
        "lenovo": np.log(lenovo_usd).diff(), "benchmark": np.log(weekly[spec["beta_benchmark"]]).diff(),
    }).dropna().tail(int(spec["beta_window_weeks"]))
    raw_beta = float(np.cov(returns["lenovo"], returns["benchmark"])[0, 1] / returns["benchmark"].var())
    beta = 0.67 * raw_beta + 0.33 if spec["beta_adjustment"] == "blume" else raw_beta
    cost_equity = risk_free + beta * float(spec["equity_risk_premium"]) + float(spec["brand_specific_premium"])
    cost_debt = (risk_free + float(spec["pre_tax_debt_spread"])) * (1 - tax)
    equity_value, price_date, price_hkd, fx = _market_cap_usd_m(market, market["date"].max(), shares)
    weight_debt = debt / (debt + equity_value)
    return {
        "risk_free": risk_free, "risk_free_date": risk_free_date, "raw_beta": raw_beta, "beta": beta,
        "beta_benchmark": spec["beta_benchmark"], "beta_adjustment": spec["beta_adjustment"],
        "pre_tax_debt_spread": float(spec["pre_tax_debt_spread"]), "tax_rate_used": tax,
        "equity_value_date": str(price_date.date()), "share_price_hkd": price_hkd, "usd_hkd": fx, "shares": shares,
        "equity_risk_premium": float(spec["equity_risk_premium"]), "cost_of_equity": cost_equity,
        "after_tax_cost_of_debt": cost_debt, "equity_value_usd_m": equity_value, "debt_usd_m": debt,
        "weight_debt": weight_debt, "wacc": (1 - weight_debt) * cost_equity + weight_debt * cost_debt,
        "beta_weeks": int(len(returns)),
    }


def _forecast(base: dict[str, float], start_growth: float, terminal_growth: float, years: int,
              wacc: float) -> pd.DataFrame:
    """Economic-profit forecast; growth fades linearly from start to terminal."""
    rows = []
    revenue, capital = base["revenue"], base["invested_capital"]
    turnover = revenue / capital
    for year in range(1, years + 1):
        growth = start_growth + (terminal_growth - start_growth) * (year - 1) / max(years - 1, 1)
        opening_capital = capital
        revenue *= 1 + growth
        capital = revenue / turnover
        nopat = revenue * base["operating_margin"] * (1 - base["tax_rate"])
        charge = wacc * opening_capital
        rows.append({"year": year, "revenue_growth": growth, "revenue_usd_m": revenue,
                     "nopat_usd_m": nopat, "opening_invested_capital_usd_m": opening_capital,
                     "capital_charge_usd_m": charge, "economic_profit_usd_m": nopat - charge,
                     "closing_invested_capital_usd_m": capital})
    return pd.DataFrame(rows)


def _brand_value(forecast: pd.DataFrame, role: float, wacc: float, terminal_growth: float) -> dict[str, float]:
    branded = forecast["economic_profit_usd_m"] * role
    factors = (1 + wacc) ** -forecast["year"]
    explicit = float((branded * factors).sum())
    final = forecast.iloc[-1]
    # First terminal-year economic profit: NOPAT grows at g; the charge is on closing capital.
    next_ep = final["nopat_usd_m"] * (1 + terminal_growth) - wacc * final["closing_invested_capital_usd_m"]
    terminal = role * next_ep / (wacc - terminal_growth) * float(factors.iloc[-1])
    return {"explicit_pv_usd_m": explicit, "terminal_pv_usd_m": terminal, "brand_value_usd_m": explicit + terminal}


def build_brand_value_dcf(config_path: str = "config/experiments/brand_value_dcf_v2.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs = config["inputs"]
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    annual = pd.read_csv(inputs["annual_financials"]).set_index("fiscal_year")
    row = annual.loc[config["base_fiscal_year"]]
    tax_rate = float(row["taxation_usd_m"] / row["profit_before_tax_usd_m"])
    invested = float(row["total_equity_usd_m"] + row["total_debt_usd_m"] - row["cash_usd_m"]
                     - row["short_term_investments_usd_m"])
    base = {"revenue": float(row["revenue_usd_m"]),
            "operating_margin": float(row["operating_profit_usd_m"] / row["revenue_usd_m"]),
            "tax_rate": tax_rate, "invested_capital": invested}
    fiscal = _fiscal_revenue(pd.read_csv(inputs["quarterly_financials"]))
    position = list(fiscal.index).index(config["base_fiscal_year"])
    start_growth = float((fiscal.iloc[position] / fiscal.iloc[position - 3]) ** (1 / 3) - 1)
    terminal_growth = float(config["revenue"]["terminal_growth"])

    market = pd.read_parquet(inputs["market_prices"])
    market["date"] = pd.to_datetime(market["date"])
    shares = int(pd.read_csv(inputs["market_valuation_reference"]).iloc[-1]["ordinary_shares_outstanding"])
    wacc = _wacc(config, market, shares, float(row["total_debt_usd_m"]), tax_rate)

    dominance = json.loads(Path(inputs["dominance_manifest"]).read_text(encoding="utf-8"))
    # Role of brand = the brand contribution factor (ADR-0044) and its bootstrap band.
    role = float(dominance["values"]["brand_share"])
    band = [float(v) for v in dominance["values"]["brand_share_90pct"]]
    roles = {"brand_contribution_factor": role, "factor_bootstrap_p05": band[0], "factor_bootstrap_p95": band[1]}

    forecast = _forecast(base, start_growth, terminal_growth, int(config["forecast_years"]), wacc["wacc"])
    forecast["branded_earnings_usd_m"] = forecast["economic_profit_usd_m"] * role
    forecast["discount_factor"] = (1 + wacc["wacc"]) ** -forecast["year"]
    primary = _brand_value(forecast, role, wacc["wacc"], terminal_growth)
    primary["terminal_share_of_value"] = primary["terminal_pv_usd_m"] / primary["brand_value_usd_m"]
    inputs_used = {
        "annual_financials": {fy: {k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else v)
                                   for k, v in annual.loc[fy].items()} for fy in annual.index},
        "invested_capital_components_usd_m": {
            "total_equity": float(row["total_equity_usd_m"]), "total_debt": float(row["total_debt_usd_m"]),
            "less_cash": float(row["cash_usd_m"]), "less_short_term_investments": float(row["short_term_investments_usd_m"])},
        "fiscal_year_revenue_usd_m": {k: float(v) for k, v in fiscal.items()},
        "start_growth_years": [fiscal.index[position - 3], fiscal.index[position]],
    }

    # Sensitivities: role of brand x WACC x terminal growth.
    grid_rows = []
    for role_name, role_value in [*roles.items(), *[(f"grid_{v:g}", v) for v in config["role_of_brand"]["sensitivity_grid"]]]:
        for dw in config["sensitivity"]["wacc_shift"]:
            for dg in config["sensitivity"]["terminal_growth_shift"]:
                rate, growth = wacc["wacc"] + dw, terminal_growth + dg
                path = _forecast(base, start_growth, growth, int(config["forecast_years"]), rate)
                grid_rows.append({"role_of_brand": role_name, "role_value": role_value, "wacc": rate,
                                  "terminal_growth": growth,
                                  **_brand_value(path, role_value, rate, growth)})
    grid = pd.DataFrame(grid_rows)

    # FIFA-added brand value: FIFA-specific uplift (ADR-0043) x this brand value; elasticity as in the dominance chain.
    fs = dominance["fifa_specific_incremental_brand_value"]
    elasticity = float(dominance["primary_result"]["brand_value_elasticity_to_brand_share"])
    counterfactual = float(dominance["primary_result"]["counterfactual_index_level"])

    def sponsorship(brand_value: float) -> dict[str, Any]:
        return {"fifa_added_brand_value_usd_m": {name: elasticity * pct / 100 * brand_value for name, pct in fs["uplift_pct"].items()},
                "value_per_brand_index_point_usd_m": elasticity * brand_value / counterfactual}

    by_role = {name: {"role_of_brand": value,
                      **(lambda bv: {"brand_value_usd_m": bv, **sponsorship(bv)})(
                          _brand_value(forecast, value, wacc["wacc"], terminal_growth)["brand_value_usd_m"])}
               for name, value in roles.items()}
    ep_pv = primary["brand_value_usd_m"] / role if role else None
    references = {
        "market_cap_route_usd_m": float(dominance["values"]["brand_value_usd_m"]),
        "brand_finance_2025_usd_m": float(config["cross_check"]["brand_finance_2025_brand_value_usd_m"]),
        "interbrand_2015_usd_m": float(config["cross_check"]["interbrand_2015_brand_value_usd_m"]),
    }
    implied_roles = {name: value / ep_pv for name, value in references.items()} if ep_pv else {}

    _write(forecast, target, "economic_profit_forecast")
    _write(grid, target, "sensitivity_grid")
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "standard": "ISO 10668 income approach, brand earnings split on economic profit",
        "valuation_date": config["valuation_date"],
        "base_year": {"fiscal_year": config["base_fiscal_year"], **base,
                      "return_on_invested_capital": base["revenue"] * base["operating_margin"]
                      * (1 - tax_rate) / invested},
        "revenue_growth": {"start": start_growth, "terminal": terminal_growth,
                           "rule": config["revenue"]["start_growth_rule"]},
        "discount_rate": wacc,
        "role_of_brand": {"definition": "brand contribution factor: brand share of the Lenovo-specific explained share-price movement (ADR-0044)",
                          "values": roles},
        "economic_profit_pv_usd_m": ep_pv,
        "inputs_used": inputs_used,
        "primary_result": {
            "role_of_brand": role, **primary, **sponsorship(primary["brand_value_usd_m"]),
            "fifa_specific_uplift_pct": fs["uplift_pct"], "elasticity_to_brand_share": elasticity,
        },
        "by_role_definition": by_role,
        "sensitivity_range_usd_m": {
            name: [float(group["brand_value_usd_m"].min()), float(group["brand_value_usd_m"].max())]
            for name, group in grid.groupby("role_of_brand", sort=False)
        },
        "cross_check": {**references, "role_of_brand_implied": implied_roles,
                        "sources": {"brand_finance": config["cross_check"]["brand_finance_source"],
                                    "interbrand": config["cross_check"]["interbrand_source"]}},
        "disclosures": [
            "Role of brand is the brand contribution factor (ADR-0044): the brand's share of the Lenovo-specific share-price drivers stands in for ISO 10668's behavioural analysis of the brand's contribution to demand. The market data alone do not identify it (placebo, brand_value_dominance_v1).",
            "Economic profit uses FY25/26 reported operating margin and effective tax rate, constant capital turnover and a linear growth fade.",
            "FIFA-added value assumes brand value proportional to brand share of attention (elasticity 1) and the FIFA-specific uplift (ADR-0043).",
        ],
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
    }
    (target / "brand_value_dcf_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/brand_value_dcf_v2.yaml")
    args = parser.parse_args()
    build_brand_value_dcf(args.config)
