"""Experimental synthetic-control estimate of sponsorship-associated Index change."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import yaml
from scipy.optimize import minimize

from srmp.exposure.adstock import geometric_adstock


def _load(path: str) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Experimental SCM input unavailable: {source}")
    return pq.read_table(source).to_pandas()


def _write(frame: pd.DataFrame, stem: Path) -> None:
    table = __import__("pyarrow").Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, stem.with_suffix(".parquet"))
    pacsv.write_csv(table, stem.with_suffix(".csv"))


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _monday(values: pd.Series) -> pd.Series:
    values = pd.to_datetime(values)
    return values + pd.to_timedelta((7 - values.dt.weekday) % 7, unit="D")


def _fit_simplex(
    target: pd.Series,
    donors: pd.DataFrame,
    pre_mask: pd.Series,
) -> dict[str, Any]:
    """Fit non-negative sum-to-one weights with all scaling frozen pre-treatment."""
    target = target.astype(float)
    donors = donors.astype(float)
    y_mean, y_sd = float(target[pre_mask].mean()), float(target[pre_mask].std(ddof=0))
    x_mean, x_sd = donors.loc[pre_mask].mean(), donors.loc[pre_mask].std(ddof=0)
    if y_sd <= 0 or (x_sd <= 0).any():
        raise ValueError("Experimental SCM has a zero-variance pre-treatment series.")
    y = (target - y_mean) / y_sd
    x = (donors - x_mean) / x_sd
    n = len(donors.columns)

    def objective(weights: np.ndarray) -> float:
        residual = y[pre_mask].to_numpy() - x.loc[pre_mask].to_numpy() @ weights
        return float(residual @ residual)

    starts = [np.repeat(1.0 / n, n)]
    starts.extend(np.eye(n))
    candidates = []
    for start in starts:
        result = minimize(
            objective,
            x0=start,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * n,
            constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1.0},
            options={"ftol": 1e-12, "maxiter": 2000},
        )
        weights = np.asarray(result.x, dtype=float)
        feasible = (
            np.isfinite(weights).all()
            and abs(float(weights.sum()) - 1.0) <= 1e-7
            and float(weights.min()) >= -1e-8
            and float(weights.max()) <= 1.0 + 1e-8
        )
        if feasible:
            candidates.append((objective(weights), weights, result))
    if not candidates:
        raise ValueError("Experimental SCM optimization failed to find a feasible simplex solution.")
    _, selected_weights, _ = min(candidates, key=lambda value: value[0])
    selected_weights = np.clip(selected_weights, 0.0, 1.0)
    selected_weights /= selected_weights.sum()
    synthetic = pd.Series(x.to_numpy() @ selected_weights, index=target.index)
    return {
        "target_z": y,
        "synthetic_z": synthetic,
        "weights": {
            name: float(weight) for name, weight in zip(donors.columns, selected_weights)
        },
    }


def _rmspe(values: pd.Series) -> float:
    return float(np.sqrt(np.mean(np.square(values.astype(float)))))


def _aggregate_exposure_controls(
    exposure: pd.DataFrame,
    taxonomy: pd.DataFrame,
    treatment_group: str,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Aggregate Blinkfire after donor fitting: FIFA treatment versus other sponsorship."""
    known = set(taxonomy["property_id"])
    observed = set(exposure["property_id"])
    unknown = observed - known
    if unknown:
        raise ValueError(f"Exposure properties absent from taxonomy: {sorted(unknown)}")
    fifa_ids = sorted(
        taxonomy.loc[taxonomy["property_group"].eq(treatment_group), "property_id"]
    )
    nonfifa_ids = sorted(observed - set(fifa_ids))
    if not fifa_ids or not nonfifa_ids:
        raise ValueError("Both FIFA and non-FIFA exposure controls are required.")

    def aggregate(ids: list[str], prefix: str) -> pd.DataFrame:
        selected = exposure[exposure["property_id"].isin(ids)]
        return selected.groupby("week", as_index=True).agg(
            **{
                f"{prefix}_impressions": ("impressions", "sum"),
                f"{prefix}_views": ("views", "sum"),
                f"{prefix}_adstock": ("adstock_impressions", "sum"),
                f"{prefix}_property_rows": ("property_id", "size"),
            }
        )

    controls = aggregate(fifa_ids, "fifa").join(
        aggregate(nonfifa_ids, "nonfifa"), how="outer"
    ).fillna(0.0)
    denominator = controls["fifa_adstock"] + controls["nonfifa_adstock"]
    controls["fifa_share_of_adstock"] = np.where(
        denominator > 0, controls["fifa_adstock"] / denominator, np.nan
    )
    return controls, {"fifa": fifa_ids, "nonfifa": nonfifa_ids}


