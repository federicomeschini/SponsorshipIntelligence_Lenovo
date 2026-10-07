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
    fifa = expo[expo["property_id"].isin(fifa_ids)]
    fifa_weekly = fifa.groupby("week")[["impressions", "views"]].sum()
    by_property = (fifa.groupby("property_id")["impressions"].sum().sort_values(ascending=False))
    timing = pd.read_parquet(E / "sponsorship_exposure_timing_v1/exposure_timing_weekly.parquet")
    timing["week"] = pd.to_datetime(timing["week"])
    timing = timing[timing["exposure_observed"]]
    tm = j(E / "sponsorship_exposure_timing_v1/exposure_timing_manifest.json")
    fs = tm["fifa_specific_effect"]
    dec = pd.read_parquet(E / "sponsorship_exposure_timing_v1/fifa_specific_decomposition.parquet")
    scales = pd.read_parquet(E / "sponsorship_exposure_timing_v1/nonfifa_backcast_scales.parquet")

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
                 "synthetic": series(weekly["synthetic_index"]), "gap": series(weekly["index_gap"])},
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
    dom = j(E / "brand_value_dominance_v1/brand_value_dominance_manifest.json")
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
    values, chain = dom["values"], dom["primary_result"]
    cf = chain["counterfactual_index_level"]
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
        "marketCap": r(values["market_cap_usd_m"] * 1e6, 0), "capBase": values["market_cap_base"],
        # ADR-0044: one measure, the brand's share of the Lenovo-specific explained movement.
        "brand": {"share": r(values["brand_share"], 5), "share90": [r(v, 4) for v in values["brand_share_90pct"]],
                  "brandValue": r(values["brand_value_usd_m"] * 1e6, 0),
                  "band90": [r(v * 1e6, 0) for v in values["brand_value_90pct_usd_m"]],
                  "valuePerPoint": r(values["brand_value_usd_m"] * 1e6 / cf, 0)},
        "placebo": {"actual": r(dom["placebo"]["actual_unsigned_share"], 4),
                    "noiseMedian": r(dom["placebo"]["random_series"]["median"], 4),
                    "noiseP": r(dom["placebo"]["random_series"]["probability_at_or_above_actual"], 3),
                    "shiftMedian": r(dom["placebo"]["time_shifted_brand"]["median"], 4),
                    "shiftP": r(dom["placebo"]["time_shifted_brand"]["probability_at_or_above_actual"], 3)},
        "stabilityShareRange": [r(stab["brand_share_min"], 4), r(stab["brand_share_max"], 4)],
        "stability": [{"check": s.check, "share": r(s.brand_share, 4), "value": r(s.brand_value_usd_m * 1e6, 0)}
                      for s in pd.read_parquet(E / "brand_value_dominance_v1/stability.parquet").itertuples()],
        "brandFinance": r(dom["external_reference"]["brand_finance_2025_brand_value_usd_m"] * 1e6, 0),
        "interbrand2015": r(dom["external_reference"]["interbrand_2015_brand_value_usd_m"] * 1e6, 0),
        "counterfactualLevel": r(cf, 2),
    }


