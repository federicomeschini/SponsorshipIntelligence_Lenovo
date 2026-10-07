"""Total effect of the FIFA sponsorship on the Lenovo Brand Index (ADR-0034, ADR-0038).

Headline estimand: the mean gap between Lenovo and a synthetic no-sponsorship
Lenovo over every week since the partnership announcement, World Cup included.

Phase A selects the method and donor pool by rolling-origin out-of-sample
prediction of Lenovo across the pre-announcement weeks. It receives a panel
truncated before treatment, so no post-period outcome can influence the
choice, and writes its selection record before Phase B runs. Phase B fits the
selected design once, tests it against donor placebos, writes its weekly path
and leave-one-donor-out range, and reports every other design as a
specification curve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from srmp.counterfactual import scm
from srmp.experiments.sponsorship_counterfactual_v1 import _monday
from srmp.experiments.world_cup_impact_v1_estimator import _fit_methods, _write
from srmp.index.brand_factor import donor_shares_of_search


def _load_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    inputs = config["inputs"]
    outcome = config.get("outcome_column", "index_level")
    index = pd.read_parquet(inputs["brand_index"])[["week", outcome]].rename(columns={outcome: "index_level"})
    index["week"] = pd.to_datetime(index["week"])
    trends = pd.read_parquet(inputs["jointly_scaled_donor_trends"])
    trends["week"] = _monday(trends["week"])
    registry = pd.read_csv(inputs["donor_registry"])
    base = registry.loc[registry["inclusion_policy"].eq("base"), "query_id"].tolist()
    sensitivity = registry.loc[registry["inclusion_policy"].eq("sensitivity"), "query_id"].tolist()
    candidates = registry.loc[registry["inclusion_policy"].eq("candidate_base"), "query_id"].tolist()
    donors = trends[trends["query_id"].isin(base + sensitivity + candidates)].pivot(
        index="week", columns="query_id", values="interest_common_scale")
    share = config.get("donor_share_of_search")
    if share:
        rivals = registry.loc[registry["inclusion_policy"].isin(share["denominator_policies"]), "query_id"].tolist()
        donors = donor_shares_of_search(donors, [r for r in rivals if r in donors])
    panel = index.set_index("week").join(donors, how="inner").sort_index()
    trailing = int(config["provisional_trailing_weeks"])
    if trailing:
        panel = panel.iloc[:-trailing]
    pre = panel.index < pd.Timestamp(config["treatment"]["first_full_post_week"])
    # Data-quality rule: complete and not constant before treatment.
    complete = lambda names: [n for n in names if n in panel and panel[n].notna().all()  # noqa: E731
                              and panel.loc[pre, n].std() > 0]
    return panel, {"base": complete(base), "sensitivity": complete(sensitivity),
                   "candidate_base": complete(candidates)}


def _hac_trend_t(values: np.ndarray, lags: int) -> float:
    time = np.arange(len(values), dtype=float)
    design = np.column_stack([np.ones(len(values)), (time - time.mean()) / time.std()])
    coef = np.linalg.lstsq(design, values, rcond=None)[0]
    residual = values - design @ coef
    scores = design * residual[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        weight = 1 - lag / (lags + 1)
        gamma = scores[lag:].T @ scores[:-lag]
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.inv(design.T @ design)
    return float(coef[1] / np.sqrt((bread @ meat @ bread)[1, 1]))


def _screen_rows(pre_panel: pd.DataFrame, names: list[str], spec: dict[str, Any]) -> list[dict]:
    lenovo = pre_panel["index_level"]
    lenovo_z = (lenovo - lenovo.mean()) / lenovo.std()
    rows = []
    for name in names:
        donor = pre_panel[name]
        gap = (lenovo_z - (donor - donor.mean()) / donor.std()).to_numpy()
        t = _hac_trend_t(gap, int(spec["hac_lags"]))
        rows.append({"query_id": name, "pre_gap_trend_hac_t": t, "parallel": abs(t) < float(spec["max_abs_t"])})
    return rows


def _pools(pre_panel: pd.DataFrame, groups: dict[str, list[str]], config: dict[str, Any]) -> tuple[dict[str, list[str]], list[dict]]:
    spec = config["selection"]["parallel_trend_screen"]
    lenovo = pre_panel["index_level"]
    lenovo_z = (lenovo - lenovo.mean()) / lenovo.std()
    screen = _screen_rows(pre_panel, groups["base"], spec)
    parallel = [row["query_id"] for row in screen if row["parallel"]]
    pools = {"base": groups["base"], "base_plus_sensitivity": groups["base"] + groups["sensitivity"]}
    if len(parallel) >= int(spec["minimum_donors"]):
        pools["parallel_trend_screened"] = parallel
    if config["selection"].get("include_candidate_pools") and groups.get("candidate_base"):
        pools["expanded"] = groups["base"] + groups["candidate_base"]
        pools["expanded_plus_sensitivity"] = pools["expanded"] + groups["sensitivity"]
        expanded_parallel = parallel + [row["query_id"] for row in _screen_rows(
            pre_panel, groups["candidate_base"], spec) if row["parallel"]]
        if len(expanded_parallel) >= int(spec["minimum_donors"]):
            pools["expanded_parallel_trend_screened"] = expanded_parallel
    return pools, screen


def select_design(pre_panel: pd.DataFrame, groups: dict[str, list[str]], config: dict[str, Any]) -> dict[str, Any]:
    """Phase A. ``pre_panel`` must contain only pre-treatment weeks."""
    pools, screen = _pools(pre_panel, groups, config)
    spec = config["selection"]["rolling_origin"]
    n = len(pre_panel)
    origins = list(range(int(spec["first_origin_week"]), n - 1, int(spec["step_weeks"])))
    target = pre_panel["index_level"].to_numpy(dtype=float)
    rows = []
    for pool_name, names in pools.items():
        donors = pre_panel[names].to_numpy(dtype=float)
        errors: dict[str, list[np.ndarray]] = {}
        for origin in origins:
            end = min(origin + int(spec["horizon_weeks"]), n)
            train = np.arange(end) < origin
            hold = ~train
            fits, _, _, sd = _fit_methods(target[:end], donors[:end], train, hold, config)
            for method, fit in fits.items():
                errors.setdefault(method, []).append(fit.gap_z[hold] * sd)
        for method, folds in errors.items():
            stacked = np.concatenate(folds)
            rows.append({
                "donor_pool": pool_name, "method": method, "donors": len(names), "folds": len(folds),
                "oos_rmspe_index_points": float(np.sqrt(np.mean(stacked ** 2))),
                "oos_mean_error_index_points": float(stacked.mean()),
                "worst_fold_mean_error": float(max(abs(f.mean()) for f in folds)),
            })
    table = pd.DataFrame(rows)
    order = {m: i for i, m in enumerate(config["selection"]["tie_break_order"])}
    table["tie_break"] = table["method"].map(order)
    table = table.sort_values(["oos_rmspe_index_points", "tie_break"]).reset_index(drop=True)
    chosen = table.iloc[0]
    return {"selected_method": chosen["method"], "selected_pool": chosen["donor_pool"],
            "selected_donors": pools[chosen["donor_pool"]], "pools": pools,
            "parallel_trend_screen": screen, "table": table, "origins": origins,
            "pre_period_end": str(pre_panel.index.max().date())}


def _stats(gap_z: np.ndarray, pre: np.ndarray, post: np.ndarray) -> dict[str, float]:
    pre_rmspe = scm.rmspe(gap_z[pre])
    return {"pre_rmspe_z": pre_rmspe, "rmspe_ratio": scm.rmspe(gap_z[post]) / pre_rmspe,
            "mean_gap_over_pre_rmspe": float(gap_z[post].mean()) / pre_rmspe}


def _p_value(treated: float, placebos: list[float]) -> float:
    return (1 + sum(value >= treated for value in placebos)) / (1 + len(placebos))


def build(config_path: str = "config/experiments/sponsorship_total_effect_v1.yaml",
          selection_only: bool = False) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    target_dir = Path(config["outputs"]["directory"])
    target_dir.mkdir(parents=True, exist_ok=True)
    panel, groups = _load_panel(config)
    treatment = pd.Timestamp(config["treatment"]["first_full_post_week"])

    # ---- Phase A: pre-period only --------------------------------------
    pre_panel = panel[panel.index < treatment].copy()
    selection = select_design(pre_panel, groups, config)
    selection_record = {
        "experiment_id": config["experiment_id"], "phase": "A_design_selection",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(config_file.read_bytes()).hexdigest(),
        "data_weeks_seen": [str(pre_panel.index.min().date()), selection["pre_period_end"]],
        "post_period_outcomes_accessed": False,
        "criterion": config["selection"]["criterion"],
        "selected_method": selection["selected_method"], "selected_pool": selection["selected_pool"],
        "selected_donors": selection["selected_donors"], "rolling_origins": selection["origins"],
        "parallel_trend_screen": selection["parallel_trend_screen"],
    }
    (target_dir / "selection_record.json").write_text(json.dumps(selection_record, indent=2, default=str) + "\n", encoding="utf-8")
    _write(selection["table"].drop(columns="tie_break"), target_dir, "selection_table")
    if selection_only:
        return selection_record

    # ---- Phase B: single estimate + placebos + specification curve ------
    pre = np.asarray(panel.index < treatment)
    windows = {"all_post": np.asarray(panel.index >= treatment)}
    lo, hi = (pd.Timestamp(v) for v in config["inference"]["secondary_windows"]["excluding_spring_2026_surge"])
    windows["excluding_spring_2026_surge"] = windows["all_post"] & ~np.asarray((panel.index >= lo) & (panel.index <= hi))
    cut = pd.Timestamp(config["inference"]["secondary_windows"]["before_spring_2026_surge_end"])
    windows["before_spring_2026_surge"] = windows["all_post"] & np.asarray(panel.index <= cut)
    target = panel["index_level"].to_numpy(dtype=float)
    filters = {"none": None, **config["inference"]["secondary_placebo_filters"]}

    curve, primary = [], None
    for pool_name, names in selection["pools"].items():
        donors = panel[names].to_numpy(dtype=float)
        fits, _, _, sd = _fit_methods(target, donors, pre, windows["all_post"], config)
        placebo_fits = []
        for position in range(len(names)):
            others = [k for k in range(len(names)) if k != position]
            p_fits, _, _, _ = _fit_methods(donors[:, position], donors[:, others], pre, windows["all_post"], config)
            placebo_fits.append(p_fits)
        for method, fit in fits.items():
            for window_name, post in windows.items():
                treated = _stats(fit.gap_z, pre, post)
                placebo_stats = [_stats(p[method].gap_z, pre, post) for p in placebo_fits]
                for filter_name, multiple in filters.items():
                    kept = [s for s in placebo_stats
                            if multiple is None or s["pre_rmspe_z"] <= float(multiple) * treated["pre_rmspe_z"]]
                    for statistic in ("rmspe_ratio", "mean_gap_over_pre_rmspe"):
                        row = {
                            "donor_pool": pool_name, "method": method, "window": window_name,
                            "placebo_filter": filter_name, "statistic": statistic,
                            "lift_index_points": float(fit.gap_z[post].mean() * sd),
                            "pre_rmspe_index_points": treated["pre_rmspe_z"] * sd,
                            "treated_statistic": treated[statistic], "placebos_kept": len(kept),
                            "p_value": _p_value(treated[statistic], [s[statistic] for s in kept]),
                            "selected_design": (pool_name == selection["selected_pool"]
                                                and method == selection["selected_method"]),
                        }
                        primary_spec = config["inference"]["primary"]
                        row["is_primary"] = bool(row["selected_design"] and window_name == primary_spec["window"]
                                                 and filter_name == primary_spec["placebo_filter"]
                                                 and statistic == primary_spec["statistic"])
                        curve.append(row)
                        if row["is_primary"]:
                            primary = {**row, "placebos": [
                                {"placebo_unit": names[k], **placebo_stats[k]} for k in range(len(names))]}
    curve = pd.DataFrame(curve)
    _write(curve, target_dir, "specification_curve")

    # Weekly path of the selected design and leave-one-donor-out lifts.
    names, method = selection["selected_donors"], selection["selected_method"]
    donors = panel[names].to_numpy(dtype=float)
    fits, _, _, sd = _fit_methods(target, donors, pre, windows["all_post"], config)
    gap = fits[method].gap_z * sd
    weekly = pd.DataFrame({"week": panel.index, "actual_index": target, "synthetic_index": target - gap,
                           "index_gap": gap, "period": np.where(pre, "pre", "post")})
    _write(weekly, target_dir, "total_effect_weekly")
    loo = []
    for position, name in enumerate(names):
        keep = [k for k in range(len(names)) if k != position]
        alt, _, _, alt_sd = _fit_methods(target, donors[:, keep], pre, windows["all_post"], config)
        loo.append({"specification": f"leave_out_{name}", "donor_count": len(keep),
                    "post_mean_gap": float(alt[method].gap_z[windows["all_post"]].mean() * alt_sd)})
    loo = pd.DataFrame(loo)
    _write(loo, target_dir, "donor_sensitivity")
    alpha = float(config["inference"]["significance_level"])
    selected = curve[curve["selected_design"]]
    summary = {
        "specifications": int(len(curve)),
        "share_lift_positive": float((curve.drop_duplicates(["donor_pool", "method", "window"])["lift_index_points"] > 0).mean()),
        "share_p_at_or_below_alpha": float((curve["p_value"] <= alpha).mean()),
        "selected_design_share_p_at_or_below_alpha": float((selected["p_value"] <= alpha).mean()),
        "lift_range_index_points": [float(curve["lift_index_points"].min()), float(curve["lift_index_points"].max())],
    }
    manifest = {
        "experiment_id": config["experiment_id"], "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection": {k: selection_record[k] for k in ("selected_method", "selected_pool", "selected_donors",
                                                       "post_period_outcomes_accessed", "data_weeks_seen")},
        "total_effect": {
            "lift_index_points": primary["lift_index_points"] if primary else None,
            "first_post_week": str(panel.index[~pre].min().date()),
            "last_week": str(panel.index.max().date()),
            "post_weeks": int((~pre).sum()),
            "synthetic_post_mean_index": float(weekly.loc[~pre, "synthetic_index"].mean()),
            "leave_one_donor_out_range": [float(loo["post_mean_gap"].min()), float(loo["post_mean_gap"].max())],
        },
        "primary": primary, "passes_primary_test": bool(primary and primary["p_value"] <= alpha),
        "specification_curve_summary": summary,
        "note": ("Headline total sponsorship effect. Primary inference is unchanged from sponsorship_counterfactual_v1; "
                 "the design is selected on pre-announcement evidence only."),
    }
    (target_dir / "estimate_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/sponsorship_total_effect_v1.yaml")
    parser.add_argument("--selection-only", action="store_true")
    args = parser.parse_args()
    build(args.config, selection_only=args.selection_only)
