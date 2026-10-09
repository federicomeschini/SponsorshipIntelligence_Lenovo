"""Build frontend/data/eroi-data.js (window.EROI) for the Lenovo case dashboard.

Reads production outputs only (data/curated, data/staged, data/reference); never
simulates. Every figure the dashboard shows is either copied from a manifest or
derived here with the arithmetic stated next to it, so the page itself only
formats and draws. Run from the repository root after `python -m srmp.pipeline`:

    python frontend/scripts/build_eroi_data.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "data/curated/experimental"
OUT = ROOT / "frontend/data/eroi-data.js"
ANNOUNCE_EVENT = "2024-10-15"
PRE_END = pd.Timestamp("2024-10-14")          # last pre-announcement week (W-MON)
BRAND_NAMES = {
    "donor_dell": "Dell", "donor_asus": "Asus", "donor_acer": "Acer", "donor_hp": "HP",
    "donor_microsoft_surface": "Microsoft Surface", "donor_razer": "Razer", "donor_logitech": "Logitech",
    "donor_macbook": "MacBook", "donor_corsair": "Corsair", "donor_steelseries": "SteelSeries", "donor_benq": "BenQ",
    "donor_huawei": "Huawei", "donor_msi": "MSI",
}


def j(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def r(x, d: int = 4):
    """Round for compact JSON; keep None for missing values."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), d)


def series(values, d: int = 3) -> list:
    return [r(v, d) for v in values]


def iso(weeks) -> list[str]:
    return [pd.Timestamp(w).date().isoformat() for w in weeks]


# --------------------------------------------------------------------- events
def build_events() -> list[dict]:
    ev = pd.read_csv(ROOT / "data/reference/events.csv")
    rows = [{"id": e.event_id, "type": e.event_type, "name": e.event_name,
             "date": str(pd.Timestamp(e.event_timestamp_utc).date()), "property": e.property_id}
            for e in ev.itertuples() if e.event_id.startswith(("fifa_", "fcwc_"))]
    cal = pd.read_parquet(ROOT / "data/staged/fifa_calendar/official_fifa_calendar.parquet").sort_values("match_number")
    rows.append({"id": "wc_opening_2026", "type": "tournament_start", "name": "FIFA World Cup 2026 opening match",
                 "date": str(pd.Timestamp(cal.iloc[0]["event_timestamp_utc"]).date()), "property": "fwc"})
    rows.append({"id": "wc_final_2026", "type": "tournament_final", "name": "FIFA World Cup 2026 final",
                 "date": str(pd.Timestamp(cal.iloc[-1]["event_timestamp_utc"]).date()), "property": "fwc"})
    return rows


