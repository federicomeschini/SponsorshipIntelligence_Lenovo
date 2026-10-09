"""Does the headline gap move with FIFA exposure or with Lenovo's other sponsorships? (ADR-0042)

Lenovo's motorsport sponsorships (Ducati, MotoGP, F1) were running before the
sample starts, so their usual exposure is part of what the synthetic control was
fitted on. Blinkfire only starts in late September 2024, so their pre-FIFA
exposure is back-cast: each property's observed ISO-week profile in its first
observed year, scaled year by year by its own co-brand Google search interest
(an observed intensity proxy). Exposure above that pre-FIFA baseline, and all
FIFA exposure, is incremental.

Three tests, all partial associations with Newey-West errors (diagnostic only;
the headline estimate is unchanged):
1. pre-period: did the gap move with back-cast non-FIFA exposure before FIFA existed?
2. post-period: does the gap move with FIFA exposure or with incremental non-FIFA exposure?
3. full sample: FIFA exposure (zero before the deal) against total non-FIFA exposure.
Each is run in levels without and with a linear trend, and in weekly changes.

FIFA-specific effect (ADR-0043, owner-selected primary): the post-period gap is split
into the parts explained by FIFA exposure, by the other sponsorships (relative to
their pre-FIFA baseline) and by Lenovo events, and a residual. The primary is the
FIFA part under the full-sample specification with a trend; bands are its 95%
interval and, as the upper attribution bound, the whole gap over the same weeks.
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

from srmp.experiments.brand_financial_bridge_v1 import _ols
from srmp.experiments.sponsorship_counterfactual_v1 import _weekly_event_controls
from srmp.experiments.world_cup_impact_v1_estimator import _write
from srmp.exposure.adstock import geometric_adstock

EVENTS = ["product_campaign_control", "promotion_calendar_control", "mixed_event_control"]


def _cobrand_scales(trends: pd.DataFrame, query: str, spec: dict[str, Any]) -> dict[int, float]:
    """Year scale factor = mean co-brand interest in the year / mean in the reference window."""
    series = trends[trends["query_id"].eq(query)].set_index("week")["interest_mean"]
    lo, hi = (pd.Timestamp(v) for v in spec["cobrand_reference_window"])
    reference = float(series[(series.index >= lo) & (series.index <= hi)].mean())
    years = sorted(set(series.index.year) & set(range(2018, pd.Timestamp(lo).year + 1)))
    return {int(y): float(series[series.index.year == y].mean()) / reference for y in years}


def backcast_property(observed: pd.Series, weeks: pd.DatetimeIndex, scales: dict[int, float],
                      active_from: pd.Timestamp, spec: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
    """Return (combined, baseline) weekly impressions over ``weeks``.

    combined: back-cast before Blinkfire coverage, observed after.
    baseline: the same ISO-week profile at the mean pre-FIFA intensity, every week.
    """
    lo, hi = (pd.Timestamp(v) for v in spec["profile_window"])
    window = observed[(observed.index >= lo) & (observed.index <= hi)]
    profile = window.groupby(window.index.isocalendar().week.clip(upper=52).to_numpy()).mean()
    iso = pd.Series(weeks.isocalendar().week.clip(upper=52).to_numpy(), index=weeks)
    shape = iso.map(profile).fillna(0.0)
    pre_fifa = float(np.mean([scales[y] for y in spec["pre_fifa_years"] if y in scales]))
    active = weeks >= active_from
    baseline = (shape * pre_fifa).where(active, 0.0)
    year_scale = pd.Series(weeks.year, index=weeks).map(scales).fillna(pre_fifa)
    backcast = (shape * year_scale).where(active, 0.0)
    start = observed.index.min()
    combined = backcast.where(weeks < start, observed.reindex(weeks).fillna(0.0))
    return combined, baseline


def _adstock(series: pd.Series, delta: float) -> pd.Series:
    return pd.Series(geometric_adstock(series.to_numpy(), delta), index=series.index)


def _z(series: pd.Series) -> pd.Series:
    return (series - series.mean()) / series.std(ddof=0)


def _regressions(frame: pd.DataFrame, regressors: list[str], test: str, hac_lags: int,
                 post_step: bool = False) -> list[pd.DataFrame]:
    """Levels without trend, levels with trend, and weekly changes; regressors standardised on the sample.

    ``post_step`` adds a fourth specification with a trend and an after-announcement step, so an
    exposure coefficient must come from variation within the post-period rather than from
    exposure merely being zero before the deal."""
    out = []
    events = [e for e in EVENTS if frame[e].std() > 0]
    levels = frame.copy()
    for column in regressors:
        levels[column] = _z(levels[column])
    levels["linear_time_z"] = _z(pd.Series(np.arange(len(levels), dtype=float), index=levels.index))
    specifications = [("levels_without_trend", regressors + events),
                      ("levels_with_trend", regressors + ["linear_time_z"] + events)]
    if post_step:
        levels["post_step"] = frame["period"].eq("post").astype(float)
        specifications.append(("levels_with_trend_and_post_step", regressors + ["linear_time_z", "post_step"] + events))
    for name, terms in specifications:
        rows, diag, _ = _ols(levels, "index_gap", terms, f"{test}:{name}", covariance="HAC", hac_lags=hac_lags)
        out.append(rows.assign(test=test, specification=name, observations=len(levels), r_squared=diag["r_squared"]))
    changes = frame[["index_gap"] + regressors].diff().join(frame[events]).dropna()
    for column in regressors:
        changes[column] = _z(changes[column])
    rows, diag, _ = _ols(changes, "index_gap", regressors + events, f"{test}:first_differences",
                         covariance="HAC", hac_lags=hac_lags)
    out.append(rows.assign(test=test, specification="first_differences", observations=len(changes),
                           r_squared=diag["r_squared"]))
    return out


def decompose(sample: pd.DataFrame, post: pd.DataFrame, rows: pd.DataFrame, references: dict[str, pd.Series]) -> dict[str, Any]:
    """Split the mean post-period gap into regression-explained parts and a residual.

    A term's part = coefficient x mean over post weeks of (x - reference) / sd(x over the
    estimation sample), i.e. the gap its exposure explains relative to the reference level
    (zero for FIFA, the pre-FIFA baseline for the other sponsorships). Events are 0/1 and
    enter unstandardised. Residual = mean gap - explained parts (trend, intercept, error).
    """
    estimate = rows.set_index("term")["estimate"]
    se = rows.set_index("term")["robust_se"]
    parts, scale = {}, {}
    for term, reference in references.items():
        if term in estimate:
            scale[term] = float((post[term] - reference.reindex(post.index)).mean() / sample[term].std(ddof=0))
            parts[term] = float(estimate[term] * scale[term])
    events = float(sum(estimate[e] * post[e].mean() for e in EVENTS if e in estimate))
    gap = float(post["index_gap"].mean())
    return {"mean_gap": gap, "parts": parts, "events": events,
            "residual": gap - sum(parts.values()) - events,
            "se": {term: float(se[term] * abs(scale[term])) for term in parts}}


def build(config_path: str = "config/experiments/sponsorship_exposure_timing_v1.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs, spec, delta = config["inputs"], config["backcast"], float(config["adstock_delta"])
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    gap = pd.read_parquet(inputs["total_effect_weekly"])
    gap["week"] = pd.to_datetime(gap["week"])
    gap = gap.set_index("week")[["index_gap", "period", "synthetic_index"]]
    weeks = gap.index
    exposure = pd.read_parquet(inputs["exposure"])
    exposure["week"] = pd.to_datetime(exposure["week"])
    wide = exposure.pivot_table(index="week", columns="property_id", values="impressions", aggfunc="sum").fillna(0.0)
    coverage_end = wide.index.max()
    taxonomy = pd.read_csv(inputs["property_taxonomy"])
    fifa_ids = taxonomy.loc[taxonomy["property_group"].eq(config["treatment_property_group"]), "property_id"].tolist()
    trends = pd.read_parquet(inputs["trends"])
    trends["week"] = pd.to_datetime(trends["week"]) + pd.Timedelta(days=1)   # W-SUN -> W-MON

    # FIFA: sponsorship exposure starts at the deal (ADR-0048). FIFA content before it (two days in 2024 with
    # Lenovo visible, before Lenovo was a partner) is not sponsorship exposure and is set to zero.
    fifa_all = wide[[c for c in wide if c in fifa_ids]].sum(axis=1).reindex(weeks).fillna(0.0)
    treatment_start = pd.Timestamp(config["treatment_start"])
    treatment_week = treatment_start - pd.Timedelta(days=treatment_start.weekday())
    fifa = fifa_all.where(weeks >= treatment_week, 0.0)
    prefifa_excluded = float(fifa_all[weeks < treatment_week].sum())
    combined, baseline, scale_rows = {}, {}, []
    for prop, meta in config["pre_existing"].items():
        scales = _cobrand_scales(trends, meta["cobrand_query"], spec)
        combined[prop], baseline[prop] = backcast_property(
            wide[prop], weeks, scales, pd.Timestamp(meta["active_from"]), spec)
        post = gap["period"].eq("post").to_numpy() & (weeks <= coverage_end)
        scale_rows.append({
            "property_id": prop, "active_from": str(meta["active_from"]), "upgraded_from": str(meta.get("upgraded_from")),
            **{f"scale_{y}": scales.get(y) for y in spec["pre_fifa_years"]},
            "pre_fifa_mean_scale": float(np.mean([scales[y] for y in spec["pre_fifa_years"] if y in scales])),
            "observed_post_impressions_m": float(combined[prop][post].sum() / 1e6),
            "baseline_post_impressions_m": float(baseline[prop][post].sum() / 1e6),
        })
    for prop in config["new_or_unknown"]:
        if prop in wide:
            combined[prop] = wide[prop].reindex(weeks).fillna(0.0)
            baseline[prop] = pd.Series(0.0, index=weeks)
    # ADR-0048: how well did the earlier back-cast (post-deal profile, co-brand scaling) predict the
    # pre-deal months that are now observed? Re-run it as if coverage started in October 2024.
    validation_rows = []
    check = config.get("backcast_validation")
    if check:
        old_spec = {**spec, **{k: check[k] for k in ("profile_window", "cobrand_reference_window")}}
        lo, hi = (pd.Timestamp(v) for v in check["check_window"])
        in_check = (weeks >= lo) & (weeks <= hi)
        for prop, meta in config["pre_existing"].items():
            truncated = wide[prop][wide.index >= pd.Timestamp(check["observed_from"])]
            predicted, _ = backcast_property(truncated, weeks, _cobrand_scales(trends, meta["cobrand_query"], old_spec),
                                             pd.Timestamp(meta["active_from"]), old_spec)
            observed_w = wide[prop].reindex(weeks).fillna(0.0)
            validation_rows.append({
                "property_id": prop, "weeks": int(in_check.sum()),
                "observed_impressions_m": float(observed_w[in_check].sum() / 1e6),
                "earlier_backcast_impressions_m": float(predicted[in_check].sum() / 1e6),
                "earlier_backcast_over_observed": float(predicted[in_check].sum() / observed_w[in_check].sum()),
                "weekly_correlation": float(np.corrcoef(predicted[in_check], observed_w[in_check])[0, 1]),
            })
    validation = pd.DataFrame(validation_rows)
    scale_table = pd.DataFrame(scale_rows)
    scale_table["observed_over_baseline"] = scale_table["observed_post_impressions_m"] / scale_table["baseline_post_impressions_m"]

    nonfifa_total = sum(combined.values())
    nonfifa_baseline = sum(baseline.values())
    weekly = pd.DataFrame({
        "index_gap": gap["index_gap"], "period": gap["period"], "synthetic_index": gap["synthetic_index"],
        "fifa_impressions": fifa, "nonfifa_impressions": nonfifa_total, "nonfifa_baseline_impressions": nonfifa_baseline,
        "fifa_adstock": _adstock(fifa, delta), "nonfifa_adstock": _adstock(nonfifa_total, delta),
        "nonfifa_baseline_adstock": _adstock(nonfifa_baseline, delta),
    })
    weekly["fifa_log_adstock"] = np.log1p(weekly["fifa_adstock"])
    weekly["nonfifa_log_adstock"] = np.log1p(weekly["nonfifa_adstock"])
    weekly["nonfifa_incremental_log_adstock"] = weekly["nonfifa_log_adstock"] - np.log1p(weekly["nonfifa_baseline_adstock"])
    events = _weekly_event_controls(pd.read_csv(inputs["product_campaign_events"]), int(config["event_carryover_weeks"]))
    weekly = weekly.join(events.reindex(weeks).fillna(0.0)).fillna({e: 0.0 for e in EVENTS})
    weekly["exposure_observed"] = weekly.index <= coverage_end
    weekly["nonfifa_source"] = np.where(weekly.index < wide.index.min(), "backcast", "observed")

    lags = int(config["hac_lags"])
    sample = weekly[weekly["exposure_observed"]]
    pre, post = sample[sample["period"].eq("pre")], sample[sample["period"].eq("post")]
    tables = (
        _regressions(pre, ["nonfifa_log_adstock"], "pre_period_nonfifa", lags)
        + _regressions(post, ["fifa_log_adstock", "nonfifa_incremental_log_adstock"], "post_period_incremental", lags)
        + _regressions(sample, ["fifa_log_adstock", "nonfifa_log_adstock"], "full_sample", lags, post_step=True)
    )
    coefficients = pd.concat(tables, ignore_index=True)
    _write(coefficients, target, "exposure_timing_coefficients")
    _write(weekly.reset_index(names="week"), target, "exposure_timing_weekly")
    _write(scale_table, target, "nonfifa_backcast_scales")
    if not validation.empty:
        _write(validation, target, "backcast_validation_2024")

    def coef(test: str, specification: str, term: str) -> dict[str, float]:
        row = coefficients[(coefficients["test"] == test) & (coefficients["specification"] == specification)
                           & (coefficients["term"] == term)].iloc[0]
        return {"points_per_sd": float(row["estimate"]), "hac_se": float(row["robust_se"]),
                "p": float(row["p_value_normal_approx"])}

    summary = {
        f"{test}:{s}": {t: coef(test, s, t) for t in terms}
        for test, terms in [("pre_period_nonfifa", ["nonfifa_log_adstock"]),
                            ("post_period_incremental", ["fifa_log_adstock", "nonfifa_incremental_log_adstock"]),
                            ("full_sample", ["fifa_log_adstock", "nonfifa_log_adstock"])]
        for s in ["levels_without_trend", "levels_with_trend", "first_differences"]
    }
    summary["full_sample:levels_with_trend_and_post_step"] = {
        t: coef("full_sample", "levels_with_trend_and_post_step", t) for t in ["fifa_log_adstock", "nonfifa_log_adstock", "post_step"]}
    # FIFA-specific effect (ADR-0043): decomposition under every levels specification; primary fixed in config.
    references = {"fifa_log_adstock": pd.Series(0.0, index=weekly.index),
                  "nonfifa_log_adstock": np.log1p(weekly["nonfifa_baseline_adstock"]),
                  "nonfifa_incremental_log_adstock": pd.Series(0.0, index=weekly.index)}
    decompositions = []
    for (test, specification), rows in coefficients.groupby(["test", "specification"], sort=False):
        if test == "pre_period_nonfifa" or specification == "first_differences":
            continue
        frame = sample if test == "full_sample" else post
        d = decompose(frame, post, rows, references)
        nonfifa = sum(v for k, v in d["parts"].items() if k.startswith("nonfifa"))
        decompositions.append({"test": test, "specification": specification, "mean_gap": d["mean_gap"],
                               "fifa": d["parts"].get("fifa_log_adstock"), "fifa_se": d["se"].get("fifa_log_adstock"),
                               "other_sponsorships": nonfifa, "events": d["events"], "residual": d["residual"]})
    decompositions = pd.DataFrame(decompositions)
    _write(decompositions, target, "fifa_specific_decomposition")
    primary_test, primary_spec = config["fifa_specific_effect"]["primary_specification"].split(":")
    p = decompositions[(decompositions["test"] == primary_test) & (decompositions["specification"] == primary_spec)].iloc[0]
    counterfactual = float(post["synthetic_index"].mean())
    low, high = p["fifa"] - 1.96 * p["fifa_se"], p["fifa"] + 1.96 * p["fifa_se"]
    fifa_specific = {
        "definition": config["fifa_specific_effect"]["definition"],
        "primary_specification": config["fifa_specific_effect"]["primary_specification"],
        "period": [str(post.index.min().date()), str(post.index.max().date())], "weeks": len(post),
        "primary_index_points": float(p["fifa"]),
        "primary_uplift_pct": 100 * float(p["fifa"]) / counterfactual,
        "statistical_band_95_index_points": [float(low), float(high)],
        "statistical_band_95_uplift_pct": [100 * low / counterfactual, 100 * high / counterfactual],
        "attribution_band_upper_index_points": float(p["mean_gap"]),
        "attribution_band_upper_uplift_pct": 100 * float(p["mean_gap"]) / counterfactual,
        "attribution_band_upper_definition": "whole gap over the same weeks: the unexplained residual also credited to FIFA",
        "counterfactual_index_level": counterfactual,
        "decomposition_index_points": {"fifa": float(p["fifa"]), "other_sponsorships": float(p["other_sponsorships"]),
                                       "events": float(p["events"]), "residual": float(p["residual"]),
                                       "total_gap": float(p["mean_gap"])},
        "specification_range_fifa_index_points": [float(decompositions["fifa"].min()), float(decompositions["fifa"].max())],
    }

    post_time = np.arange(len(post), dtype=float)
    manifest = {
        "experiment_id": config["experiment_id"], "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "headline_lift_index_points": json.loads(Path(inputs["total_effect_manifest"]).read_text(encoding="utf-8"))["total_effect"]["lift_index_points"],
        "samples": {"pre_weeks": len(pre), "post_weeks_with_exposure": len(post), "exposure_coverage_end": str(coverage_end.date()),
                    "backcast_weeks": int((sample["nonfifa_source"] == "backcast").sum())},
        "nonfifa_backcast": scale_table.to_dict("records"),
        "exposure_coverage": [str(wide.index.min().date()), str(coverage_end.date())],
        "treatment_start": str(treatment_start.date()), "fifa_impressions_before_treatment_excluded": prefifa_excluded,
        "backcast_validation_2024": validation.to_dict("records"),
        "post_collinearity": {
            "fifa_log_adstock_vs_time": float(np.corrcoef(post["fifa_log_adstock"], post_time)[0, 1]),
            "nonfifa_incremental_vs_time": float(np.corrcoef(post["nonfifa_incremental_log_adstock"], post_time)[0, 1]),
        },
        "summary": summary,
        "fifa_specific_effect": fifa_specific,
        "assumptions": [
            "Motorsport exposure is observed from January 2024; 2022-2023 is back-cast from the observed 2024 week profile, scaled by each year's co-brand search level relative to 2024 (ADR-0048); it is constructed, not observed.",
            "Co-brand search after June 2025 is not used for scaling because low-volume Lenovo queries step up in 2025Q3 (Google data change, ADR-0039).",
            "Exposure is digital and social only (Blinkfire); broadcast is not measured.",
            "Weeks after the last Blinkfire week are excluded, not treated as zero.",
        ],
        "interpretation_rule": ("Non-FIFA exposure is 'absorbed in the pre-trend' if the pre-period coefficient is near zero; "
                                "FIFA is supported as the incremental driver only if its post-period coefficient is positive in a "
                                "specification that also controls for a trend or uses weekly changes."),
    }
    (target / "exposure_timing_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/sponsorship_exposure_timing_v1.yaml")
    args = parser.parse_args()
    build(args.config)
