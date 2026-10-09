"""Television check for the FIFA-specific effect (ADR-0046).

The FIFA exposure measure (Blinkfire) counts social media impressions only. The only
broadcast-inclusive measure is the client's media-value export, which covers May 2025 to
March 2026 and so misses the 2026 World Cup. This experiment asks whether leaving
television out biases the FIFA-specific effect (ADR-0043):

1. Observed window: the production regression re-run on weeks to March 2026, with and
   without media value as a second FIFA exposure channel.
2. Forward simulation: media value extended through the World Cup from the official match
   calendar, with a value per match by stage calibrated on the 2025 Club World Cup and four
   tournament scales; the regression re-run on the full production sample.

Media value enters only as a unitless relative intensity (ADR-0028); every amount written
here is relative (Club World Cup = 1, or group match = 1), never money (P1).
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
from scipy.optimize import nnls

from srmp.experiments.brand_financial_bridge_v1 import _ols
from srmp.experiments.sponsorship_exposure_timing_v1 import EVENTS, _z, decompose
from srmp.experiments.world_cup_impact_v1_estimator import _write
from srmp.exposure.adstock import geometric_adstock

STAGES = ["group", "knockout", "late"]


def _monday(stamp: pd.Timestamp) -> pd.Timestamp:
    return (stamp - pd.Timedelta(days=stamp.weekday())).normalize()


def _media_weekly(path: str, measure: str) -> tuple[pd.Series, pd.DataFrame]:
    daily = pd.read_parquet(path)
    if not bool(daily["banned_as_feature"].all()):
        raise ValueError("Media value rows must carry the monetary-use ban flag.")
    daily["week"] = pd.to_datetime(daily["week"])
    weekly = daily.groupby("week")[measure].sum()
    grid = pd.date_range(weekly.index.min(), weekly.index.max(), freq="W-MON")
    return weekly.reindex(grid, fill_value=0.0), daily


def _fit(sample: pd.DataFrame, fifa_terms: list[str], hac_lags: int) -> dict[str, Any]:
    """Production primary specification (levels, linear trend, other sponsorships, events) with the given FIFA terms."""
    frame = sample.copy()
    terms = fifa_terms + ["nonfifa_log_adstock"]
    for term in terms:
        frame[term] = _z(frame[term])
    frame["linear_time_z"] = _z(pd.Series(np.arange(len(frame), dtype=float), index=frame.index))
    events = [e for e in EVENTS if frame[e].std() > 0]
    rows, diag, _ = _ols(frame, "index_gap", terms + ["linear_time_z"] + events, "tv_check",
                         covariance="HAC", hac_lags=hac_lags)
    post = sample[sample["period"].eq("post")]
    zero = pd.Series(0.0, index=sample.index)
    d = decompose(sample, post, rows, {"fifa_log_adstock": zero, "tv_log_adstock": zero,
                                       "nonfifa_log_adstock": np.log1p(sample["nonfifa_baseline_adstock"])})
    est = rows.set_index("term")
    fifa_total = sum(d["parts"].get(t, 0.0) for t in fifa_terms)
    return {
        "weeks": len(sample), "post_weeks": len(post), "r_squared": float(diag["r_squared"]),
        "mean_gap": d["mean_gap"], "fifa_total": float(fifa_total),
        "social_part": float(d["parts"]["fifa_log_adstock"]) if "fifa_log_adstock" in fifa_terms else None,
        "tv_part": float(d["parts"]["tv_log_adstock"]) if "tv_log_adstock" in fifa_terms else None,
        "not_attributed": float(d["mean_gap"] - fifa_total),
        "p_social": float(est.loc["fifa_log_adstock", "p_value_normal_approx"]) if "fifa_log_adstock" in fifa_terms else None,
        "p_tv": float(est.loc["tv_log_adstock", "p_value_normal_approx"]) if "tv_log_adstock" in fifa_terms else None,
    }


def build(config_path: str = "config/experiments/tv_exposure_check_v1.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs, delta, lags = config["inputs"], float(config["adstock_delta"]), int(config["hac_lags"])
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    weekly = pd.read_parquet(inputs["exposure_timing_weekly"])
    weekly["week"] = pd.to_datetime(weekly["week"])
    weekly = weekly.set_index("week")
    production = weekly[weekly["exposure_observed"]].copy()
    timing = json.loads(Path(inputs["exposure_timing_manifest"]).read_text(encoding="utf-8"))

    observed, daily = _media_weekly(inputs["media_values"], config["measure"])
    first, last = observed.index.min(), observed.index.max()

    # Blinkfire FIFA impressions by week (social media), for correlations and the scale link.
    taxonomy = pd.read_csv(inputs["property_taxonomy"])
    fifa_ids = taxonomy.loc[taxonomy["property_group"].eq("fifa"), "property_id"].tolist()
    bf = pd.read_parquet(inputs["blinkfire"])
    bf["week"] = pd.to_datetime(bf["week"])
    social = bf[bf["property_id"].isin(fifa_ids)].groupby("week")["impressions"].sum()

    # Weeks without media value since the deal (October 2024 - April 2025) are filled from social media at
    # the television-to-social ratio observed over every week with media value (ADR-0048), not set to zero.
    tv_per_social_all = float(observed.sum() / social.reindex(observed.index).fillna(0.0).sum())
    fill_from = pd.Timestamp(config["backward_fill"]["from"])
    backward_grid = pd.date_range(fill_from, first - pd.Timedelta(weeks=1), freq="W-MON")
    backward = social.reindex(backward_grid).fillna(0.0) * tv_per_social_all

    def tv_log(series_rel: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
        """log(1 + adstock / mean adstock over the observed media-value weeks): unitless, zero before the deal."""
        values = series_rel.reindex(index).fillna(0.0)
        adstock = pd.Series(geometric_adstock(values.to_numpy(float), delta), index=index)
        return np.log1p(adstock / adstock.loc[first:last].mean())

    # 1. Observed window -----------------------------------------------------------------
    window = weekly[weekly.index <= last].copy()
    window["tv_log_adstock"] = tv_log(pd.concat([backward, observed]).sort_index() / observed.mean(), window.index)
    cover = window.loc[first:last]
    overlap = {
        "weeks": int(len(cover)), "weeks_with_tv_value": int((observed > 0).sum()),
        "corr_tv_vs_social_weekly": float(observed.corr(social.reindex(observed.index).fillna(0.0))),
        "corr_tv_vs_social_adstock_log": float(cover["tv_log_adstock"].corr(cover["fifa_log_adstock"])),
        "corr_tv_vs_gap": float(cover["tv_log_adstock"].corr(cover["index_gap"])),
        "corr_social_vs_gap": float(cover["fifa_log_adstock"].corr(cover["index_gap"])),
    }
    observed_fits = {
        "social_only": _fit(window, ["fifa_log_adstock"], lags),
        "social_and_tv": _fit(window, ["fifa_log_adstock", "tv_log_adstock"], lags),
        "tv_only": _fit(window, ["tv_log_adstock"], lags),
    }

    # 2. Calibration: value per match by stage on the Club World Cup -------------------------
    cal = config["calibration"]
    schedule = pd.DataFrame([{"week": _monday(pd.Timestamp(day)), "stage": stage, "matches": n}
                             for stage, days in cal["matches_per_day"].items() for day, n in days.items()])
    cwc = schedule.pivot_table(index="week", columns="stage", values="matches", aggfunc="sum", fill_value=0)[STAGES]
    cwc_media = (daily[daily["competition"].eq(cal["competition"])].assign(week=lambda d: pd.to_datetime(d["week"]))
                 .groupby("week")[config["measure"]].sum())
    cwc_total = float(cwc_media.reindex(cwc.index).fillna(0.0).sum())
    target_rel = cwc_media.reindex(cwc.index).fillna(0.0) / cwc_total             # Club World Cup = 1
    per_match, _ = nnls(cwc.to_numpy(float), target_rel.to_numpy())
    per_match = dict(zip(STAGES, per_match))
    fitted = cwc.to_numpy(float) @ np.array([per_match[s] for s in STAGES])
    tail_week = pd.Timestamp(cal["tail_week_after_final"])
    tail_share = float(cwc_media.get(tail_week, 0.0) / cwc_media.get(tail_week - pd.Timedelta(weeks=1)))
    calibration = {
        "competition": cal["competition"], "matches": int(cwc.to_numpy().sum()), "source": cal["source"],
        "value_per_match_relative_to_group": {s: float(per_match[s] / per_match["group"]) for s in STAGES},
        "fit_weekly_correlation": float(np.corrcoef(fitted, target_rel.to_numpy())[0, 1]),
        "tail_share_week_after_final": tail_share,
        "weekly": [{"week": str(w.date()), **{s: int(cwc.loc[w, s]) for s in STAGES},
                    "observed_share": float(target_rel.loc[w]), "fitted_share": float(f)} for w, f in zip(cwc.index, fitted)],
    }

    # 3. World Cup 2026 calendar -> weekly matches by stage ----------------------------------
    calendar = pd.read_parquet(inputs["fifa_calendar"])
    calendar["local"] = (pd.to_datetime(calendar["event_timestamp_utc"], utc=True)
                         .dt.tz_convert(config["match_timezone"]).dt.tz_localize(None))
    calendar["stage_group"] = calendar["stage"].map(config["stage_map"])
    if calendar["stage_group"].isna().any():
        raise ValueError(f"Unmapped World Cup stages: {calendar.loc[calendar['stage_group'].isna(), 'stage'].unique()}")
    calendar["week"] = calendar["local"].map(_monday)
    wc = calendar.pivot_table(index="week", columns="stage_group", values="match_number", aggfunc="count",
                              fill_value=0).reindex(columns=STAGES, fill_value=0)
    social_per_match = {"club_world_cup": float(social.reindex(cwc.index).fillna(0.0).sum() / cwc.to_numpy().sum()),
                        "world_cup": float(social.reindex(wc.index).fillna(0.0).sum() / wc.to_numpy().sum())}
    scale_bf = social_per_match["world_cup"] / social_per_match["club_world_cup"]
    tv_per_social = 1.0 / float(social.reindex(cwc.index).fillna(0.0).sum())       # Club World Cup TV (=1) per social impression

    forward_grid = pd.date_range(last + pd.Timedelta(weeks=1), production.index.max(), freq="W-MON")
    final_week = wc.index.max()

    def scenario_series(spec: dict[str, Any]) -> pd.Series:
        if spec["scale"] == "blinkfire_weekly":
            weeks = wc.index.union([final_week + pd.Timedelta(weeks=1)])
            s = social.reindex(weeks).fillna(0.0) * tv_per_social_all / cwc_total
        else:
            scale = scale_bf if spec["scale"] == "blinkfire_per_match" else float(spec["scale"])
            s = (wc[STAGES].to_numpy(float) @ np.array([per_match[x] for x in STAGES])) * scale
            s = pd.Series(s, index=wc.index)
            s.loc[final_week + pd.Timedelta(weeks=1)] = s.loc[final_week] * tail_share
        return s.reindex(forward_grid).fillna(0.0)

    # Observed in Club-World-Cup units, then the forward weeks, then the regression on the full sample.
    observed_cwc_units = observed / cwc_total
    model_terms = ["fifa_log_adstock", "nonfifa_log_adstock", "linear_time_z"]
    base = production.copy()
    for t in ["fifa_log_adstock", "nonfifa_log_adstock"]:
        base[t] = _z(base[t])
    base["linear_time_z"] = _z(pd.Series(np.arange(len(base), dtype=float), index=base.index))
    events = [e for e in EVENTS if base[e].std() > 0]
    rows0, _, _ = _ols(base, "index_gap", model_terms + events, "production", covariance="HAC", hac_lags=lags)
    b0 = rows0.set_index("term")["estimate"]
    model_error = base["index_gap"] - (b0["intercept"] + sum(b0[t] * base[t] for t in model_terms + events))

    scenario_rows, weekly_rows = [], {}
    for spec in config["scenarios"]:
        forward = scenario_series(spec)
        full = pd.concat([backward / cwc_total, observed_cwc_units, forward]).sort_index()
        weekly_rows[spec["id"]] = full
        sample = production.copy()
        sample["tv_log_adstock"] = tv_log(full, sample.index)
        with_tv = _fit(sample, ["fifa_log_adstock", "tv_log_adstock"], lags)
        tv_only = _fit(sample, ["tv_log_adstock"], lags)
        err = pd.DataFrame({"err": model_error, "tv_z": _z(sample["tv_log_adstock"])}).loc[first:]
        er, _, _ = _ols(err, "err", ["tv_z"], "error", covariance="HAC", hac_lags=lags)
        er = er.set_index("term")
        scenario_rows.append({
            "scenario": spec["id"], "label": spec["label"],
            "world_cup_vs_club_world_cup": float(forward.sum()),
            "fifa_total_with_tv": with_tv["fifa_total"], "social_part": with_tv["social_part"], "tv_part": with_tv["tv_part"],
            "p_tv": with_tv["p_tv"], "not_attributed_with_tv": with_tv["not_attributed"],
            "fifa_total_tv_only": tv_only["fifa_total"], "p_tv_only": tv_only["p_tv"],
            "change_vs_primary": with_tv["fifa_total"] - timing["fifa_specific_effect"]["primary_index_points"],
            "model_error_slope_per_sd": float(er.loc["tv_z", "estimate"]), "model_error_p": float(er.loc["tv_z", "p_value_normal_approx"]),
        })
    scenarios = pd.DataFrame(scenario_rows)
    _write(scenarios, target, "tv_exposure_scenarios")
    series = pd.DataFrame(weekly_rows).rename_axis("week")
    series["social_impressions_relative"] = social.reindex(series.index).fillna(0.0) / social.reindex(cwc.index).fillna(0.0).sum()
    series["tv_source"] = np.where(series.index <= last, "observed", "simulated")
    _write(series.reset_index(), target, "tv_exposure_weekly_relative")

    primary = timing["fifa_specific_effect"]
    manifest = {
        "experiment_id": config["experiment_id"], "status": config["status"],
        "role": "sensitivity_only_relative_exposure_intensity", "decision": "ADR-0046", "monetary_totals_used": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tv_coverage": {"from": str(first.date()), "to": str(last.date()),
                        "misses": ["October 2024 - April 2025 (announcement months)", "2026 Men's World Cup (June - July 2026)"]},
        "primary_fifa_specific_index_points": primary["primary_index_points"],
        "primary_band_95_index_points": primary["statistical_band_95_index_points"],
        "overlap": overlap,
        "observed_window": {"to": str(last.date()), **observed_fits},
        "calibration": calibration,
        "world_cup_matches": int(wc.to_numpy().sum()),
        "social_impressions_per_match": social_per_match, "blinkfire_scale": scale_bf,
        "backward_fill": {"from": str(backward_grid.min().date()), "to": str(backward_grid.max().date()), "weeks": len(backward_grid),
                          "method": "weekly Blinkfire FIFA impressions x television-to-social ratio over every week with media value",
                          "share_of_club_world_cup": float(backward.sum() / cwc_total)},
        "forward_to": str(forward_grid.max().date()),
        "scenarios": scenarios.to_dict("records"),
        "summary": {
            "max_change_vs_primary_index_points": float(scenarios["change_vs_primary"].abs().max()),
            "fifa_total_with_tv_range": [float(scenarios["fifa_total_with_tv"].min()), float(scenarios["fifa_total_with_tv"].max())],
            "tv_part_range": [float(scenarios["tv_part"].min()), float(scenarios["tv_part"].max())],
            "tv_p_range": [float(scenarios["p_tv"].min()), float(scenarios["p_tv"].max())],
            "within_primary_band": bool(scenarios["fifa_total_with_tv"].between(*primary["statistical_band_95_index_points"]).all()),
        },
        "assumptions": [
            "Media value is used only as a weekly relative intensity (adstock / its mean over the observed weeks); no monetary amount is used or reported.",
            "Media value is zero before the deal; October 2024 - April 2025 (no rows in the export) is filled from Blinkfire FIFA impressions at the television-to-social ratio of the observed weeks (ADR-0048).",
            "The World Cup value per match by stage is calibrated on the 2025 Club World Cup; the tournament scale is a scenario.",
            "Simulated weeks follow the match calendar, which is also when social media exposure peaks, so the two series overlap by construction.",
        ],
    }
    (target / "tv_exposure_check_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/tv_exposure_check_v1.yaml")
    result = build(parser.parse_args().config)
    s = result["summary"]
    print(f"TV check: FIFA-specific with TV {s['fifa_total_with_tv_range'][0]:+.2f} to {s['fifa_total_with_tv_range'][1]:+.2f} "
          f"(primary {result['primary_fifa_specific_index_points']:+.2f}); within band: {s['within_primary_band']}")