def _weekly_event_controls(events: pd.DataFrame, carryover_weeks: int) -> pd.DataFrame:
    events = events.copy()
    events["event_timestamp_utc"] = pd.to_datetime(events["event_timestamp_utc"], utc=True)
    event_date = events["event_timestamp_utc"].dt.tz_convert(None).dt.normalize()
    events["week"] = event_date - pd.to_timedelta(event_date.dt.weekday, unit="D")
    rows: list[dict[str, Any]] = []
    for row in events.to_dict("records"):
        if row["event_type"] == "promotion_calendar_proxy":
            control = "promotion_calendar_control"
        elif row["event_scope"] == "mixed_sponsorship_and_nonsponsorship":
            control = "mixed_event_control"
        else:
            control = "product_campaign_control"
        for offset in range(int(carryover_weeks) + 1):
            rows.append({"week": row["week"] + pd.Timedelta(weeks=offset), control: 1.0})
    long = pd.DataFrame(rows).melt(id_vars="week", var_name="control", value_name="value").dropna()
    weekly = long.pivot_table(index="week", columns="control", values="value", aggfunc="max", fill_value=0.0)
    for column in ("product_campaign_control", "promotion_calendar_control", "mixed_event_control"):
        if column not in weekly:
            weekly[column] = 0.0
    return weekly[["product_campaign_control", "promotion_calendar_control", "mixed_event_control"]]


def _prepare(
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, list[str]],
    pd.DataFrame, pd.DataFrame, pd.DataFrame,
]:
    trends = _load(config["inputs"]["joint_donor_trends"])
    index = _load(config["inputs"]["brand_index"])
    exposure = _load(config["inputs"]["adstock_exposure"])
    taxonomy = pd.read_csv(config["inputs"]["property_taxonomy"])
    registry = pd.read_csv(config["inputs"]["donor_registry"])
    events = pd.read_csv(config["inputs"]["product_campaign_events"])
    trends["week"] = _monday(trends["week"])
    index["week"] = pd.to_datetime(index["week"])
    exposure["week"] = pd.to_datetime(exposure["week"])
    query_ids = config["donors"]["base"] + config["donors"].get("sensitivity_only", [])
    registered = set(registry.loc[registry["query_id"].notna(), "query_id"])
    missing_registry = set(query_ids) - registered
    if missing_registry:
        raise ValueError(f"SCM donors absent from donor registry: {sorted(missing_registry)}")
    policies = registry.set_index("query_id")["inclusion_policy"].to_dict()
    invalid_base = [query for query in config["donors"]["base"] if policies.get(query) != "base"]
    if invalid_base:
        raise ValueError(f"SCM base donors fail registry eligibility: {invalid_base}")
    donor_quality = trends[~trends["query_id"].eq("anchor_lenovo")].groupby(
        ["query_id", "brand_id"], as_index=False
    ).agg(
        weeks=("week", "nunique"),
        mean_common_scale=("interest_common_scale", "mean"),
        sd_common_scale=("interest_common_scale", "std"),
        zero_share=("interest_common_scale", lambda values: float((values == 0).mean())),
        minimum_draws=("draws_used", "min"),
    ).merge(
        registry[["query_id", "inclusion_policy", "fifa_treatment_status"]],
        on="query_id", how="left",
    )
    donor = trends[trends["query_id"].isin(query_ids)].pivot(
        index="week", columns="query_id", values="interest_common_scale"
    )
    index = index.set_index("week").sort_index()
    donor = donor.reindex(index.index)
    missing = donor[query_ids].isna().sum()
    if (missing > 0).any():
        raise ValueError(f"Experimental SCM donor panel has missing weeks: {missing[missing > 0].to_dict()}")
    controls, property_sets = _aggregate_exposure_controls(
        exposure, taxonomy, config["exposure"]["treatment_property_group"]
    )
    event_controls = _weekly_event_controls(events, int(config["event_controls"]["carryover_weeks"]))
    return index, donor, controls, property_sets, registry, event_controls, donor_quality


