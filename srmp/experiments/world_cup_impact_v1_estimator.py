"""Preregistered World Cup impact estimator (ADR-0019 protocol, ADR-0029 rules).

Runs on whatever data exist. Every estimate is labelled interim until all
acceptance gates pass; only then is a row handed to monetization.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from srmp.index.brand_factor import donor_shares_of_search
import pyarrow.parquet as pq

from srmp.counterfactual import scm
from srmp.experiments.sponsorship_counterfactual_v1 import (
    _media_value_intensity,
    _monday,
    _weekly_event_controls,
)
from srmp.exposure.adstock import geometric_adstock

ACCEPTED_SCHEMA = pa.schema([
    ("estimate_id", pa.string()),
    ("treatment_window", pa.string()),
    ("delta_index_attrib", pa.float64()),
    ("lower_bound", pa.float64()),
    ("upper_bound", pa.float64()),
    ("pre_rmspe", pa.float64()),
    ("placebo_p_value", pa.float64()),
    ("accepted_for_valuation", pa.bool_()),
    ("assumptions_hash", pa.string()),
])


ROLES = {
    "augmented_scm": "primary",
    "simplex_scm": "robustness",
    "synthetic_did": "robustness",
    "generalized_scm_factor": "robustness_category_shock_added_after_partial_outcome_ADR_0029",
}


def _week_start(value: Any) -> pd.Timestamp:
    day = pd.Timestamp(value)
    return day - pd.Timedelta(days=day.weekday())


def _write(frame: pd.DataFrame, target: Path, name: str) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, target / f"{name}.parquet")
    pacsv.write_csv(table, target / f"{name}.csv")


def _panel(config: dict[str, Any]) -> tuple[pd.DataFrame, list[str], list[str]]:
    sources = config["data_sources"]
    index = pd.read_parquet(sources["brand_index"]["path"])[["week", "index_level"]]
    index["week"] = pd.to_datetime(index["week"])
    trends = pd.read_parquet(sources["jointly_scaled_donor_trends"]["path"])
    trends["week"] = _monday(trends["week"])
    registry = pd.read_csv("data/reference/counterfactual_donor_registry.csv")
    base = registry.loc[registry["inclusion_policy"].eq("base"), "query_id"].tolist()
    sensitivity = [f"donor_{name}" for name in config["counterfactual"].get("sensitivity_only_donors", [])]
    donors = trends[trends["query_id"].isin(base + sensitivity)].pivot(
        index="week", columns="query_id", values="interest_common_scale"
    )
    share = config["estimation"].get("donor_share_of_search")
    if share:
        # Same basis as the Brand Index: each donor's share against the base rivals without itself (ADR-0040).
        rivals = registry.loc[registry["inclusion_policy"].isin(share["denominator_policies"]), "query_id"]
        donors = donor_shares_of_search(donors, [r for r in rivals if r in donors])
    panel = index.set_index("week").join(donors, how="inner").sort_index()
    # Google revises the trailing weeks of every pull; they never enter estimation.
    trailing = int(config["estimation"].get("provisional_trailing_weeks", 0))
    if trailing:
        panel = panel.iloc[:-trailing]
    complete = [name for name in base if name in panel and panel[name].notna().all()]
    return panel, complete, [name for name in sensitivity if name in panel]


def _vintages(config: dict[str, Any]) -> dict[str, Any]:
    """Pull timestamps of the outcome and donor Trends series."""
    spec = config["estimation"]["vintage_alignment"]
    stamps = {}
    for name, path in spec["manifests"].items():
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        stamps[name] = manifest["generated_at_utc"]
    times = [pd.Timestamp(value) for value in stamps.values()]
    gap_days = (max(times) - min(times)).total_seconds() / 86400
    return {"pulls": stamps, "max_gap_days": gap_days,
            "aligned": gap_days <= float(spec["max_days_between_pulls"])}


def _exposure(config: dict[str, Any], weeks: pd.DatetimeIndex) -> tuple[pd.Series, pd.Timestamp]:
    """FIFA-family adstock on the panel weeks; NaN where Blinkfire is unobserved."""
    spec = config["estimation"]["exposure_weighting"]
    path = Path(config["data_sources"][spec["source"]]["path"])
    weekly = pd.read_parquet(path)
    weekly["week"] = pd.to_datetime(weekly["week"])
    taxonomy = pd.read_csv("data/reference/property_taxonomy.csv")
    fifa = set(taxonomy.loc[taxonomy["property_group"].eq(spec["property_group"]), "property_id"])
    fifa_weekly = weekly[weekly["property_id"].isin(fifa)].groupby("week")["impressions"].sum()
    grid = pd.date_range(fifa_weekly.index.min(), fifa_weekly.index.max(), freq="W-MON")
    fifa_weekly = fifa_weekly.reindex(grid, fill_value=0)
    adstock = pd.Series(geometric_adstock(fifa_weekly, float(spec["adstock_delta"])), index=grid)
    manifest = json.loads((path.parent / "pull_manifest.json").read_text(encoding="utf-8"))
    observed_through = pd.Timestamp(manifest["date_max"])
    return adstock.reindex(weeks), observed_through


def _estimands(
    gap: pd.Series, weights: pd.Series, windows: dict[str, pd.Series], event_weeks: pd.Series,
) -> dict[str, float | None]:
    def mean(mask: pd.Series) -> float | None:
        values = gap[mask]
        return float(values.mean()) if len(values) else None

    def weighted(mask: pd.Series) -> float | None:
        usable = mask & weights.notna() & (weights > 0)
        if not usable.any():
            return None
        return float(np.average(gap[usable], weights=weights[usable]))

    window = windows["exposure_window"]
    rolling = gap[window].rolling(4).mean().dropna()
    return {
        "primary_exposure_weighted_gap": weighted(window),
        "primary_event_weeks_excluded": weighted(window & ~event_weeks),
        "all_post_mean_gap": mean(window),
        "tournament_mean_gap": mean(windows["tournament"]),
        "peak_four_week_mean_gap": float(rolling.max()) if len(rolling) else None,
        "post_event_persistence_mean_gap": mean(windows["persistence"]),
    }


def _fit_methods(
    target: np.ndarray, donors: np.ndarray, pre: np.ndarray, post: np.ndarray, config: dict[str, Any]
) -> tuple[dict[str, scm.Fit], float, list[dict], float]:
    y, x, _, y_sd = scm.standardize(target, donors, pre)
    ascm = config["estimation"]["ascm"]
    multiplier, grid = scm.select_ridge_lambda(
        y, x, pre, ascm["ridge_lambda_multipliers"], int(ascm["inner_validation_weeks"])
    )
    fits = {
        "augmented_scm": scm.fit_ascm(y, x, pre, multiplier),
        "simplex_scm": scm.fit_simplex(y, x, pre),
        "synthetic_did": scm.fit_sdid(y, x, pre, post),
    }
    shock = config["estimation"].get("category_shock_robustness")
    if shock:
        count, _ = scm.select_factor_count(
            y, x, pre, int(shock["max_factors"]), int(shock["cv_block_weeks"])
        )
        fits["generalized_scm_factor"] = scm.fit_factor_model(y, x, pre, count)
    return fits, multiplier, grid, y_sd


def _holdout(
    target: np.ndarray, donors: np.ndarray, pre: np.ndarray, weeks: int, config: dict[str, Any]
) -> dict[str, float]:
    """Refit on pre minus the final holdout weeks; report out-of-sample RMSPE."""
    index = np.flatnonzero(pre)
    train = np.zeros_like(pre)
    train[index[:-weeks]] = True
    holdout = np.zeros_like(pre)
    holdout[index[-weeks:]] = True
    fits, _, _, y_sd = _fit_methods(target, donors, train, holdout, config)
    return {name: scm.rmspe(fit.gap_z[holdout]) * y_sd for name, fit in fits.items()}


def _confounder_diagnostics(
    gap: pd.Series, target: np.ndarray, donors: np.ndarray, base: list[str],
    weights: np.ndarray, y_sd: float, pre: np.ndarray, window: pd.Series,
    treatment: pd.Timestamp, config: dict[str, Any],
) -> dict[str, Any]:
    """Checks that separate a World Cup effect from shocks the SCM may not absorb.

    Diagnostics only (ADR-0029): none of them alters the preregistered estimate.
    """
    weeks = gap.index
    window_len = int(window.sum())
    y, x, _, _ = scm.standardize(target, donors, pre)

    # 1. Pre-trend: was the gap already moving before treatment?
    last = gap[pre][-8:]
    pre_trend = {"last_8_pre_weeks_mean_gap": float(last.mean()),
                 "last_8_pre_weeks_slope_per_week": float(np.polyfit(np.arange(len(last)), last, 1)[0])}

    # 2. Same calendar window in earlier years: Lenovo minus weighted donors.
    seasonal = []
    for years_back in range(1, 5):
        start = _week_start(treatment - pd.Timedelta(weeks=52 * years_back))
        before = (weeks >= start - pd.Timedelta(weeks=8)) & (weeks < start)
        during = (weeks >= start) & (weeks < start + pd.Timedelta(weeks=max(window_len, 1)))
        if during.sum() < 3 or before.sum() < 8:
            continue
        change = (y[during].mean() - y[before].mean()) - weights @ (x[during].mean(0) - x[before].mean(0))
        seasonal.append({"window_start": str(start.date()), "lenovo_minus_weighted_donors_index_points": float(change * y_sd)})
    if window_len:
        before = (weeks >= treatment - pd.Timedelta(weeks=8)) & (weeks < treatment)
        during = np.asarray(window)
        current = float(((y[during].mean() - y[before].mean())
                         - weights @ (x[during].mean(0) - x[before].mean(0))) * y_sd)
    else:
        current = None

    # 3. Common shock: how far the median donor moved in the window, in pre-sd units.
    donor_shift = float(np.median(x[np.asarray(window)].mean(0))) if window_len else None

    # 4. Leave-one-donor-out primary method.
    loo = {}
    post = np.asarray(window)
    if window_len:
        for position, name in enumerate(base):
            keep = [index for index in range(len(base)) if index != position]
            fits, _, _, sd = _fit_methods(target, donors[:, keep], pre, post, config)
            loo[name] = float(fits["augmented_scm"].gap_z[post].mean() * sd)

    # 5. Category-shock loading on the common-anchor panel: Lenovo YoY on donor-median YoY.
    loading = {"status": "unavailable"}
    trends = pd.read_parquet(config["data_sources"]["jointly_scaled_donor_trends"]["path"])
    trends["week"] = _monday(trends["week"])
    panel = trends[trends["query_id"].isin(base + ["anchor_lenovo"])].groupby(
        ["week", "query_id"])["interest_common_scale"].mean().unstack()
    if "anchor_lenovo" in panel:
        yoy = 100 * np.log(panel / panel.shift(52))
        frame = pd.DataFrame({"lenovo": yoy["anchor_lenovo"], "category": yoy[base].median(axis=1)}).dropna()
        fit_rows = frame[frame.index < treatment]
        design = np.column_stack([np.ones(len(fit_rows)), fit_rows["category"]])
        coef = np.linalg.lstsq(design, fit_rows["lenovo"], rcond=None)[0]
        residual = frame["lenovo"] - (coef[0] + coef[1] * frame["category"])
        resid_sd = float((fit_rows["lenovo"] - design @ coef).std())
        final_week = _week_start(config["milestones"]["tournament_end"])
        tournament = residual[(residual.index >= treatment) & (residual.index <= final_week)]
        after = residual[residual.index > final_week]
        loading = {
            "status": "computed",
            "definition": "Lenovo YoY % on donor-median YoY %, fitted on pre-treatment weeks",
            "loading": float(coef[1]), "intercept": float(coef[0]), "residual_sd_pct": resid_sd,
            "raw_lenovo_minus_category_tournament_pct": float(
                (frame["lenovo"] - frame["category"])[tournament.index].mean()) if len(tournament) else None,
            "loading_adjusted_residual_tournament_pct": float(tournament.mean()) if len(tournament) else None,
            "loading_adjusted_residual_after_final_pct": float(after.mean()) if len(after) else None,
            "tournament_residual_in_sd_units": float(tournament.mean() / resid_sd) if len(tournament) else None,
            "category_yoy_peak_pct": float(frame.loc[frame.index < treatment, "category"].tail(26).max()),
        }
    return {
        "role": "diagnostic_only_does_not_change_preregistered_estimate",
        "pre_trend": pre_trend,
        "seasonal_same_window_prior_years": seasonal,
        "current_window_same_construction_index_points": current,
        "median_donor_shift_in_window_pre_sd": donor_shift,
        "leave_one_donor_out_mean_gap": loo,
        "category_shock_loading": loading,
    }


def estimate_world_cup_impact(
    config: dict[str, Any], protocol_hash: str, output_dir: str | Path,
) -> dict[str, Any]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    milestones = config["milestones"]
    rules = config["counterfactual"]
    panel, base, sensitivity = _panel(config)
    weeks = panel.index

    approved_activation = milestones.get("activation_start")
    treatment = _week_start(approved_activation or milestones["tournament_start"])
    final_week = _week_start(milestones["tournament_end"])
    window_end = _week_start(milestones["primary_post_window_end"])
    pre = np.asarray(weeks < treatment)
    post = np.asarray(weeks >= treatment)
    as_series = lambda mask: pd.Series(mask, index=weeks)  # noqa: E731
    windows = {
        "exposure_window": as_series((weeks >= treatment) & (weeks <= window_end)),
        "tournament": as_series((weeks >= treatment) & (weeks <= final_week)),
        "persistence": as_series((weeks > final_week) & (weeks <= window_end)),
    }
    post_window = np.asarray(windows["exposure_window"])

    exposure, exposure_through = _exposure(config, weeks)
    events = pd.read_csv(config["data_sources"]["product_launch_controls"]["path"])
    event_any = _weekly_event_controls(events, carryover_weeks=1).max(axis=1)
    event_weeks = as_series(np.asarray(event_any.reindex(weeks, fill_value=0.0) > 0))

    target = panel[config["estimation"]["outcome_column"]].to_numpy(dtype=float)
    donors = panel[base].to_numpy(dtype=float)
    fits, multiplier, lambda_grid, y_sd = _fit_methods(target, donors, pre, post_window, config)
    holdout_rmspe = _holdout(target, donors, pre, int(rules["validation_holdout_weeks"]), config)

    estimate_rows, paths = [], pd.DataFrame({"week": weeks, "actual_index": target})
    for name, fit in fits.items():
        gap = pd.Series(fit.gap_z * y_sd, index=weeks)
        paths[f"{name}_synthetic_index"] = target - gap.to_numpy()
        paths[f"{name}_gap_index_points"] = gap.to_numpy()
        values = _estimands(gap, exposure, windows, event_weeks)
        estimate_rows.append({
            "method": name, "role": ROLES[name],
            "pre_rmspe_index_points": scm.rmspe(fit.gap_z[pre]) * y_sd,
            "holdout_rmspe_index_points": holdout_rmspe[name],
            **values,
        })
    paths["fifa_exposure_adstock"] = exposure.to_numpy()
    paths["exposure_observed"] = np.asarray(weeks <= _week_start(exposure_through))
    paths["known_lenovo_event_week"] = event_weeks.to_numpy()
    paths["period"] = np.where(pre, "pre", np.where(post_window, "registered_window", "after_window"))

    # Sensitivity-only donors join the pool; the primary keeps the base registry pool.
    if sensitivity:
        with_sensitivity = panel[base + sensitivity].to_numpy(dtype=float)
        sens_fits, _, _, sens_sd = _fit_methods(target, with_sensitivity, pre, post_window, config)
        gap = pd.Series(sens_fits["augmented_scm"].gap_z * sens_sd, index=weeks)
        estimate_rows.append({
            "method": "augmented_scm_with_sensitivity_donors", "role": "sensitivity",
            "pre_rmspe_index_points": scm.rmspe(sens_fits["augmented_scm"].gap_z[pre]) * sens_sd,
            "holdout_rmspe_index_points": None,
            **_estimands(gap, exposure, windows, event_weeks),
        })
    estimates = pd.DataFrame(estimate_rows)
    primary = estimates.iloc[0]

    # In-space placebos for the primary method: every base donor as pseudo-treated.
    placebo_rows = []
    ratio = lambda fit: scm.rmspe(fit.gap_z[post_window]) / scm.rmspe(fit.gap_z[pre])  # noqa: E731
    treated_ratio = ratio(fits["augmented_scm"])
    for position, name in enumerate(base):
        others = [index for index in range(len(base)) if index != position]
        p_fits, _, _, p_sd = _fit_methods(donors[:, position], donors[:, others], pre, post_window, config)
        p_gap = pd.Series(p_fits["augmented_scm"].gap_z * p_sd, index=weeks)
        p_values = _estimands(p_gap, exposure, windows, event_weeks)
        placebo_rows.append({
            "placebo_unit": name,
            "pre_rmspe_z": scm.rmspe(p_fits["augmented_scm"].gap_z[pre]),
            "post_rmspe_z": scm.rmspe(p_fits["augmented_scm"].gap_z[post_window]),
            "post_pre_rmspe_ratio": scm.rmspe(p_fits["augmented_scm"].gap_z[post_window])
            / scm.rmspe(p_fits["augmented_scm"].gap_z[pre]),
            "primary_estimand_pseudo_effect_pre_sd_units": (
                p_values["primary_exposure_weighted_gap"] / p_sd
                if p_values["primary_exposure_weighted_gap"] is not None else None
            ),
            "factor_model_post_pre_rmspe_ratio": (
                ratio(p_fits["generalized_scm_factor"]) if "generalized_scm_factor" in p_fits else None
            ),
        })
    placebos = pd.DataFrame(placebo_rows)
    placebo_p = (1 + int((placebos["post_pre_rmspe_ratio"] >= treated_ratio).sum())) / (1 + len(placebos))
    factor_placebo = None
    if "generalized_scm_factor" in fits:
        factor_ratio = ratio(fits["generalized_scm_factor"])
        factor_placebo = {
            "post_pre_rmspe_ratio": factor_ratio,
            "p_value": (1 + int((placebos["factor_model_post_pre_rmspe_ratio"] >= factor_ratio).sum()))
            / (1 + len(placebos)),
            "factor_count": fits["generalized_scm_factor"].details["factor_count"],
        }
    primary_value = primary["primary_exposure_weighted_gap"]
    pseudo = placebos["primary_estimand_pseudo_effect_pre_sd_units"].dropna().abs() * y_sd
    half_width = float(np.quantile(pseudo, 0.90)) if len(pseudo) else None
    estimand_p = (
        (1 + int((pseudo >= abs(primary_value)).sum())) / (1 + len(pseudo))
        if primary_value is not None and len(pseudo) else None
    )

    # In-time placebo: same window length, before any FIFA treatment.
    time_rows = []
    window_weeks = int(post_window.sum())
    for value in config["estimation"].get("time_placebo_weeks", []):
        fake = _week_start(value)
        fake_pre = np.asarray(weeks < fake)
        fake_post = np.asarray((weeks >= fake) & (weeks < fake + pd.Timedelta(weeks=max(window_weeks, 1))))
        if fake_pre.sum() <= int(config["estimation"]["ascm"]["inner_validation_weeks"]) + 26:
            continue
        t_fits, _, _, t_sd = _fit_methods(target, donors, fake_pre, fake_post, config)
        gap = t_fits["augmented_scm"].gap_z
        time_rows.append({
            "fake_treatment_week": fake.date().isoformat(),
            "window_weeks": int(fake_post.sum()),
            "mean_gap_index_points": float(gap[fake_post].mean() * t_sd),
            "post_pre_rmspe_ratio": scm.rmspe(gap[fake_post]) / scm.rmspe(gap[fake_pre]),
        })

    confounders = _confounder_diagnostics(
        pd.Series(fits["augmented_scm"].gap_z * y_sd, index=weeks), target, donors, base,
        fits["augmented_scm"].weights, y_sd, pre, windows["exposure_window"], treatment, config,
    )
    (target_dir / "confounder_diagnostics.json").write_text(
        json.dumps(confounders, indent=2, default=str) + "\n", encoding="utf-8"
    )

    # Media-value intensity weighting (ADR-0028) where it covers the window.
    mv_spec = config["estimation"].get("media_value_intensity_sensitivity")
    media = {"status": "not_configured"}
    if mv_spec:
        intensity = _media_value_intensity(mv_spec)["media_intensity_adstock_share"]
        weights = intensity.reindex(weeks)
        covered = windows["exposure_window"] & weights.notna() & (weights > 0)
        if covered.any():
            gap = pd.Series(fits["augmented_scm"].gap_z * y_sd, index=weeks)
            media = {"status": "computed", "covered_window_weeks": int(covered.sum()),
                     "media_weighted_gap": float(np.average(gap[covered], weights=weights[covered]))}
        else:
            media = {"status": "waiting_for_media_value_coverage_of_window",
                     "media_value_covers_through": str(intensity.index.max().date()),
                     "window_start": str(treatment.date())}

    # Co-brand search: descriptive level change, not a counterfactual.
    cobrand = {"status": "unavailable"}
    trends_path = Path("data/curated/trends/trends_weekly_averaged.parquet")
    if trends_path.exists():
        trends = pd.read_parquet(trends_path)
        series = trends[trends["query_id"].eq(config["estimation"]["cobrand_query"])].copy()
        series["week"] = _monday(series["week"])
        series = series.set_index("week")["interest_mean"]
        baseline = series[(series.index < treatment)].tail(int(config["estimation"]["cobrand_baseline_weeks"]))
        during = series[(series.index >= treatment) & (series.index <= final_week)]
        cobrand = {
            "status": "descriptive_level_change_not_counterfactual",
            "query_id": config["estimation"]["cobrand_query"],
            "baseline_mean": float(baseline.mean()) if len(baseline) else None,
            "tournament_mean": float(during.mean()) if len(during) else None,
            "tournament_weeks": int(len(during)),
        }

    index_through = weeks.max() + pd.Timedelta(days=6)
    vintages = _vintages(config)
    persistence_weeks = int(windows["persistence"].sum())
    gates = [
        {"gate": "activation_start_approved", "passed": approved_activation is not None,
         "detail": str(approved_activation) if approved_activation else
         f"provisional treatment week {treatment.date()} (tournament start week)"},
        {"gate": "brand_index_covers_window", "passed": bool(index_through >= pd.Timestamp(milestones["primary_post_window_end"])),
         "detail": f"index through {index_through.date()}, window ends {milestones['primary_post_window_end']}"},
        {"gate": "exposure_covers_window", "passed": bool(exposure_through >= pd.Timestamp(milestones["primary_post_window_end"])),
         "detail": f"Blinkfire through {exposure_through.date()}"},
        {"gate": "outcome_and_donor_vintages_aligned", "passed": bool(vintages["aligned"]),
         "detail": f"pulls {vintages['max_gap_days']:.1f} days apart"},
        {"gate": "minimum_pre_weeks", "passed": int(pre.sum()) >= int(rules["minimum_pre_weeks"]),
         "detail": f"{int(pre.sum())} pre weeks"},
        {"gate": "minimum_credible_donors", "passed": len(base) >= int(rules["minimum_credible_donors"]),
         "detail": f"{len(base)} base donors"},
        {"gate": "minimum_post_weeks_after_tournament",
         "passed": persistence_weeks >= int(rules["minimum_post_weeks_after_tournament"]),
         "detail": f"{persistence_weeks} observed post-tournament weeks"},
        {"gate": "placebo_p_value", "passed": placebo_p <= float(rules["maximum_placebo_p_value"]),
         "detail": f"p = {placebo_p:.4f} over {len(placebos)} donor placebos"},
    ]
    accepted = all(gate["passed"] for gate in gates) and primary_value is not None
    rows = []
    if accepted:
        rows.append({
            "estimate_id": "world_cup_impact_v1_primary",
            "treatment_window": f"{treatment.date()}/{milestones['primary_post_window_end']}",
            "delta_index_attrib": float(primary_value),
            "lower_bound": float(primary_value - half_width),
            "upper_bound": float(primary_value + half_width),
            "pre_rmspe": float(primary["pre_rmspe_index_points"]),
            "placebo_p_value": float(placebo_p),
            "accepted_for_valuation": True,
            "assumptions_hash": protocol_hash,
        })
    accepted_table = pa.Table.from_pylist(rows, schema=ACCEPTED_SCHEMA)
    pq.write_table(accepted_table, target_dir / "accepted_attribution.parquet")
    pacsv.write_csv(accepted_table, target_dir / "accepted_attribution.csv")

    weights = pd.DataFrame({"query_id": base})
    for name, fit in fits.items():
        if len(fit.weights) == len(base):  # the factor model carries loadings, not donor weights
            weights[f"{name}_weight"] = fit.weights
    weights["scm_weight_before_ridge"] = fits["augmented_scm"].details["scm_weights"]
    _write(estimates, target_dir, "estimates")
    _write(paths, target_dir, "weekly_paths")
    _write(placebos, target_dir, "donor_placebos")
    _write(weights, target_dir, "donor_weights")
    _write(pd.DataFrame(lambda_grid), target_dir, "ascm_lambda_selection")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": "accepted" if accepted else "interim_estimate_gates_not_met",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_hash": protocol_hash,
        "accepted_attribution_rows": len(rows),
        "treatment_week": str(treatment.date()),
        "treatment_week_status": "approved" if approved_activation else "provisional",
        "final_week": str(final_week.date()),
        "window_end_week": str(window_end.date()),
        "data_through": {"brand_index": str(index_through.date()),
                         "fifa_exposure": str(exposure_through.date())},
        "panel": {"pre_weeks": int(pre.sum()), "window_weeks_observed": int(post_window.sum()),
                  "persistence_weeks_observed": persistence_weeks,
                  "base_donors": base, "sensitivity_donors": sensitivity},
        "ascm": {"ridge_multiplier": multiplier,
                 "ridge_lambda": fits["augmented_scm"].details["ridge_lambda"],
                 "selected_at_grid_boundary": multiplier in (
                     min(config["estimation"]["ascm"]["ridge_lambda_multipliers"]),
                     max(config["estimation"]["ascm"]["ridge_lambda_multipliers"]))},
        "primary": {key: (None if pd.isna(value) else value) for key, value in primary.items()},
        "vintages": vintages,
        "provisional_trailing_weeks_excluded": int(config["estimation"].get("provisional_trailing_weeks", 0)),
        "category_shock_robust": {
            "method": "generalized_scm_factor",
            "estimates": next((row for row in estimate_rows if row["method"] == "generalized_scm_factor"), None),
            "placebo": factor_placebo,
            "status": "robustness_only_added_after_partial_outcome_never_a_valuation_input",
        },
        "placebo": {"post_pre_rmspe_ratio": treated_ratio, "p_value": placebo_p,
                    "primary_estimand_p_value": estimand_p,
                    "interval_half_width_index_points": half_width},
        "time_placebos": time_rows,
        "confounder_diagnostics": {
            "artifact": "confounder_diagnostics.json",
            "category_shock_loading": confounders["category_shock_loading"],
            "pre_trend": confounders["pre_trend"],
        },
        "media_value_intensity_sensitivity": media,
        "cobrand_search": cobrand,
        "survey_lift": {"status": "waiting_for_post_world_cup_survey"},
        "gates": gates,
        "interpretation": (
            "Incremental World Cup lift above the pre-tournament path, which already "
            "contains the 2024 partnership. Interim rows describe the data so far and "
            "are never valuation inputs."
        ),
        "caveats": [
            "Blinkfire exposure is digital/social only; broadcast is weighted only where media value covers the window (ADR-0028).",
            "Weeks without observed exposure carry no weight rather than zero exposure.",
            "Product and campaign controls enter as an event-week-excluded robustness estimand.",
            "The placebo gate ranks the two-sided post/pre RMSPE ratio, so a large negative gap can pass it; the sign is carried into delta_index_attrib unchanged.",
        ],
    }
    (target_dir / "estimate_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


def interim_world_cup_gaps(estimate_manifest_path: str, total_effect_weekly_path: str) -> dict[str, float | None]:
    """World Cup gaps for illustrative valuation cases (never accepted inputs).

    ``incremental``: the engine's primary estimate above the pre-tournament path.
    ``total_path``: the headline total-effect design's mean gap over the
    tournament weeks, i.e. against the no-sponsorship Lenovo.
    """
    manifest = json.loads(Path(estimate_manifest_path).read_text(encoding="utf-8"))
    weekly = pd.read_parquet(total_effect_weekly_path)
    weekly["week"] = pd.to_datetime(weekly["week"])
    start, end = pd.Timestamp(manifest["treatment_week"]), pd.Timestamp(manifest["final_week"])
    tournament = weekly[(weekly["week"] >= start) & (weekly["week"] <= end)]
    return {"incremental": manifest["primary"]["primary_exposure_weighted_gap"],
            "total_path": float(tournament["index_gap"].mean()) if len(tournament) else None,
            "status": manifest["status"]}


def protocol_hash(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode("utf-8")).hexdigest()
