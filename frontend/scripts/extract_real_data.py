"""Extract real pipeline artifacts into frontend/data/real-data.js.

Reads curated/staged artifacts from the SRMP pipeline and writes a single
JS global (window.SRMP_REAL) consumed by the demo front end. This is the
only bridge between the pipeline and the demo; the demo never reads
data/raw|staged|curated at runtime (VISUALIZATION.md §0.4).

Run from the repo root:  python frontend/scripts/extract_real_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend" / "data" / "real-data.js"


def r(x, nd=3):
    if pd.isna(x):
        return None
    return round(float(x), nd)


def week_str(s):
    return pd.to_datetime(s).dt.strftime("%Y-%m-%d").tolist()


def main() -> None:
    out: dict = {}

    # --- Weekly Brand Index (v4 proxy-led, canonical simple index) --------
    idx = pd.read_csv(ROOT / "data/curated/index/brand_index_weekly.csv")
    out["brandIndexWeekly"] = {
        "week": week_str(idx["week"]),
        "level": [r(v) for v in idx["index_level"]],
        "se": [r(v) for v in idx["index_se"]],
        "sourceVersion": str(idx["source_version"].iloc[0]),
    }

    # --- Quarterly survey composite (GWI PC1) ------------------------------
    gwi = pd.read_csv(ROOT / "data/curated/index/brand_index_composite_quarterly.csv")
    out["surveyQuarterly"] = {
        "waveId": gwi["wave_id"].tolist(),
        "date": week_str(gwi["fieldwork_midpoint"]),
        "composite": [r(v) for v in gwi["composite_index"]],
    }

    # --- Blinkfire exposure, weekly by property ----------------------------
    bf = pd.read_csv(ROOT / "data/staged/blinkfire/blinkfire_exposure_weekly.csv")
    bf["week"] = pd.to_datetime(bf["week"]).dt.strftime("%Y-%m-%d")
    props = {}
    for pid, g in bf.groupby("property_id"):
        g = g.sort_values("week")
        props[pid] = {
            "week": g["week"].tolist(),
            "impressions": [int(v) for v in g["impressions"]],
            "views": [int(v) for v in g["views"]],
        }
    out["exposureWeekly"] = props
    fifa_family = ["fifa", "fwc", "fwwc", "fcwc", "fifae", "fifaewc", "infantino"]
    out["exposureMeta"] = {
        "fifaFamily": fifa_family,
        "totalImpressions": int(bf["impressions"].sum()),
        "fifaImpressions": int(bf.loc[bf.property_id.isin(fifa_family), "impressions"].sum()),
        "totalViews": int(bf["views"].sum()),
        "firstWeek": bf["week"].min(),
        "lastWeek": bf["week"].max(),
    }

    # --- Sponsorship funnel lift (aware vs unaware) -------------------------
    lift = pd.read_csv(ROOT / "data/staged/survey/sponsorship_funnel_lift.csv")
    out["funnelLift"] = [
        {
            "wave": row.reported_period,
            "property": row.property_id,
            "stage": row.funnel_stage,
            "aware": r(row.aware),
            "unaware": r(row.unaware),
            "lift": r(row.lift),
        }
        for row in lift.itertuples()
    ]

    # --- Counterfactual (announcement SCM, ADR-0021 donor pool) ------------
    cf = pd.read_csv(
        ROOT
        / "data/curated/experimental/sponsorship_counterfactual_v1/counterfactual_weekly.csv"
    )
    cf["week"] = pd.to_datetime(cf["week"]).dt.strftime("%Y-%m-%d")
    out["counterfactualWeekly"] = {
        "week": cf["week"].tolist(),
        "actual": [r(v) for v in cf["actual_index"]],
        "synthetic": [r(v) for v in cf["synthetic_index"]],
        "gap": [r(v) for v in cf["index_gap"]],
        "period": cf["period"].tolist(),
        "fifaAdstock": [r(v, 1) for v in cf["fifa_adstock"]],
    }
    out["counterfactualMeta"] = {
        "announcementWeek": "2024-10-14",
        "exposureWeightedGap": 1.033,
        "preRmspe": 0.244,
        "donorCount": 11,
    }

    # --- Donor panel (jointly scaled competitor salience) -------------------
    don = pd.read_csv(ROOT / "data/curated/trends/jointly_scaled_donor_trends.csv")
    don["week"] = pd.to_datetime(don["week"]).dt.strftime("%Y-%m-%d")
    base_donors = [  # 11 clean base donors per ADR-0021
        "Dell", "Asus", "Acer", "HP laptop", "Microsoft Surface", "Razer",
        "Logitech", "MacBook", "Corsair", "SteelSeries", "BenQ",
    ]
    donors = {}
    for term, g in don.groupby("term"):
        if term not in base_donors:
            continue
        g = (
            g.groupby("week", as_index=False)["interest_common_scale"].mean()
        ).sort_values("week")
        donors[term] = {
            "week": g["week"].tolist(),
            "value": [r(v, 2) for v in g["interest_common_scale"]],
        }
    out["donorPanel"] = donors

    # --- Commercial-intent search (category family, ADR-0010) --------------
    tw = pd.read_csv(ROOT / "data/curated/trends/trends_weekly_averaged.csv")
    cat = tw[tw["family"] == "category_purchase"].copy()
    ci = cat.groupby("week", as_index=False)["interest_mean"].mean().sort_values("week")
    out["commercialIntentWeekly"] = {
        "week": week_str(ci["week"]),
        "interest": [r(v, 2) for v in ci["interest_mean"]],
    }

    # --- GDELT earned media, aggregated to weeks ----------------------------
    gd = pd.read_csv(ROOT / "data/staged/gdelt/gdelt_brand_daily.csv")
    gd["date"] = pd.to_datetime(gd["date"])
    gd["week"] = gd["date"].dt.to_period("W-SUN").dt.start_time
    gw = gd.groupby("week").agg(volume=("news_volume", "sum"), tone=("mean_tone", "mean")).reset_index()
    out["earnedMediaWeekly"] = {
        "week": gw["week"].dt.strftime("%Y-%m-%d").tolist(),
        "volume": [int(v) for v in gw["volume"]],
        "tone": [r(v) for v in gw["tone"]],
    }

    # --- Events + official World Cup calendar -------------------------------
    ev = pd.read_csv(ROOT / "data/reference/events.csv")
    out["events"] = [
        {
            "id": row.event_id,
            "type": row.event_type,
            "name": row.event_name,
            "date": str(pd.to_datetime(row.event_timestamp_utc).date()),
            "property": row.property_id,
        }
        for row in ev.itertuples()
    ]
    cal = pd.read_csv(
        ROOT
        / "data/curated/experimental/world_cup_simulation_v1/official_fifa_calendar.csv"
    )
    cal["date"] = pd.to_datetime(cal["event_timestamp_utc"], format="ISO8601")
    cal["week"] = cal["date"].dt.to_period("W-SUN").dt.start_time
    wk = (
        cal.groupby("week")
        .agg(matches=("match_number", "count"), topStage=("stage", "last"))
        .reset_index()
    )
    out["worldCupCalendarWeekly"] = [
        {
            "week": row.week.strftime("%Y-%m-%d"),
            "matches": int(row.matches),
            "topStage": row.topStage,
        }
        for row in wk.itertuples()
    ]
    out["worldCupMeta"] = {
        "firstMatch": str(cal["date"].min().date()),
        "finalMatch": str(cal["date"].max().date()),
        "totalMatches": int(len(cal)),
    }

    # --- Simulated WC exposure (pipeline artifact, base scenario) -----------
    wce = pd.read_csv(
        ROOT
        / "data/curated/experimental/world_cup_simulation_v1/simulated_world_cup_exposure.csv"
    )
    wce = wce[wce["scenario"] == "base"].sort_values("week")
    out["worldCupSimulatedExposure"] = {
        "week": week_str(wce["week"]),
        "impressions": [int(v) for v in wce["impressions"]],
        "matches": [int(v) for v in wce["match_count"]],
    }

    # --- Earnings calibration (ADR-0025) ------------------------------------
    out["earningsCalibration"] = {
        "usdPerIndexPointPerYear": 6.253e6,
        "sourceAdr": "ADR-0025",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(out, separators=(",", ":"))
    OUT.write_text(
        "/* Generated by frontend/scripts/extract_real_data.py - do not edit by hand. */\n"
        f"window.SRMP_REAL = {payload};\n",
        encoding="utf-8",
    )
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({kb:.0f} KB)")
    print("fifa impressions:", out["exposureMeta"]["fifaImpressions"])
    print("total impressions:", out["exposureMeta"]["totalImpressions"])
    print("index weeks:", len(out["brandIndexWeekly"]["week"]),
          out["brandIndexWeekly"]["week"][0], "->", out["brandIndexWeekly"]["week"][-1],
          "last level:", out["brandIndexWeekly"]["level"][-1])
    print("donors:", list(donors))
    print("wc weeks:", len(out["worldCupCalendarWeekly"]))


if __name__ == "__main__":
    main()