# -------------------------------------------------------------------- exposure
def build_exposure(events: list[dict]) -> dict:
    head = j(E / "sponsorship_total_effect_v1/estimate_manifest.json")
    weekly = pd.read_parquet(E / "sponsorship_total_effect_v1/total_effect_weekly.parquet")
    weekly["week"] = pd.to_datetime(weekly["week"])
    ann_idx = int((weekly["period"] == "pre").sum())

    # Lenovo and the base rivals, each rebased to 100 on its own pre-announcement mean (4-week mean).
    panel = pd.read_parquet(ROOT / "data/curated/trends/jointly_scaled_donor_trends.parquet")
    panel["week"] = pd.to_datetime(panel["week"]) + pd.Timedelta(days=1)
    wide = panel.pivot_table(index="week", columns="query_id", values="interest_common_scale", aggfunc="mean")
    wide = wide[wide.index >= pd.Timestamp("2022-01-03")]
    registry = pd.read_csv(ROOT / "data/reference/counterfactual_donor_registry.csv")
    base = [q for q in registry.loc[registry["inclusion_policy"].eq("base"), "query_id"] if q in wide]
    pre = wide.index <= PRE_END
    rebased = (wide / wide[pre].mean() * 100).rolling(4, min_periods=1).mean()
    peers = rebased[base]
    composite, p25, p75 = peers.median(axis=1), peers.quantile(0.25, axis=1), peers.quantile(0.75, axis=1)
    lenovo = rebased["anchor_lenovo"]
    post = ~pre
    late = rebased.index >= rebased.index.max() - pd.Timedelta(weeks=25)
    drift = {"brandDrift": float(lenovo[post].mean() - 100), "peerDrift": float(composite[post].mean() - 100),
             "brandDriftLate": float(lenovo[late].mean() - 100), "peerDriftLate": float(composite[late].mean() - 100)}
    drift["netDrift"] = drift["brandDrift"] - drift["peerDrift"]
    drift["netDriftLate"] = drift["brandDriftLate"] - drift["peerDriftLate"]

    # Brand Index: Lenovo's share of search, % of pre-announcement level.
    bi = pd.read_parquet(ROOT / "data/curated/index/brand_index_weekly.parquet")
    bi["week"] = pd.to_datetime(bi["week"])
    bi_man = j(ROOT / "data/curated/index/brand_index_manifest.json")

    # FIFA exposure (Blinkfire, digital only) and other sponsorships.
    expo = pd.read_parquet(ROOT / "data/staged/blinkfire/blinkfire_exposure_weekly.parquet")
    expo["week"] = pd.to_datetime(expo["week"])
    tax = pd.read_csv(ROOT / "data/reference/property_taxonomy.csv")
    fifa_ids = tax.loc[tax["property_group"].eq("fifa"), "property_id"].tolist()
    names = dict(zip(tax["property_id"], tax["property_name"]))
    # Sponsorship exposure counts from the deal (ADR-0048): earlier FIFA content is not shown.
    treatment = pd.Timestamp(j(E / "sponsorship_exposure_timing_v1/exposure_timing_manifest.json")["treatment_start"])
    fifa = expo[expo["property_id"].isin(fifa_ids) & (expo["week"] >= treatment - pd.Timedelta(days=treatment.weekday()))]
    fifa_weekly = fifa.groupby("week")[["impressions", "views"]].sum()
    by_property = (fifa.groupby("property_id")["impressions"].sum().sort_values(ascending=False))
    timing = pd.read_parquet(E / "sponsorship_exposure_timing_v1/exposure_timing_weekly.parquet")
    timing["week"] = pd.to_datetime(timing["week"])
    timing = timing[timing["exposure_observed"]]
    tm = j(E / "sponsorship_exposure_timing_v1/exposure_timing_manifest.json")
    fs = tm["fifa_specific_effect"]
    dec = pd.read_parquet(E / "sponsorship_exposure_timing_v1/fifa_specific_decomposition.parquet")
    scales = pd.read_parquet(E / "sponsorship_exposure_timing_v1/nonfifa_backcast_scales.parquet")

    # Weekly gap and the part explained by FIFA exposure, both in % of the twin (brand share) (FE-026).
    # FIFA part_t = b_F x log adstock_t / sd over the estimation sample: its post-period mean is the
    # FIFA-specific effect (ADR-0043 decomposition).
    coef = pd.read_parquet(E / "sponsorship_exposure_timing_v1/exposure_timing_coefficients.parquet")
    p_test, p_spec = fs["primary_specification"].split(":")
    b_fifa = float(coef[(coef["test"] == p_test) & (coef["specification"] == p_spec)
                        & (coef["term"] == "fifa_log_adstock")]["estimate"].iloc[0])
    fifa_points = (b_fifa * timing.set_index("week")["fifa_log_adstock"] / timing["fifa_log_adstock"].std(ddof=0))
    core = weekly.set_index("week")
    gap_pct = 100 * core["index_gap"] / core["synthetic_index"]
    fifa_pct = (100 * fifa_points.reindex(core.index) / core["synthetic_index"]).where(core["period"].eq("post"))

    # Cross-checks and World Cup.
    share = j(E / "sponsorship_total_effect_share_of_search_v1/estimate_manifest.json")
    share_curve = pd.read_parquet(E / "sponsorship_total_effect_share_of_search_v1/specification_curve.parquet")
    share_ex = share_curve[share_curve["selected_design"] & share_curve["placebo_filter"].eq("none")
                           & share_curve["statistic"].eq("rmspe_ratio") & share_curve["window"].eq("excluding_spring_2026_surge")]
    salience = j(E / "sponsorship_total_effect_search_salience_v1/estimate_manifest.json")
    curve = pd.read_parquet(E / "sponsorship_total_effect_v1/specification_curve.parquet")
    sel = curve[curve["selected_design"] & curve["placebo_filter"].eq("none") & curve["statistic"].eq("rmspe_ratio")].set_index("window")
    wc = j(E / "world_cup_impact_v1/estimate_manifest.json")
    ev = {e["id"]: pd.Timestamp(e["date"]) for e in events}
    wc_start = ev["wc_opening_2026"] - pd.to_timedelta(ev["wc_opening_2026"].weekday(), unit="D")
    wc_end = ev["wc_final_2026"]

    def window(a, b):
        m = (weekly["week"] >= a) & (weekly["week"] <= b) & (weekly["period"] == "post")
        return {"weeks": int(m.sum()), "gap": r(weekly.loc[m, "index_gap"].mean(), 3)}

    te = head["total_effect"]
    return {
        "core": {"weeks": iso(weekly["week"]), "annIdx": ann_idx, "actual": series(weekly["actual_index"]),
                 "synthetic": series(weekly["synthetic_index"]), "gap": series(weekly["index_gap"]),
                 "gapPct": series(gap_pct, 2), "fifaPct": series(fifa_pct, 2),
                 "fifaPointsPostMean": r(fifa_points.reindex(core.index)[core["period"].eq("post")].mean(), 3)},
        "brandIndex": {"weeks": iso(bi["week"]), "level": series(bi["index_level"]), "se": series(bi["index_se"]),
                       "productDemand": series(bi["product_search_demand"], 1),
                       "surveyFit": {k: r(v["correlation"], 2) for k, v in bi_man["survey_fit"].items()},
                       "postMean": r(bi.loc[bi["week"] > PRE_END, "index_level"].mean(), 2)},
        "peerWeeks": iso(rebased.index), "brandSearch": series(lenovo, 1), "peerComposite": series(composite, 1),
        "peerP25": series(p25, 1), "peerP75": series(p75, 1),
        "peers": [{"name": BRAND_NAMES.get(q, q), "series": series(peers[q], 1)} for q in base],
        "event": {"weeks": iso(fifa_weekly.index), "impressions": [int(v) for v in fifa_weekly["impressions"]],
                  "views": [int(v) for v in fifa_weekly["views"]], "coverageEnd": str(fifa_weekly.index.max().date())},
        "byProperty": [{"label": names.get(p, p), "impressions": int(v)} for p, v in by_property.items() if v > 0],
        "sponsorships": {"weeks": iso(timing["week"]), "fifa": series(timing["fifa_adstock"] / 1e6, 2),
                         "other": series(timing["nonfifa_adstock"] / 1e6, 2),
                         "otherBaseline": series(timing["nonfifa_baseline_adstock"] / 1e6, 2),
                         "backcastEnd": str(timing.loc[timing["nonfifa_source"] == "backcast", "week"].max().date()),
                         "properties": [{"id": s.property_id, "name": names.get(s.property_id, s.property_id),
                                         "activeFrom": s.active_from, "upgradedFrom": None if s.upgraded_from in (None, "None") else s.upgraded_from,
                                         "observedOverBaseline": r(s.observed_over_baseline, 2)} for s in scales.itertuples()]},
        "timingTests": tm["summary"],
        "fifaSpecific": {**{k: fs[k] for k in ["primary_index_points", "primary_uplift_pct", "statistical_band_95_index_points",
                                                "statistical_band_95_uplift_pct", "attribution_band_upper_index_points",
                                                "attribution_band_upper_uplift_pct", "counterfactual_index_level",
                                                "decomposition_index_points", "period", "weeks", "primary_specification",
                                                "specification_range_fifa_index_points"]},
                         "specifications": [{"spec": f"{d.test} / {d.specification}", "fifa": r(d.fifa, 2), "other": r(d.other_sponsorships, 2),
                                             "events": r(d.events, 2), "residual": r(d.residual, 2)} for d in dec.itertuples()]},
        "design": {"method": head["selection"]["selected_method"], "pool": head["selection"]["selected_pool"],
                   "donors": [BRAND_NAMES.get(d, d) for d in head["selection"]["selected_donors"]],
                   "preRmspe": r(head["primary"]["pre_rmspe_index_points"], 3), "placeboP": r(head["primary"]["p_value"], 3),
                   "placebos": head["primary"]["placebos_kept"], "minP": r(1 / (1 + head["primary"]["placebos_kept"]), 3),
                   "looRange": [r(v, 2) for v in te["leave_one_donor_out_range"]],
                   "specs": head["specification_curve_summary"]["specifications"],
                   "sharePositive": r(head["specification_curve_summary"]["share_lift_positive"], 3),
                   "shareSignificant": r(head["specification_curve_summary"]["share_p_at_or_below_alpha"], 3),
                   "exSurge": {"lift": r(sel.loc["excluding_spring_2026_surge", "lift_index_points"], 2),
                               "p": r(sel.loc["excluding_spring_2026_surge", "p_value"], 3)}},
        "total": {"lift": r(te["lift_index_points"], 3), "upliftPct": r(100 * te["lift_index_points"] / te["synthetic_post_mean_index"], 2),
                  "counterfactual": r(te["synthetic_post_mean_index"], 2), "from": te["first_post_week"], "to": te["last_week"],
                  "weeks": te["post_weeks"]},
        "crossChecks": [
            {"label": "Brand Index (headline design)", "lift": r(te["lift_index_points"], 2), "p": r(head["primary"]["p_value"], 3), "unit": "Brand Index points"},
            {"label": "Google share of search only", "lift": r(share["total_effect"]["lift_index_points"], 2), "p": r(share["primary"]["p_value"], 3), "unit": "% of pre-announcement share",
             "exSurgeP": r(share_ex["p_value"].iloc[0], 3)},
            {"label": "Former search-salience index", "lift": r(salience["total_effect"]["lift_index_points"], 2), "p": r(salience["primary"]["p_value"], 3), "unit": "old 100/15 points"},
        ],
        "worldCup": {"beforeTournament": window(pd.Timestamp(te["first_post_week"]), wc_start - pd.Timedelta(days=1)),
                     "tournament": window(wc_start, wc_end), "afterFinal": window(wc_end + pd.Timedelta(days=1), pd.Timestamp(te["last_week"])),
                     "incremental": {k: r(wc["primary"][k], 2) for k in ["primary_exposure_weighted_gap", "tournament_mean_gap", "post_event_persistence_mean_gap"]},
                     "incrementalP": r(wc["placebo"]["p_value"], 3), "gatesOpen": int(sum(not g["passed"] for g in wc["gates"])),
                     "gates": len(wc["gates"]), "status": wc["status"]},
        "kpi": {**{k: r(v, 2) for k, v in drift.items()}, "peerCount": len(base),
                "eventImpressions": int(fifa_weekly["impressions"].sum()), "eventViews": int(fifa_weekly["views"].sum()),
                "matches": 104},
    }