# ---------------------------------------------------------------- monetization
def build_monetization(exposure: dict, evaluation: dict) -> dict:
    dom = j(E / "brand_value_dominance_v1/brand_value_dominance_manifest.json")
    fsv = dom["fifa_specific_incremental_brand_value"]
    fs = exposure["fifaSpecific"]
    bv = evaluation["brand"]["brandValue"]
    keys = {"conservative": "statistical_band_95_low", "base": "primary", "ambitious": "attribution_band_upper"}
    points = {"conservative": fs["statistical_band_95_index_points"][0], "base": fs["primary_index_points"],
              "ambitious": fs["attribution_band_upper_index_points"]}
    scenarios = {}
    for name, key in keys.items():
        scenarios[name] = {"upliftPct": r(fsv["uplift_pct"][key], 3), "indexPoints": r(points[name], 3),
                           "value": r(fsv["incremental_brand_value_usd_m"][key] * 1e6, 0)}
    # Bridge: whole gap (same weeks) -> less residual -> less other sponsorships and events -> FIFA-specific.
    d, cf = fs["decomposition_index_points"], fs["counterfactual_index_level"]
    bridge = [
        {"label": "Whole gap to the twin", "points": r(d["total_gap"], 3), "value": r(d["total_gap"] / cf * bv, 0), "total": True},
        {"label": "Unexplained residual", "points": r(-d["residual"], 3), "value": r(-d["residual"] / cf * bv, 0)},
        {"label": "Other sponsorships and events", "points": r(-(d["other_sponsorships"] + d["events"]), 3),
         "value": r(-(d["other_sponsorships"] + d["events"]) / cf * bv, 0)},
        {"label": "FIFA-specific value", "points": r(d["fifa"], 3), "value": r(d["fifa"] / cf * bv, 0), "total": True},
    ]

    # Sensitivity of the base-case increment: one input moved at a time.
    base_pct = scenarios["base"]["upliftPct"] / 100
    caps = dom["values"]["brand_value_by_cap_base_usd_m"]
    stab = evaluation["stability"]
    tornado = [
        {"label": "FIFA-specific uplift (95% band to whole gap)", "lo": r(scenarios["conservative"]["upliftPct"] / 100 * bv, 0),
         "hi": r(scenarios["ambitious"]["upliftPct"] / 100 * bv, 0)},
        {"label": "Brand share of Lenovo-specific drivers (bootstrap 90%)", "lo": r(base_pct * evaluation["brand"]["band90"][0], 0),
         "hi": r(base_pct * evaluation["brand"]["band90"][1], 0)},
        {"label": "Brand share across samples and controls (stability checks)", "lo": r(base_pct * min(s["value"] for s in stab), 0),
         "hi": r(base_pct * max(s["value"] for s in stab), 0)},
        {"label": "Market-cap base (pre-announcement to latest)", "lo": r(base_pct * min(caps.values()) * 1e6, 0),
         "hi": r(base_pct * max(caps.values()) * 1e6, 0)},
        {"label": "Elasticity of brand value to brand share (0.5 to 1.5, assumed)", "lo": r(0.5 * base_pct * bv, 0),
         "hi": r(1.5 * base_pct * bv, 0)},
    ]
    tornado.sort(key=lambda t: abs(t["hi"] - t["lo"]), reverse=True)

    # Is the lift holding? Quarterly mean gap of the total path.
    w = pd.read_parquet(E / "sponsorship_total_effect_v1/total_effect_weekly.parquet")
    w["week"] = pd.to_datetime(w["week"])
    q = w[w["period"] == "post"].groupby(w["week"].dt.to_period("Q"))["index_gap"].mean()

    routes = pd.read_parquet(E / "valuation_routes_v1/valuation_routes.parquet")
    be = pd.read_parquet(E / "valuation_routes_v1/breakeven.parquet")
    royalty = be[be["route"].eq("relief_from_royalty")]
    mie = j(E / "market_implied_earnings_bridge_v1/market_implied_earnings_bridge_manifest.json")
    mon = j(E / "sponsorship_monetization_v1/experiment_manifest.json")
    return {
        "scenarios": scenarios, "bridge": bridge, "tornado": tornado,
        "quarterlyGap": [{"q": str(k), "gap": r(v, 2)} for k, v in q.items()],
        "routes": [{"route": t.route, "identified": bool(t.link_identified), "unit": t.value_unit,
                    "value": r(t.value_at_measured_level, 1)} for t in routes.itertuples()],
        "royaltyBreakeven": [{"costUsdM": r(t.cost_usd_m, 0), "bp": r(t.required_royalty_uplift_basis_points, 1)} for t in royalty.itertuples()],
        "earningsPerPoint": {"central": r(mie["operational_unit_mapping"]["annual_adjusted_earnings_usd_m_per_BI_point"] * 1e6, 0),
                             "planning": [r(mie["operational_unit_mapping"]["planning_lower_usd_m_per_BI_point"] * 1e6, 0),
                                          r(mie["operational_unit_mapping"]["planning_upper_usd_m_per_BI_point"] * 1e6, 0)]},
        "valuationGate": {"missing": mon["valuation_gate"]["missing_inputs"], "fee": None},
    }


def main() -> None:
    events = build_events()
    exposure = build_exposure(events)
    evaluation = build_evaluation()
    monetization = build_monetization(exposure, evaluation)
    bi = j(ROOT / "data/curated/index/brand_index_manifest.json")
    data = {
        "meta": {"product": "EROI · Event Return on Investment", "brand": "Lenovo", "event": "FIFA",
                 "caseLabel": "FIFA × Lenovo", "built": date.today().isoformat(), "dataThrough": bi["sample"][1],
                 "announce": ANNOUNCE_EVENT, "firstPostWeek": exposure["total"]["from"],
                 "decisions": "ADR-0038 to ADR-0043", "notebooks": "reports/methods_annex/10_total_sponsorship_effect.ipynb, 40_brand_value.ipynb"},
        "events": events, "exposure": exposure, "evaluation": evaluation, "monetization": monetization,
    }
    OUT.write_text("/* Generated by frontend/scripts/build_eroi_data.py from production outputs. Do not edit by hand. */\n"
                   "window.EROI = " + json.dumps(data, separators=(",", ":"), default=str) + ";\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
