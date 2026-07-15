import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/stock_brand_response_v2"


def test_factor_model_is_strictly_prior_and_rolling():
    daily = pd.read_parquet(EXPERIMENT / "rolling_abnormal_returns_daily.parquet")
    assert len(daily) > 800
    assert daily["factor_training_observations"].eq(120).all()
    assert (daily["factor_training_end"] < daily["date"]).all()
    assert "stock_price" not in daily.columns


def test_response_family_is_frozen_and_not_accepted_as_profit():
    manifest = json.loads(
        (EXPERIMENT / "stock_response_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "exploratory_no_familywise_signal"
    assert manifest["accepted_for_profit_conversion"] is False
    assert manifest["accepted_for_causal_valuation"] is False
    assert {row["horizon_weeks"] for row in manifest["horizon_results"]} == {
        0, 1, 4, 13
    }
    assert not manifest["multiple_testing"]["any_adjusted_p_at_or_below_0_10"]
    assert all(row["p_value_holm"] > 0.10 for row in manifest["horizon_results"])


def test_brand_index_shocks_and_earnings_controls_are_present():
    weekly = pd.read_parquet(EXPERIMENT / "stock_brand_response_weekly.parquet")
    assert weekly["brand_index_innovation"].notna().sum() >= 150
    assert weekly["earnings_control"].sum() >= 40
    events = pd.read_csv(ROOT / "data/reference/lenovo_financial_results_events.csv")
    assert len(events) == 16
    assert events["source_url"].str.startswith(
        "https://investor.lenovo.com/"
    ).all()


def test_long_horizon_signal_is_endpoint_sensitive():
    stability = pd.read_parquet(EXPERIMENT / "endpoint_stability.parquet")
    h13 = stability[stability["horizon_weeks"].eq(13)].sort_values(
        "sample_endpoint"
    )
    assert len(h13) == 3
    assert h13.iloc[0]["estimate"] < 0
    assert h13.iloc[-1]["estimate"] > 0
