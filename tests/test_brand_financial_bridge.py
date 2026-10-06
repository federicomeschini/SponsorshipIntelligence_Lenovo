import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/brand_financial_bridge_v1"


def test_financial_bridge_uses_direct_profit_and_is_not_accepted():
    manifest = json.loads(
        (EXPERIMENT / "financial_bridge_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "exploratory_no_approved_monetization_coefficient"
    assert manifest["accepted_for_valuation"] is False
    assert manifest["canonical_contracts_replaced"] == []
    assert manifest["primary_profit_mapping"]["model"] == "margin_macro"
    assert manifest["margin_model_sensitivity"]["all_signs_positive"] is False
    assert "not profit" in manifest["stock_corroboration"]["interpretation"]


def test_quarterly_panel_contains_official_lenovo_periods_and_controls():
    panel = pd.read_parquet(EXPERIMENT / "quarterly_financial_bridge.parquet")
    # FY22/23 Q1 through FY26/27 Q1 (added October 2026, ADR-0027).
    assert len(panel) == 17
    assert panel["revenue_usd_m"].gt(0).all()
    assert panel["adjusted_net_income_usd_m"].gt(0).all()
    assert panel["source_url"].str.startswith(
        "https://investor.lenovo.com/"
    ).all()
    assert {
        "brand_index", "category_demand_z", "hsi_log_return",
        "ndx_hkd_log_return", "lenovo_event_count",
    }.issubset(panel.columns)


def test_stock_bridge_uses_factor_adjusted_returns_not_price_levels():
    coefficients = pd.read_parquet(EXPERIMENT / "stock_model_coefficients.parquet")
    assert set(coefficients["model"]) == {
        "daily_lenovo_factor_model", "weekly_abnormal_return_brand_index",
    }
    weekly = pd.read_parquet(EXPERIMENT / "stock_brand_index_weekly.parquet")
    assert "abnormal_return" in weekly
    assert "stock_price" not in weekly
    assert len(weekly) > 200


def test_monetization_cases_are_mechanical_and_never_accepted():
    scenarios = pd.read_parquet(
        EXPERIMENT / "illustrative_monetization_scenarios.parquet"
    )
    assert set(scenarios["case"]) == {
        "one_brand_index_point",
        "announcement_period_candidate",
        "world_cup_total_sponsorship_path_interim",
        "world_cup_incremental_tournament_interim",
    }
    assert not scenarios["accepted_for_valuation"].any()
    unit = scenarios[scenarios["case"].eq("one_brand_index_point")].iloc[0]
    assert unit["quarterly_adjusted_profit_usd_m_lower_95"] < 0
    assert unit["quarterly_adjusted_profit_usd_m_upper_95"] > 0
