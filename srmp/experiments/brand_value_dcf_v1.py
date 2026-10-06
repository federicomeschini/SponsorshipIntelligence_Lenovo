"""Brand value by discounted branded earnings (ISO 10668 income approach, ADR-0033).

Economic profit (NOPAT less a capital charge on invested capital) is
forecast from Lenovo's latest audited year, a role-of-brand share of it is
taken as branded earnings, and those are discounted at a CAPM WACC with a
Gordon terminal value. The owner's assumption sets the role of brand equal to
the brand's share of share-price formation (ADR-0031). The sponsorship's
incremental brand value follows the Index-lift chain of ADR-0032.
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
    equity_value = _market_cap_usd_m(market, market["date"].max(), shares)[0]
    weight_debt = debt / (debt + equity_value)
    return {
        "risk_free": risk_free, "raw_beta": raw_beta, "beta": beta,
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


def build_brand_value_dcf(config_path: str = "config/experiments/brand_value_dcf_v1.yaml") -> dict[str, Any]:
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
    weights = pd.read_parquet(Path(inputs["dominance_manifest"]).parent / "dominance_weights.parquet")
    full = weights[weights["model"].eq("brand_full_sample")].set_index("group")
    sign = dominance["coefficients"]["brand_full_sample"]["brand"]["sign"]
    roles = {
        "share_of_price_formation": float(dominance["values"]["brand_share_of_price_formation"]),
        "firm_specific_share": float(sign * full.loc["brand", "dominance_r2"]
                                     / full.drop(index="market")["dominance_r2"].sum()),
    }
    role = roles[config["role_of_brand"]["primary"]]

    forecast = _forecast(base, start_growth, terminal_growth, int(config["forecast_years"]), wacc["wacc"])
    forecast["branded_earnings_usd_m"] = forecast["economic_profit_usd_m"] * role
    forecast["discount_factor"] = (1 + wacc["wacc"]) ** -forecast["year"]
    primary = _brand_value(forecast, role, wacc["wacc"], terminal_growth)

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

    chain = dominance["primary_result"]
    uplift = float(chain["salience_uplift_pct"]) / 100
    elasticity = float(chain["brand_value_elasticity_to_salience"])
    headroom = float(chain["counterfactual_index_level"] - chain["zero_interest_index_level"])
    world_cup = json.loads(Path(inputs["world_cup_estimate_manifest"]).read_text(encoding="utf-8"))
    wc_lift = world_cup["primary"]["primary_exposure_weighted_gap"]

    def sponsorship(brand_value: float) -> dict[str, float | None]:
        per_point = elasticity * brand_value / headroom
        return {"incremental_brand_value_usd_m": elasticity * uplift * brand_value,
                "coefficient_usd_m_per_index_point": per_point,
                "world_cup_incremental_brand_value_usd_m": per_point * wc_lift if wc_lift is not None else None}

    by_role = {name: {"role_of_brand": value,
                      **(lambda bv: {"brand_value_usd_m": bv, **sponsorship(bv)})(
                          _brand_value(forecast, value, wacc["wacc"], terminal_growth)["brand_value_usd_m"])}
               for name, value in roles.items()}
    cross = float(config["cross_check"]["brand_finance_2025_brand_value_usd_m"])
    implied_role = cross / (primary["brand_value_usd_m"] / role) if role else None

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
        "role_of_brand": {"primary_definition": config["role_of_brand"]["primary"], "values": roles},
        "primary_result": {
            "role_of_brand": role, **primary, **sponsorship(primary["brand_value_usd_m"]),
            "salience_uplift_pct": 100 * uplift, "elasticity_to_salience": elasticity,
        },
        "by_role_definition": by_role,
        "sensitivity_range_usd_m": {
            name: [float(group["brand_value_usd_m"].min()), float(group["brand_value_usd_m"].max())]
            for name, group in grid.groupby("role_of_brand", sort=False)
        },
        "cross_check": {"brand_finance_2025_usd_m": cross,
                        "role_of_brand_implied_by_brand_finance": implied_role,
                        "source": config["cross_check"]["brand_finance_source"]},
        "disclosures": [
            "Role of brand is the owner's assumption (ADR-0031): the brand's share of share-price formation stands in for ISO 10668's behavioural analysis of the brand's contribution to demand.",
            "Economic profit uses FY25/26 reported operating margin and effective tax rate, constant capital turnover and a linear growth fade.",
            "Incremental sponsorship value assumes brand value proportional to search salience (ADR-0032) and an unaccepted synthetic-control lift.",
        ],
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
    }
    (target / "brand_value_dcf_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/brand_value_dcf_v1.yaml")
    args = parser.parse_args()
    build_brand_value_dcf(args.config)