# ------------------------------------------------------------------ evaluation
def build_evaluation() -> dict:
    """Step 02: the brand contribution factor (share-price evidence) and the income-split brand value.

    Every money figure comes from brand_value_dcf_v2 (ADR-0045); the share-price analysis
    supplies only the factor and its diagnostics (shares, not values)."""
    dom = j(E / "brand_value_dominance_v1/brand_value_dominance_manifest.json")
    dcf = j(E / "brand_value_dcf_v2/brand_value_dcf_manifest.json")
    stock = j(E / "stock_brand_response_v2/stock_response_manifest.json")
    daily = pd.read_parquet(E / "stock_brand_response_v2/rolling_abnormal_returns_daily.parquet")
    daily["date"] = pd.to_datetime(daily["date"])
    daily["week"] = daily["date"] - pd.to_timedelta(daily["date"].dt.weekday, unit="D")
    wk = daily.groupby("week")[["lenovo_log_return", "predicted_lenovo_log_return", "abnormal_return"]].sum()
    actual = 100 * np.exp(wk["lenovo_log_return"].cumsum())
    expected = 100 * np.exp(wk["predicted_lenovo_log_return"].cumsum())
    car = 100 * (np.exp(wk["abnormal_return"].cumsum()) - 1)
    ann_idx = int((wk.index <= PRE_END).sum())
    betas = {"hsi": r(daily["factor_beta_hsi"].mean(), 3), "ndx": r(daily["factor_beta_ndx_hkd_lagged"].mean(), 3)}

    resp = pd.read_parquet(E / "stock_brand_response_v2/stock_brand_response_weekly.parquet").dropna(
        subset=["brand_index_innovation", "forward_abnormal_return_h0"])
    resp["week"] = pd.to_datetime(resp["week"])
    h0 = stock["horizon_results"][0]
    xs = resp["brand_index_innovation"]
    fit = [{"x": r(xs.min(), 3), "y": r(h0["abnormal_return_percentage_points_per_BI_innovation_point"] / 100 * xs.min(), 5)},
           {"x": r(xs.max(), 3), "y": r(h0["abnormal_return_percentage_points_per_BI_innovation_point"] / 100 * xs.max(), 5)}]
    weights = pd.read_parquet(E / "brand_value_dominance_v1/dominance_weights.parquet")
    stab = dom["stability_summary"]

    # Income split (ADR-0045).
    prim, rate, base = dcf["primary_result"], dcf["discount_rate"], dcf["base_year"]
    forecast = pd.read_parquet(E / "brand_value_dcf_v2/economic_profit_forecast.parquet")
    grid = pd.read_parquet(E / "brand_value_dcf_v2/sensitivity_grid.parquet")
    own = grid[grid["role_of_brand"].eq("brand_contribution_factor")]
    g0, w0 = dcf["revenue_growth"]["terminal"], rate["wacc"]
    wacc_only = own[np.isclose(own["terminal_growth"], g0)]["brand_value_usd_m"]
    growth_only = own[np.isclose(own["wacc"], w0)]["brand_value_usd_m"]
    heat = grid[grid["role_of_brand"].str.startswith("grid") & np.isclose(grid["terminal_growth"], g0)]
    by_role = dcf["by_role_definition"]
    return {
        "ticker": "0992.HK", "weeks": iso(wk.index), "annIdx": ann_idx,
        "actualPath": series(actual, 2), "expectedPath": series(expected, 2), "carPath": series(car, 2), "betas": betas,
        "points": [{"x": r(a, 3), "y": r(b, 5), "w": str(w.date()), "post": bool(w > PRE_END)}
                   for a, b, w in zip(resp["brand_index_innovation"], resp["forward_abnormal_return_h0"], resp["week"])],
        "fitLine": fit,
        "stockResponse": [{"h": h["horizon_weeks"], "est": r(h["abnormal_return_percentage_points_per_BI_innovation_point"], 3),
                           "lo": r(h["lower_95_percentage_points"], 3), "hi": r(h["upper_95_percentage_points"], 3),
                           "p": r(h["p_value_normal_approx"], 3), "pHolm": r(h["p_value_holm"], 3)} for h in stock["horizon_results"]],
        "dominance": [{"group": g.group, "share": r(g.share_of_explained, 4),
                       "shareOfLenovoSpecific": None if g.group == "market" else r(g.share_of_lenovo_specific, 4)}
                      for g in weights.itertuples()],
        "r2": r(dom["samples"]["brand_model_r2"], 3), "weeksN": dom["samples"]["brand_weeks"],
        "brandCoef": {k: r(v, 5) for k, v in dom["coefficients"]["brand_full_sample"]["brand"].items()},
        "factor": {"share": r(dom["values"]["brand_share"], 5), "share90": [r(v, 4) for v in dom["values"]["brand_share_90pct"]],
                   "stabilityRange": [r(stab["brand_share_min"], 4), r(stab["brand_share_max"], 4)]},
        "placebo": {"actual": r(dom["placebo"]["actual_unsigned_share"], 4),
                    "noiseMedian": r(dom["placebo"]["random_series"]["median"], 4),
                    "noiseP": r(dom["placebo"]["random_series"]["probability_at_or_above_actual"], 3),
                    "shiftMedian": r(dom["placebo"]["time_shifted_brand"]["median"], 4),
                    "shiftP": r(dom["placebo"]["time_shifted_brand"]["probability_at_or_above_actual"], 3)},
        "dcf": {
            "baseYear": base["fiscal_year"], "valuationDate": dcf["valuation_date"],
            "revenue": r(base["revenue"] * 1e6, 0), "operatingMargin": r(base["operating_margin"], 4),
            "taxRate": r(base["tax_rate"], 4), "investedCapital": r(base["invested_capital"] * 1e6, 0),
            "roic": r(base["return_on_invested_capital"], 4),
            "growthStart": r(dcf["revenue_growth"]["start"], 4), "growthTerminal": r(g0, 4),
            "wacc": {"wacc": r(w0, 4), "riskFree": r(rate["risk_free"], 4), "beta": r(rate["beta"], 3),
                     "erp": r(rate["equity_risk_premium"], 3), "costOfEquity": r(rate["cost_of_equity"], 4),
                     "costOfDebt": r(rate["after_tax_cost_of_debt"], 4), "weightDebt": r(rate["weight_debt"], 4)},
            "forecast": [{"year": int(f.year), "revenue": r(f.revenue_usd_m * 1e6, 0), "nopat": r(f.nopat_usd_m * 1e6, 0),
                          "charge": r(f.capital_charge_usd_m * 1e6, 0), "ep": r(f.economic_profit_usd_m * 1e6, 0),
                          "branded": r(f.branded_earnings_usd_m * 1e6, 0)} for f in forecast.itertuples()],
            "epPv": r(dcf["economic_profit_pv_usd_m"] * 1e6, 0),
            "brandValue": r(prim["brand_value_usd_m"] * 1e6, 0),
            "explicitPv": r(prim["explicit_pv_usd_m"] * 1e6, 0), "terminalPv": r(prim["terminal_pv_usd_m"] * 1e6, 0),
            "terminalShare": r(prim["terminal_share_of_value"], 3),
            "valuePerPoint": r(prim["value_per_brand_index_point_usd_m"] * 1e6, 0),
            "factorBand": [r(by_role["factor_bootstrap_p05"]["brand_value_usd_m"] * 1e6, 0),
                           r(by_role["factor_bootstrap_p95"]["brand_value_usd_m"] * 1e6, 0)],
            "waccRange": [r(wacc_only.min() * 1e6, 0), r(wacc_only.max() * 1e6, 0)],
            "growthRange": [r(growth_only.min() * 1e6, 0), r(growth_only.max() * 1e6, 0)],
            "heat": {"roles": sorted({r(v, 3) for v in heat["role_value"]}), "waccs": sorted({r(v, 4) for v in heat["wacc"]}),
                     "values": [{"role": r(h.role_value, 3), "wacc": r(h.wacc, 4), "value": r(h.brand_value_usd_m * 1e6, 0)}
                                for h in heat.itertuples()]},
        },
    }