def _donor_placebos(
    donor: pd.DataFrame,
    pre_mask: pd.Series,
    post_mask: pd.Series,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for treated in donor.columns:
        controls = donor.drop(columns=treated)
        fit = _fit_simplex(donor[treated], controls, pre_mask)
        gap = fit["target_z"] - fit["synthetic_z"]
        pre, post = _rmspe(gap[pre_mask]), _rmspe(gap[post_mask])
        rows.append({
            "placebo_unit": treated,
            "pre_rmspe_z": pre,
            "post_rmspe_z": post,
            "post_pre_rmspe_ratio": post / pre if pre > 0 else np.nan,
        })
    return pd.DataFrame(rows).sort_values("post_pre_rmspe_ratio", ascending=False)


def _time_placebos(
    target: pd.Series,
    donor: pd.DataFrame,
    dates: list[str],
    evaluation_weeks: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for value in dates:
        start = pd.Timestamp(value)
        pre = pd.Series(target.index < start, index=target.index)
        end = start + pd.Timedelta(weeks=evaluation_weeks - 1)
        post = pd.Series(target.index.to_series().between(start, end).to_numpy(), index=target.index)
        fit = _fit_simplex(target, donor, pre)
        gap = fit["target_z"] - fit["synthetic_z"]
        pre_rmspe, post_rmspe = _rmspe(gap[pre]), _rmspe(gap[post])
        rows.append({
            "fake_treatment_week": start,
            "evaluation_end": end,
            "pre_rmspe_z": pre_rmspe,
            "post_rmspe_z": post_rmspe,
            "post_pre_rmspe_ratio": post_rmspe / pre_rmspe,
            "mean_gap_z": float(gap[post].mean()),
        })
    return pd.DataFrame(rows)


def _exposure_weighted_gap(
    gap: pd.Series, exposure_controls: pd.DataFrame, start: pd.Timestamp
) -> float:
    paired = pd.DataFrame({"gap": gap}).join(
        exposure_controls[["fifa_adstock"]], how="inner"
    ).dropna(subset=["gap", "fifa_adstock"])
    paired = paired[paired.index >= start]
    total = float(paired["fifa_adstock"].sum())
    if total <= 0:
        raise ValueError("Experimental SCM has no positive FIFA adstock after treatment.")
    return float((paired["gap"] * paired["fifa_adstock"]).sum() / total)


def _exposure_control_regression(
    gap: pd.Series,
    exposure_controls: pd.DataFrame,
    event_controls: pd.DataFrame,
    hac_lags: int,
) -> dict[str, Any]:
    """Descriptive partial association, with Newey-West uncertainty.

    This is intentionally downstream of the synthetic-control fit. It checks
    whether the gap times with FIFA exposure after partialling non-FIFA Lenovo
    sponsorship exposure and a linear trend; it does not identify causality.
    """
    frame = pd.DataFrame({"index_gap": gap}).join(exposure_controls, how="inner")
    frame = frame.join(event_controls, how="left")
    event_names = ["product_campaign_control", "promotion_calendar_control", "mixed_event_control"]
    frame[event_names] = frame[event_names].fillna(0.0)
    frame = frame.dropna()
    raw = np.column_stack([
        np.log1p(frame["fifa_adstock"].to_numpy(dtype=float)),
        np.log1p(frame["nonfifa_adstock"].to_numpy(dtype=float)),
        np.arange(len(frame), dtype=float),
    ])
    means = raw.mean(axis=0)
    sds = raw.std(axis=0, ddof=0)
    if (sds <= 0).any():
        raise ValueError("Exposure-control regression contains a zero-variance regressor.")
    z = (raw - means) / sds
    event_matrix = frame[event_names].to_numpy(dtype=float)
    active_events = [index for index in range(len(event_names)) if event_matrix[:, index].std() > 0]
    event_matrix = event_matrix[:, active_events]
    active_event_names = [event_names[index] for index in active_events]
    x = np.column_stack([np.ones(len(frame)), z, event_matrix])
    y = frame["index_gap"].to_numpy(dtype=float)
    beta = np.linalg.pinv(x.T @ x) @ x.T @ y
    residual = y - x @ beta
    xu = x * residual[:, None]
    meat = xu.T @ xu
    max_lag = min(int(hac_lags), len(frame) - 1)
    for lag in range(1, max_lag + 1):
        weight = 1.0 - lag / (max_lag + 1.0)
        gamma = xu[lag:].T @ xu[:-lag]
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.pinv(x.T @ x)
    covariance = bread @ meat @ bread
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    total = float(np.square(y - y.mean()).sum())
    r_squared = 1.0 - float(np.square(residual).sum()) / total if total > 0 else np.nan
    names = [
        "intercept", "fifa_log_adstock_z", "nonfifa_log_adstock_z", "linear_time_z",
        *active_event_names,
    ]
    return {
        "status": "descriptive_association_not_causal",
        "sample_start": frame.index.min().date().isoformat(),
        "sample_end": frame.index.max().date().isoformat(),
        "observations": len(frame),
        "hac_lags": max_lag,
        "r_squared": r_squared,
        "coefficients": {
            name: {"estimate_index_points": float(value), "hac_se": float(error)}
            for name, value, error in zip(names, beta, se)
        },
        "regressor_definition": {
            "fifa_log_adstock_z": "standardized log1p aggregate FIFA-property adstock",
            "nonfifa_log_adstock_z": "standardized log1p aggregate all other Lenovo sponsorship adstock",
            "product_campaign_control": "confirmed Lenovo product or corporate campaign event week plus configured carryover",
            "promotion_calendar_control": "Black Friday calendar proxy; not confirmed Lenovo media spend",
            "mixed_event_control": "event week containing both FIFA activation and major non-sponsorship Lenovo news",
        },
        "interpretation": "Timing diagnostic only; exposure is endogenous and coverage starts shortly before treatment.",
    }


def _media_value_intensity(spec: dict[str, Any]) -> pd.DataFrame:
    """Weekly relative exposure intensity from media value (ADR-0028).

    Media value proxies audience x on-screen time x visibility quality x market
    rate, so it carries broadcast exposure that Blinkfire omits. Only its
    within-sample shape is used: adstock is rescaled to sum to one, so no
    monetary amount leaves this function.
    """
    daily = _load(spec["path"])
    measure = spec["measure"]
    if not bool(daily["banned_as_feature"].all()):
        raise ValueError("Media value rows must carry the monetary-use ban flag.")
    daily["week"] = pd.to_datetime(daily["week"])
    weekly = daily.groupby("week")[measure].sum()
    grid = pd.date_range(weekly.index.min(), weekly.index.max(), freq="W-MON")
    weekly = weekly.reindex(grid, fill_value=0.0)
    adstock = pd.Series(
        geometric_adstock(weekly.to_numpy(dtype=float), float(spec["adstock_delta"])),
        index=grid,
    )
    return pd.DataFrame({
        "media_intensity_week_share": weekly / weekly.sum(),
        "media_intensity_adstock_share": adstock / adstock.sum(),
    }).rename_axis("week")


def _media_value_sensitivity(
    gap: pd.Series,
    post: pd.Series,
    exposure_controls: pd.DataFrame,
    event_controls: pd.DataFrame,
    spec: dict[str, Any],
    hac_lags: int,
) -> dict[str, Any]:
    """Re-weight the gap and re-run the timing check on media-value intensity."""
    intensity = _media_value_intensity(spec)
    frame = intensity.join(pd.DataFrame({"gap": gap, "post": post}), how="inner").join(
        exposure_controls[["fifa_adstock", "fifa_impressions", "nonfifa_adstock"]], how="left"
    )
    frame = frame[frame["post"].astype(bool)].dropna(subset=["gap"])
    exposure_columns = ["fifa_adstock", "fifa_impressions", "nonfifa_adstock"]
    frame[exposure_columns] = frame[exposure_columns].fillna(0.0)
    media_w = frame["media_intensity_adstock_share"]
    blink_w = frame["fifa_adstock"]
    timing_controls = pd.DataFrame({
        "fifa_adstock": frame["media_intensity_adstock_share"],
        "nonfifa_adstock": frame["nonfifa_adstock"],
    })
    timing = _exposure_control_regression(frame["gap"], timing_controls, event_controls, hac_lags)
    timing["coefficients"]["media_intensity_log_adstock_z"] = timing["coefficients"].pop(
        "fifa_log_adstock_z"
    )
    timing["regressor_definition"].pop("fifa_log_adstock_z", None)
    timing["regressor_definition"]["media_intensity_log_adstock_z"] = (
        "standardized log1p of the media-value adstock share (unitless relative intensity)"
    )
    coefficient = timing["coefficients"]["media_intensity_log_adstock_z"]["estimate_index_points"]
    return {
        "role": "sensitivity_only_relative_exposure_intensity",
        "decision": "ADR-0028",
        "source": spec["path"],
        "source_sha256": _sha256(spec["path"]),
        "measure": spec["measure"],
        "adstock_delta": float(spec["adstock_delta"]),
        "monetary_totals_used": False,
        "window_start": frame.index.min().date().isoformat(),
        "window_end": frame.index.max().date().isoformat(),
        "window_weeks": int(len(frame)),
        "weeks_with_media_value": int((frame["media_intensity_week_share"] > 0).sum()),
        "media_intensity_weighted_gap_index_points": float((frame["gap"] * media_w).sum() / media_w.sum()),
        "blinkfire_weighted_gap_same_window_index_points": (
            float((frame["gap"] * blink_w).sum() / blink_w.sum()) if blink_w.sum() > 0 else None
        ),
        "unweighted_mean_gap_same_window_index_points": float(frame["gap"].mean()),
        "weekly_correlation_with_blinkfire_fifa_impressions": {
            "pearson": float(frame["media_intensity_week_share"].corr(frame["fifa_impressions"])),
            "spearman": float(frame["media_intensity_week_share"].corr(
                frame["fifa_impressions"], method="spearman")),
        },
        "timing_regression": timing,
        "timing_coherence_support": "directionally_supported" if coefficient > 0 else "not_supported",
        "limitations": [
            "Media value covers 2025-05 to 2026-04: no 2024 announcement weeks and no 2026 Men's World Cup.",
            "Market rate cards weight audiences by local advertising prices, so this is value-weighted exposure, not unique contacts.",
            "Vendor methodology (channels, QI definition, currency) is not documented in the export.",
        ],
    }


def build_counterfactual(
    config_path: str = "config/experiments/sponsorship_counterfactual_v1.yaml",
    output_dir: str = "data/curated/experimental/sponsorship_counterfactual_v1",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    (
        index, donor_all, exposure_controls, property_sets, donor_registry,
        event_controls, donor_quality,
    ) = _prepare(config)
    base_donors = config["donors"]["base"]
    treatment = pd.Timestamp(config["treatment"]["first_full_post_week"])
    pre = pd.Series(index.index < treatment, index=index.index)
    post = pd.Series(index.index >= treatment, index=index.index)
    fit = _fit_simplex(index["proxy_z"], donor_all[base_donors], pre)

    # Convert the pre-standardized target gap into the canonical 100/15 Index
    # display scale. The relation is affine, so the intercept cancels in gaps.
    points_per_z, display_intercept = np.polyfit(
        fit["target_z"][pre], index.loc[pre, "index_level"], 1
    )
    synthetic_index = display_intercept + points_per_z * fit["synthetic_z"]
    gap = index["index_level"] - synthetic_index
    pre_rmspe, post_rmspe = _rmspe(gap[pre]), _rmspe(gap[post])
    treated_ratio = post_rmspe / pre_rmspe
    weighted_delta = _exposure_weighted_gap(gap, exposure_controls, treatment)
    exposure_regression = _exposure_control_regression(
        gap, exposure_controls, event_controls, int(config["exposure"]["hac_lags"])
    )
    media_spec = config.get("media_value_intensity")
    media_sensitivity = (
        _media_value_sensitivity(
            gap, post, exposure_controls, event_controls, media_spec,
            int(config["exposure"]["hac_lags"]),
        )
        if media_spec else None
    )
    event_any = event_controls.max(axis=1).reindex(gap.index, fill_value=0.0).gt(0)
    gap_without_event_weeks = gap.mask(event_any)
    event_excluded_delta = _exposure_weighted_gap(
        gap_without_event_weeks, exposure_controls, treatment
    )

    base_raw = donor_all[base_donors]
    placebo = _donor_placebos(base_raw, pre, post)
    placebo_p = float(
        (1 + (placebo["post_pre_rmspe_ratio"] >= treated_ratio).sum())
        / (1 + len(placebo))
    )
    time_placebo = _time_placebos(
        index["proxy_z"], base_raw, config["placebos"]["fake_treatment_weeks"],
        int(config["placebos"]["evaluation_weeks"]),
    )

    sensitivity_rows: list[dict[str, Any]] = []
    donor_sets: list[tuple[str, list[str]]] = [
        (f"leave_out_{name}", [item for item in base_donors if item != name])
        for name in base_donors
    ]
    sensitivity = config["donors"].get("sensitivity_only", [])
    if sensitivity:
        donor_sets.append(("include_sensitivity_donors", base_donors + sensitivity))
    for label, names in donor_sets:
        alternate = _fit_simplex(index["proxy_z"], donor_all[names], pre)
        alternate_gap = points_per_z * (alternate["target_z"] - alternate["synthetic_z"])
        sensitivity_rows.append({
            "specification": label,
            "donor_count": len(names),
            "post_mean_gap": float(alternate_gap[post].mean()),
            "exposure_weighted_gap": _exposure_weighted_gap(
                alternate_gap, exposure_controls, treatment
            ),
            "pre_rmspe": _rmspe(alternate_gap[pre]),
        })
    sensitivity_frame = pd.DataFrame(sensitivity_rows)

    weekly = pd.DataFrame({
        "week": index.index,
        "actual_index": index["index_level"].to_numpy(),
        "synthetic_index": synthetic_index.to_numpy(),
        "index_gap": gap.to_numpy(),
        "period": np.where(pre, "pre", "post"),
    }).merge(exposure_controls.reset_index(), on="week", how="left")
    weekly = weekly.merge(event_controls.reset_index(), on="week", how="left")
    exposure_columns = [column for column in exposure_controls.columns]
    weekly[exposure_columns] = weekly[exposure_columns].fillna(0.0)
    event_columns = list(event_controls.columns)
    weekly[event_columns] = weekly[event_columns].fillna(0.0)
    weekly["exposure_weight"] = np.where(
        weekly["week"].ge(treatment), weekly["fifa_adstock"], 0.0
    )
    if weekly["exposure_weight"].sum() > 0:
        weekly["exposure_weight"] /= weekly["exposure_weight"].sum()

    weights = pd.DataFrame({
        "query_id": list(fit["weights"]),
        "weight": list(fit["weights"].values()),
    }).sort_values("weight", ascending=False)
    windows = []
    for label, weeks in (("first_26_weeks", 26), ("first_52_weeks", 52)):
        mask = post & pd.Series(index.index < treatment + pd.Timedelta(weeks=weeks), index=index.index)
        windows.append({"window": label, "mean_index_gap": float(gap[mask].mean())})
    windows.append({"window": "all_post_weeks", "mean_index_gap": float(gap[post].mean())})
    window_frame = pd.DataFrame(windows)

    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    _write(weekly, target / "counterfactual_weekly")
    _write(weights, target / "scm_weights")
    _write(placebo, target / "donor_placebos")
    _write(time_placebo, target / "time_placebos")
    _write(sensitivity_frame, target / "donor_sensitivity")
    _write(window_frame, target / "post_window_summary")
    _write(donor_quality, target / "donor_quality_screen")
    active_registry = donor_registry[
        donor_registry["query_id"].isin(base_donors + config["donors"].get("sensitivity_only", []))
    ].copy()
    _write(active_registry, target / "donor_registry_snapshot")
    (target / "exposure_control_regression.json").write_text(
        json.dumps(exposure_regression, indent=2) + "\n", encoding="utf-8"
    )
    if media_sensitivity:
        (target / "media_value_intensity_sensitivity.json").write_text(
            json.dumps(media_sensitivity, indent=2) + "\n", encoding="utf-8"
        )

    fit_pass = pre_rmspe <= float(config["screen"]["max_pre_rmspe_index_points"])
    placebo_pass = placebo_p <= float(config["screen"]["max_placebo_p_value"])
    fifa_timing_coefficient = exposure_regression["coefficients"]["fifa_log_adstock_z"]["estimate_index_points"]
    timing_support = "directionally_supported" if fifa_timing_coefficient > 0 else "not_supported"
    status = "candidate_passes_experimental_screen" if fit_pass and placebo_pass else "candidate_not_distinguishable"
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": status,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_contracts_replaced": [],
        "treatment": config["treatment"],
        "inputs": {
            name: {"path": path, "sha256": _sha256(path)}
            for name, path in config["inputs"].items()
        },
        "base_donor_weights": {key: round(value, 8) for key, value in fit["weights"].items()},
        "counterfactual_roles": {
            "donors": "competitor-brand salience proxies screened for no known FIFA treatment",
            "blinkfire": "downstream FIFA treatment intensity and non-FIFA sponsorship timing control; excluded from donor weights",
            "property_cobrand_search": "mechanism diagnostic only; excluded from Brand Index counterfactual and valuation",
        },
        "exposure_controls": {
            "fifa_property_ids": property_sets["fifa"],
            "nonfifa_property_ids": property_sets["nonfifa"],
            "regression_artifact": "exposure_control_regression.json",
            "regression_status": exposure_regression["status"],
        },
        "event_controls": {
            "source": config["inputs"]["product_campaign_events"],
            "event_rows": int(len(pd.read_csv(config["inputs"]["product_campaign_events"]))),
            "weekly_columns": list(event_controls.columns),
            "carryover_weeks": int(config["event_controls"]["carryover_weeks"]),
            "announcement_week_is_mixed": True,
        },
        "diagnostics": {
            "pre_weeks": int(pre.sum()),
            "post_weeks": int(post.sum()),
            "pre_rmspe_index_points": pre_rmspe,
            "post_rmspe_index_points": post_rmspe,
            "post_pre_rmspe_ratio": treated_ratio,
            "donor_placebo_p_value": placebo_p,
            "pre_fit_pass": fit_pass,
            "placebo_pass": placebo_pass,
            "timing_coherence_support": timing_support,
        },
        "candidate_attribution": {
            "exposure_weighted_delta_index": weighted_delta,
            "event_week_excluded_exposure_weighted_delta_index": event_excluded_delta,
            "all_post_mean_delta_index": float(gap[post].mean()),
            "post_counterfactual_mean_index": float(synthetic_index[post].mean()),
            "policy": "candidate only; explicit methodological acceptance required before valuation",
        },
        "donor_pool": {
            "base_count": len(base_donors),
            "sensitivity_count": len(config["donors"].get("sensitivity_only", [])),
            "quality_screen_artifact": "donor_quality_screen.parquet",
            "joint_panel_path": config["inputs"]["joint_donor_trends"],
        },
        "media_value_intensity_sensitivity": (
            {key: media_sensitivity[key] for key in (
                "role", "decision", "window_start", "window_end", "window_weeks",
                "media_intensity_weighted_gap_index_points",
                "blinkfire_weighted_gap_same_window_index_points",
                "unweighted_mean_gap_same_window_index_points",
                "timing_coherence_support", "monetary_totals_used",
            )} if media_sensitivity else None
        ),
        "sensitivity_range": {
            "exposure_weighted_min": float(sensitivity_frame["exposure_weighted_gap"].min()),
            "exposure_weighted_max": float(sensitivity_frame["exposure_weighted_gap"].max()),
        },
        "known_limitations": [
            "Donor outcomes come from common-anchor Google Trends panels and are standardized using pre-treatment data for SCM fitting.",
            "Huawei and MSI are sensitivity-only because of comparability or World Cup vendor-visibility concerns.",
            "Product and campaign controls are event-week indicators, not media-spend or launch-intensity measures.",
            "Synthetic control isolates Lenovo-specific excess salience under donor assumptions; it does not prove sponsorship is the only cause.",
            "Blinkfire exposure omits broadcast, so the primary exposure-weighting covers digital/social/owned exposure only; a media-value intensity sensitivity (ADR-0028) adds broadcast-inclusive weighting for 2025-05 to 2026-04.",
            "Blinkfire coverage starts 2024-01-01 (ADR-0048); 2022-2023 non-FIFA exposure is not observed.",
            "The FIFA versus non-FIFA exposure regression is a timing diagnostic, not a causal estimator, because Lenovo chooses activation timing.",
            "Negative treatment-contamination searches are evidence-bounded and must be refreshed when FIFA announces new partners or brands launch World Cup campaigns.",
        ],
    }
    (target / "counterfactual_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/sponsorship_counterfactual_v1.yaml")
    parser.add_argument("--output-dir", default="data/curated/experimental/sponsorship_counterfactual_v1")
    args = parser.parse_args()
    build_counterfactual(args.config, args.output_dir)
