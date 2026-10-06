import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT / "data/curated/experimental/market_implied_earnings_bridge_v1"
)


def test_positive_operational_mapping_is_available():
    manifest = json.loads(
        (EXPERIMENT / "market_implied_earnings_bridge_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert manifest["accepted_for_planning"] is True
    assert manifest["accepted_for_total_sponsorship_valuation"] is False
    assert (
        manifest["superseded_for_total_return_by"]
        == "sponsorship_total_return_v3"
    )
    assert manifest["accepted_for_accounting_or_causal_claim"] is False
    mapping = manifest["operational_unit_mapping"]
    # Mapping = planning beta x latest complete fiscal-year adjusted earnings.
    assert mapping["fiscal_year"] == "FY25/26"
    assert mapping["annual_adjusted_earnings_base_usd_m"] == 2049.0
    beta = manifest["selected_stock_response"]["planning_return_percent_per_BI_point"] / 100
    assert abs(mapping["annual_adjusted_earnings_usd_m_per_BI_point"] - beta * 2049.0) < 1e-9
    assert mapping["annual_adjusted_earnings_usd_m_per_BI_point"] >= 0
    assert mapping["planning_lower_usd_m_per_BI_point"] == 0
    assert mapping["planning_upper_usd_m_per_BI_point"] > 0


def test_market_cross_check_uses_official_reference():
    manifest = json.loads(
        (EXPERIMENT / "market_implied_earnings_bridge_manifest.json")
        .read_text(encoding="utf-8")
    )
    cross_check = manifest["market_value_cross_check"]
    assert cross_check["ordinary_shares_outstanding"] == 12_404_659_302
    assert cross_check["official_market_cap_hkd_m"] == 113_500
    assert abs(
        cross_check["equity_value_divided_by_multiple_usd_m"]
        - manifest["operational_unit_mapping"][
            "annual_adjusted_earnings_usd_m_per_BI_point"
        ]
    ) < 1e-10


def test_scenarios_keep_calibration_and_attribution_separate():
    scenarios = pd.read_parquet(
        EXPERIMENT / "market_implied_earnings_scenarios.parquet"
    )
    assert scenarios["calibration_accepted_for_planning"].all()
    assert scenarios["attribution_accepted"].sum() == 1
    assert not scenarios["accepted_for_accounting_or_causal_claim"].any()
