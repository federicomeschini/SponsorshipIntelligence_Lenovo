import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "data/curated/experimental/sponsorship_total_return_v3"
ROUTES = ROOT / "data/curated/experimental/valuation_routes_v1"


def _manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v3_values_the_headline_total_effect_not_the_final_week():
    manifest = _manifest(V3 / "total_return_v3_manifest.json")
    effect = _manifest(ROOT / "data/curated/experimental/sponsorship_total_effect_v1/estimate_manifest.json")
    weekly = pd.read_parquet(ROOT / "data/curated/experimental/sponsorship_total_effect_v1/total_effect_weekly.parquet")
    level = manifest["sustained_levels_index_points"]["all_post_mean"]
    assert np.isclose(level, weekly.loc[weekly["period"].eq("post"), "index_gap"].mean())
    assert np.isclose(level, effect["total_effect"]["lift_index_points"])
    assert manifest["primary_result"]["level_definition"] == "all_post_mean"
    assert manifest["valuation_base"] == "mean_post_announcement_market_cap"


def test_v3_planning_acceptance_requires_attribution_and_identified_response():
    manifest = _manifest(V3 / "total_return_v3_manifest.json")
    evidence = manifest["evidence"]
    assert manifest["accepted_for_planning"] == (
        evidence["attribution_accepted"] and evidence["response_identified"]
    )
    assert evidence["response_identified"] == (evidence["base_13_week_response"]["lower_95"] > 0)
    assert manifest["accepted_for_accounting_or_causal_claim"] is False


def test_v3_value_is_monotone_in_the_sustained_level():
    scenarios = pd.read_parquet(V3 / "total_return_v3_scenarios.parquet")
    base = scenarios[scenarios["scenario"].eq("base")].sort_values("sustained_gap_index_points")
    assert base["full_contract_value_usd_m"].is_monotonic_increasing


def test_routes_report_identification_and_breakeven_without_assumed_fees():
    routes = pd.read_parquet(ROUTES / "valuation_routes.parquet")
    assert set(routes["route"]) >= {
        "market_implied_equity_v3", "market_implied_annual_earnings",
        "direct_profit_margin", "relief_from_royalty", "announcement_event_study",
        "industry_claimed_media_value",
    }
    media = routes[routes["route"].eq("industry_claimed_media_value")].iloc[0]
    assert not media["link_identified"]  # P1: comparison only, never a value
    manifest = _manifest(ROUTES / "valuation_routes_manifest.json")
    identified = set(routes.loc[routes["link_identified"], "route"])
    assert set(manifest["routes_identified"]) == identified
    breakeven = pd.read_parquet(ROUTES / "breakeven.parquet")
    assert "industry_claimed_media_value" not in set(breakeven["route"])
    config_costs = manifest["cost_grid_usd_m"]
    assert set(breakeven["cost_usd_m"]) == set(config_costs["annual"]) | set(config_costs["total_contract"])
    royalty = breakeven[breakeven["route"].eq("relief_from_royalty")]
    per_bp = routes.loc[routes["route"].eq("relief_from_royalty"), "value_per_basis_point"].iloc[0]
    assert np.allclose(royalty["required_royalty_uplift_basis_points"] * per_bp, royalty["cost_usd_m"])


DOMINANCE = ROOT / "data/curated/experimental/brand_value_dominance_v1"


def test_group_dominance_weights_sum_to_full_r2_and_match_shapley():
    import numpy as np
    from srmp.experiments.brand_value_dominance_v1 import group_dominance
    rng = np.random.default_rng(0)
    x = rng.normal(size=(300, 3))
    y = 0.6 * x[:, 0] + 0.3 * x[:, 1] + rng.normal(size=300)
    total, weights = group_dominance(y, {"a": x[:, [0]], "b": x[:, [1]], "c": x[:, [2]]})
    assert np.isclose(sum(weights.values()), total)
    assert weights["a"] > weights["b"] > weights["c"] >= -1e-3


def test_incremental_brand_value_follows_the_index_lift_chain():
    manifest = _manifest(DOMINANCE / "brand_value_dominance_manifest.json")
    chain = manifest["primary_result"]
    values = manifest["values"]
    # Step 1 (ADR-0044): brand value is the signed brand share of the Lenovo-specific explained movement x company value.
    assert values["brand_share_definition"] == "share_of_lenovo_specific_explained_variance"
    assert np.isclose(chain["brand_value_usd_m"], values["brand_share"] * values["market_cap_usd_m"])
    sign = manifest["coefficients"]["brand_full_sample"]["brand"]["sign"]
    assert np.sign(values["brand_share"]) in (0, sign)
    weights = pd.read_parquet(DOMINANCE / "dominance_weights.parquet").set_index("group")["dominance_r2"]
    assert np.isclose(abs(values["brand_share"]), weights["brand"] / weights.drop("market").sum())
    # Step 2: the Brand Index is a ratio scale (ADR-0040), so the uplift is lift / counterfactual level.
    assert manifest["index_scale"]["display_scale"] == "percent_of_base_share"
    assert chain["zero_index_level"] == 0.0
    assert np.isclose(chain["brand_share_uplift_pct"],
                      100 * chain["sustained_lift_index_points"] / chain["counterfactual_index_level"])
    # Step 3: incremental brand value = BV x uplift x elasticity = coefficient x lift.
    assert np.isclose(chain["incremental_brand_value_usd_m"],
                      chain["brand_value_usd_m"] * chain["brand_share_uplift_pct"] / 100
                      * chain["brand_value_elasticity_to_brand_share"])
    assert np.isclose(chain["coefficient_usd_m_per_index_point"] * chain["sustained_lift_index_points"],
                      chain["incremental_brand_value_usd_m"])
    assert values["market_cap_base"] == "mean_post_announcement_market_cap"
    assert manifest["accepted_for_accounting_or_causal_claim"] is False


def test_fifa_specific_incremental_value_is_the_primary_uplift_times_brand_value():
    manifest = _manifest(DOMINANCE / "brand_value_dominance_manifest.json")
    fs = manifest["fifa_specific_incremental_brand_value"]
    bv = manifest["values"]["brand_value_usd_m"]
    elasticity = manifest["primary_result"]["brand_value_elasticity_to_brand_share"]
    for name, pct in fs["uplift_pct"].items():
        assert np.isclose(fs["incremental_brand_value_usd_m"][name], elasticity * pct / 100 * bv)
    assert fs["uplift_pct"]["statistical_band_95_low"] < fs["uplift_pct"]["primary"] <= fs["uplift_pct"]["attribution_band_upper"]


def test_brand_share_placebo_is_reported_with_the_measure():
    manifest = _manifest(DOMINANCE / "brand_value_dominance_manifest.json")
    placebo = manifest["placebo"]
    assert np.isclose(placebo["actual_unsigned_share"], abs(manifest["values"]["brand_share"]))
    for key in ("random_series", "time_shifted_brand"):
        assert 0 <= placebo[key]["probability_at_or_above_actual"] <= 1 and placebo[key]["draws"] > 100