# ---------------------------------------------------------------- monetization
def build_monetization(exposure: dict, evaluation: dict) -> dict:
    dcf = j(E / "brand_value_dcf_v2/brand_value_dcf_manifest.json")
    added = dcf["primary_result"]["fifa_added_brand_value_usd_m"]
    uplift = dcf["primary_result"]["fifa_specific_uplift_pct"]
    elasticity = dcf["primary_result"]["elasticity_to_brand_share"]
    fs = exposure["fifaSpecific"]
    bv = evaluation["dcf"]["brandValue"]
    keys = {"conservative": "statistical_band_95_low", "base": "primary", "ambitious": "attribution_band_upper"}
    points = {"conservative": fs["statistical_band_95_index_points"][0], "base": fs["primary_index_points"],
              "ambitious": fs["attribution_band_upper_index_points"]}
    scenarios = {name: {"upliftPct": r(uplift[key], 3), "indexPoints": r(points[name], 3), "value": r(added[key] * 1e6, 0)}
                 for name, key in keys.items()}
    # Bridge: whole gap (same weeks) -> less everything not attributed to FIFA (residual, other
    # sponsorships and events, aggregated; FE-014) -> FIFA-specific.
    d, cf = fs["decomposition_index_points"], fs["counterfactual_index_level"]
    rest = d["fifa"] - d["total_gap"]
    bridge = [
        {"label": "Whole gap to the twin", "points": r(d["total_gap"], 3), "value": r(d["total_gap"] / cf * bv, 0), "total": True},
        {"label": "Not attributed to FIFA", "points": r(rest, 3), "value": r(rest / cf * bv, 0)},
        {"label": "FIFA-specific value", "points": r(d["fifa"], 3), "value": r(d["fifa"] / cf * bv, 0), "total": True},
    ]
    # FIFA's share of the brand value, applied to the forecast below.
    base_pct = elasticity * uplift["primary"] / 100
    D = evaluation["dcf"]

    # Is the lift holding? Quarterly mean gap of the total path.
    w = pd.read_parquet(E / "sponsorship_total_effect_v1/total_effect_weekly.parquet")
    w["week"] = pd.to_datetime(w["week"])
    q = w[w["period"] == "post"].groupby(w["week"].dt.to_period("Q"))["index_gap"].mean()
    # The same value as a flow: FIFA's share of each forecast year's branded earnings (base case).
    rate = dcf["discount_rate"]["wacc"]
    flow = [{"year": f["year"], "value": r(base_pct * f["branded"], 0), "pv": r(base_pct * f["branded"] / (1 + rate) ** f["year"], 0)}
            for f in D["forecast"]]
    return {"scenarios": scenarios, "bridge": bridge, "fifaBrandedEarnings": flow,
            "fifaExplicitShare": r(sum(x["pv"] for x in flow) / scenarios["base"]["value"], 3),
            "quarterlyGap": [{"q": str(k), "gap": r(v, 2)} for k, v in q.items()]}


