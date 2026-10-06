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
    # Step 1: brand value is the signed brand share of price formation x company value.
    assert np.isclose(chain["brand_value_usd_m"], values["brand_share_of_price_formation"] * values["market_cap_usd_m"])
    sign = manifest["coefficients"]["brand_full_sample"]["brand"]["sign"]
    assert np.sign(values["brand_share_of_price_formation"]) in (0, sign)
    # Step 2: the Index is affine in raw search interest, so the lift is a ratio-scale uplift.
    assert manifest["salience_map"]["correlation"] > 0.999
    headroom = chain["counterfactual_index_level"] - chain["zero_interest_index_level"]
    assert headroom > 0
    assert np.isclose(chain["salience_uplift_pct"], 100 * chain["sustained_lift_index_points"] / headroom)
    # Step 3: incremental brand value = BV x uplift x elasticity = coefficient x lift.
    assert np.isclose(chain["incremental_brand_value_usd_m"],
                      chain["brand_value_usd_m"] * chain["salience_uplift_pct"] / 100
                      * chain["brand_value_elasticity_to_salience"])
    assert np.isclose(chain["coefficient_usd_m_per_index_point"] * chain["sustained_lift_index_points"],
                      chain["incremental_brand_value_usd_m"])
    assert values["market_cap_base"] == "mean_post_announcement_market_cap"
    assert manifest["accepted_for_accounting_or_causal_claim"] is False


DCF = ROOT / "data/curated/experimental/brand_value_dcf_v1"


def test_brand_dcf_discounts_role_share_of_economic_profit():
    manifest = _manifest(DCF / "brand_value_dcf_manifest.json")
    forecast = pd.read_parquet(DCF / "economic_profit_forecast.parquet")
    rate = manifest["discount_rate"]["wacc"]
    role = manifest["primary_result"]["role_of_brand"]
    # Economic profit = NOPAT - WACC x opening invested capital.
    assert np.allclose(forecast["economic_profit_usd_m"],
                       forecast["nopat_usd_m"] - rate * forecast["opening_invested_capital_usd_m"])
    assert np.allclose(forecast["branded_earnings_usd_m"], role * forecast["economic_profit_usd_m"])
    explicit = float((forecast["branded_earnings_usd_m"] * (1 + rate) ** -forecast["year"]).sum())
    assert np.isclose(manifest["primary_result"]["explicit_pv_usd_m"], explicit)
    assert np.isclose(manifest["primary_result"]["brand_value_usd_m"],
                      manifest["primary_result"]["explicit_pv_usd_m"] + manifest["primary_result"]["terminal_pv_usd_m"])
    # Growth fades linearly to the terminal rate and the WACC exceeds it.
    assert np.isclose(forecast["revenue_growth"].iloc[-1], manifest["revenue_growth"]["terminal"])
    assert rate > manifest["revenue_growth"]["terminal"]


def test_brand_dcf_value_scales_with_role_and_feeds_the_sponsorship_chain():
    manifest = _manifest(DCF / "brand_value_dcf_manifest.json")
    by_role = manifest["by_role_definition"]
    values = {name: row["brand_value_usd_m"] / row["role_of_brand"] for name, row in by_role.items()}
    assert np.isclose(*values.values())  # same economic-profit PV under every role
    primary = manifest["primary_result"]
    assert np.isclose(primary["incremental_brand_value_usd_m"],
                      primary["brand_value_usd_m"] * primary["salience_uplift_pct"] / 100
                      * primary["elasticity_to_salience"])