# ---------------------------------------------------------------- method pages
METHOD_LABELS = {"synthetic_did": "Synthetic difference-in-differences", "generalized_scm_factor": "Generalised synthetic control (factor)",
                 "simplex_scm": "Synthetic control (simplex)", "augmented_scm": "Augmented synthetic control",
                 "base_plus_sensitivity": "13 core rivals", "expanded": "26 rivals", "expanded_plus_sensitivity": "28 rivals",
                 "google_share_of_search": "Google share of search", "wikipedia_share_of_attention": "Wikipedia share of attention",
                 "pillar_salience": "Weekly attention (Google share of search)", "gwi_engagement": "GWI engagement",
                 "gwi_consideration": "GWI consideration", "nielsen_awareness": "Nielsen awareness"}


def build_method() -> dict:
    """In-depth Method pages: the Brand Index build, the twin's design choice, exposure carryover.

    Only diagnostics and parameters (no money figures, FE-011)."""
    bi = j(ROOT / "data/curated/index/brand_index_manifest.json")
    loadings = pd.read_parquet(ROOT / "data/curated/index/brand_index_loadings.parquet")
    screen = pd.read_parquet(ROOT / "data/curated/index/brand_index_validity_screen.parquet")
    sel = pd.read_parquet(E / "sponsorship_total_effect_v1/selection_table.parquet").sort_values("oos_rmspe_index_points")
    head = j(E / "sponsorship_total_effect_v1/estimate_manifest.json")
    timing_cfg = (ROOT / "config/experiments/sponsorship_exposure_timing_v1.yaml").read_text(encoding="utf-8")
    delta = float(next(l.split(":")[1].split("#")[0] for l in timing_cfg.splitlines() if l.startswith("adstock_delta")))
    label = lambda k: METHOD_LABELS.get(k, k.replace("_", " "))
    return {
        "brandIndex": {
            "phi": r(bi["phi"], 3), "weeks": bi["weeks"], "sample": bi["sample"], "base": bi["standardisation_base"],
            "logPerSd": r(bi["display_scale"]["log_points_per_factor_sd"], 4),
            "loadings": [{"signal": label(l.signal), "frequency": l.frequency, "loading": r(l.loading, 3),
                          "explained": r(l.share_of_variance_explained, 3), "n": int(l.observations)} for l in loadings.itertuples()],
            "screen": [{"signal": label(x.signal), "engagement": r(x.gwi_engagement_level_corr, 2), "engagementChange": r(x.gwi_engagement_change_corr, 2),
                        "consideration": r(x.gwi_consideration_level_corr, 2), "considerationChange": r(x.gwi_consideration_change_corr, 2),
                        "admitted": bool(x.admitted)} for x in screen.itertuples()],
            "surveyQuarters": bi["survey_fit"]["gwi_engagement"]["quarters"],
            "nielsenWaves": int(len(pd.read_parquet(ROOT / "data/curated/index/brand_index_survey_waves.parquet"))),
            "sensitivities": [{"label": {"all_weekly_signals_admitted": "Every weekly signal admitted",
                                         "weekly_only_no_survey": "Weekly signals only, no survey",
                                         "gwi_only": "GWI only, without Nielsen"}.get(x["id"], x["id"]),
                               "corr": r(x["correlation_with_headline"], 3), "postMean": r(x["post_announcement_mean"], 1)}
                              for x in bi["sensitivities"]],
        },
        "designs": [{"method": label(d.method), "pool": label(d.donor_pool), "donors": int(d.donors),
                     "oosRmspe": r(d.oos_rmspe_index_points, 2), "selected": bool(d.method == head["selection"]["selected_method"]
                                                                                and d.donor_pool == head["selection"]["selected_pool"])}
                    for d in sel.head(6).itertuples()],
        "designFolds": int(sel["folds"].iloc[0]),
        "specRange": [r(v, 2) for v in head["specification_curve_summary"]["lift_range_index_points"]],
        "adstock": delta,
        "tv": build_tv(),
    }


def build_tv() -> dict:
    """Television check (ADR-0046): relative intensities and FIFA-specific results only, no money (P1)."""
    tv = j(E / "tv_exposure_check_v1/tv_exposure_check_manifest.json")
    w = pd.read_parquet(E / "tv_exposure_check_v1/tv_exposure_weekly_relative.parquet")
    w["week"] = pd.to_datetime(w["week"])
    w = w[w["week"] >= pd.Timestamp(tv["tv_coverage"]["from"])]
    obs = w["tv_source"].eq("observed")
    ow = tv["observed_window"]
    return {
        "coverage": [tv["tv_coverage"]["from"], tv["tv_coverage"]["to"]],
        "corrWeekly": r(tv["overlap"]["corr_tv_vs_social_weekly"], 2),
        "primary": r(tv["primary_fifa_specific_index_points"], 3),
        "band": [r(v, 2) for v in tv["primary_band_95_index_points"]],
        "observed": {"to": ow["to"], "socialOnly": r(ow["social_only"]["fifa_total"], 2),
                     "withTv": r(ow["social_and_tv"]["fifa_total"], 2), "socialPart": r(ow["social_and_tv"]["social_part"], 2),
                     "tvPart": r(ow["social_and_tv"]["tv_part"], 2), "pTv": r(ow["social_and_tv"]["p_tv"], 3)},
        "perMatch": {k: r(v, 2) for k, v in tv["calibration"]["value_per_match_relative_to_group"].items()},
        "calibrationMatches": tv["calibration"]["matches"], "worldCupMatches": tv["world_cup_matches"],
        "scenarios": [{"label": x["label"], "scale": r(x["world_cup_vs_club_world_cup"], 1), "fifaTotal": r(x["fifa_total_with_tv"], 2),
                       "socialPart": r(x["social_part"], 2), "tvPart": r(x["tv_part"], 2), "pTv": r(x["p_tv"], 2)} for x in tv["scenarios"]],
        "maxChange": r(tv["summary"]["max_change_vs_primary_index_points"], 2),
        "range": [r(v, 2) for v in tv["summary"]["fifa_total_with_tv_range"]],
        "tvPartRange": [r(v, 2) for v in tv["summary"]["tv_part_range"]],
        "tvPRange": [r(v, 2) for v in tv["summary"]["tv_p_range"]],
        "withinBand": tv["summary"]["within_primary_band"],
        "series": {"weeks": iso(w["week"]), "social": series(w["social_impressions_relative"], 4),
                   "observed": [r(v, 4) if o else None for v, o in zip(w["same_per_match"], obs)],
                   "simLow": [None if o else r(v, 4) for v, o in zip(w["same_per_match"], obs)],
                   "simHigh": [None if o else r(v, 4) for v, o in zip(w["blinkfire_per_match"], obs)]},
    }


def main() -> None:
    events = build_events()
    exposure = build_exposure(events)
    evaluation = build_evaluation()
    monetization = build_monetization(exposure, evaluation)
    bi = j(ROOT / "data/curated/index/brand_index_manifest.json")
    data = {
        "meta": {"brand": "Lenovo", "event": "FIFA",
                 "caseLabel": "FIFA × Lenovo", "built": date.today().isoformat(), "dataThrough": bi["sample"][1],
                 "announce": ANNOUNCE_EVENT, "firstPostWeek": exposure["total"]["from"],
                 "decisions": "ADR-0038 to ADR-0045", "notebooks": "reports/methods_annex/10_total_sponsorship_effect.ipynb, 40_brand_value.ipynb"},
        "events": events, "exposure": exposure, "evaluation": evaluation, "monetization": monetization,
        "method": build_method(),
    }
    OUT.write_text("/* Generated by frontend/scripts/build_eroi_data.py from production outputs. Do not edit by hand. */\n"
                   "window.EROI = " + json.dumps(data, separators=(",", ":"), default=str) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
