"""Brand value from relative importance in price formation, and the sponsorship's
incremental brand value through its lift of the Brand Index (ADR-0031, ADR-0032).

Owner-selected chain:
1. Brand value (BV) = the brand's signed general-dominance share of explained
   weekly return variance x company value (the general effect of the Brand
   Index on price formation).
2. The sponsorship's sustained Index lift is converted to a percentage of brand
   salience: the Index is exactly linear in Lenovo's raw search interest, which
   has a true zero, so lift / (counterfactual level - zero-interest level) is a
   ratio-scale uplift.
3. Incremental BV = BV x salience uplift x the elasticity of brand value to
   salience (1 = proportional, an explicit assumption).
"""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from srmp.experiments.brand_financial_bridge_v1 import _sha256, _write


def _r2(y: np.ndarray, x: np.ndarray) -> float:
    if x.shape[1] == 0:
        return 0.0
    design = np.column_stack([np.ones(len(y)), x])
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coef
    return float(1.0 - residual.var() / y.var())


def group_dominance(y: np.ndarray, columns: dict[str, np.ndarray]) -> tuple[float, dict[str, float]]:
    """General dominance (Shapley-Owen R^2 shares) over regressor groups.

    Each group's weight is the average incremental R^2 it adds, first within
    every subset size of the other groups, then across sizes. Weights sum to
    the full-model R^2.
    """
    names = list(columns)
    cache: dict[frozenset, float] = {}

    def r2(subset: frozenset) -> float:
        if subset not in cache:
            blocks = [columns[name] for name in names if name in subset]
            cache[subset] = _r2(y, np.column_stack(blocks) if blocks else np.empty((len(y), 0)))
        return cache[subset]

    weights = {}
    for name in names:
        others = [other for other in names if other != name]
        by_size = []
        for size in range(len(others) + 1):
            gains = [r2(frozenset(subset) | {name}) - r2(frozenset(subset))
                     for subset in itertools.combinations(others, size)]
            by_size.append(np.mean(gains))
        weights[name] = float(np.mean(by_size))
    return r2(frozenset(names)), weights


def _matrices(frame: pd.DataFrame, groups: dict[str, list[str]]) -> dict[str, np.ndarray]:
    return {name: frame[cols].to_numpy(dtype=float) for name, cols in groups.items()
            if frame[cols].to_numpy(dtype=float).std(axis=0).max() > 0}


def _signs(frame: pd.DataFrame, outcome: str, groups: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    """Full-model coefficient, HC1 robust SE and sign for every single-column group.

    Dominance weights are sign-blind; a contribution only counts as value with
    the sign of its coefficient (ADR-0031).
    """
    names = [column for cols in groups.values() for column in cols]
    design = np.column_stack([np.ones(len(frame)), frame[names].to_numpy(dtype=float)])
    y = frame[outcome].to_numpy(dtype=float)
    coef = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coef
    bread = np.linalg.pinv(design.T @ design)
    n, k = design.shape
    covariance = bread @ (design.T * residual ** 2) @ design @ bread * n / (n - k)
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    position = {name: index + 1 for index, name in enumerate(names)}
    return {group: {"coefficient": float(coef[position[cols[0]]]), "robust_se": float(se[position[cols[0]]]),
                    "sign": float(np.sign(coef[position[cols[0]]]))}
            for group, cols in groups.items() if len(cols) == 1}


def _shares(frame: pd.DataFrame, outcome: str, groups: dict[str, list[str]]) -> dict[str, Any]:
    columns = _matrices(frame, groups)
    total, weights = group_dominance(frame[outcome].to_numpy(dtype=float), columns)
    explained = {k: v / total if total > 0 else 0.0 for k, v in weights.items()}
    signs = _signs(frame, outcome, {name: cols for name, cols in groups.items() if name in columns})
    signed = {k: explained[k] * signs[k]["sign"] for k in signs}
    return {"r2": total, "weights": weights, "explained_share": explained,
            "signed_explained_share": signed, "total_share": weights, "coefficients": signs}


def _block_bootstrap(
    frame: pd.DataFrame, outcome: str, groups: dict[str, list[str]], spec: dict[str, Any], keys: list[str],
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(int(spec["seed"]))
    n, block = len(frame), int(spec["block_weeks"])
    draws: dict[str, list[float]] = {f"{key}_{kind}": [] for key in keys for kind in ("explained", "total")}
    for _ in range(int(spec["replications"])):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        rows = np.concatenate([np.arange(start, start + block) for start in starts])[:n]
        result = _shares(frame.iloc[rows].reset_index(drop=True), outcome, groups)
        for key in keys:
            draws[f"{key}_explained"].append(result["signed_explained_share"].get(key, 0.0))
            draws[f"{key}_total"].append(result["total_share"].get(key, 0.0)
                                         * np.sign(result["signed_explained_share"].get(key, 0.0)))
    return {name: {"p05": float(np.quantile(values, 0.05)), "p50": float(np.quantile(values, 0.50)),
                   "p95": float(np.quantile(values, 0.95))} for name, values in draws.items()}


def _salience_map(index_path: str, trends_path: str, query: str) -> dict[str, float]:
    """Exact affine map from raw search interest to Index points."""
    index = pd.read_parquet(index_path)[["week", "index_level"]]
    index["week"] = pd.to_datetime(index["week"])
    trends = pd.read_parquet(trends_path)
    trends = trends[trends["query_id"].eq(query)].copy()
    trends["week"] = pd.to_datetime(trends["week"]) + pd.Timedelta(days=1)  # W-SUN to W-MON
    joined = index.merge(trends[["week", "interest_mean"]], on="week")
    slope, intercept = np.polyfit(joined["interest_mean"], joined["index_level"], 1)
    correlation = float(np.corrcoef(joined["interest_mean"], joined["index_level"])[0, 1])
    if correlation < 0.999:
        raise ValueError("Brand Index is no longer an affine map of the headline query; salience map invalid.")
    return {"index_points_per_interest_unit": float(slope),
            "zero_interest_index_level": float(intercept), "correlation": correlation}


def build_brand_value_dominance(
    config_path: str = "config/experiments/brand_value_dominance_v1.yaml",
) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs, groups, outcome = config["inputs"], config["groups"], config["outcome"]
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    weekly = pd.read_parquet(inputs["stock_response_weekly"])
    weekly["week"] = pd.to_datetime(weekly["week"])
    daily = pd.read_parquet(inputs["rolling_abnormal_returns_daily"])
    daily["week"] = pd.to_datetime(daily["week"])
    factors = daily.groupby("week")[["hsi_log_return", "ndx_hkd_lagged_log_return"]].sum()
    panel = weekly.drop(columns=["lenovo_log_return"], errors="ignore").merge(
        daily.groupby("week")["lenovo_log_return"].sum().rename("lenovo_log_return"), on="week"
    ).merge(factors, on="week")
    needed = [outcome] + [column for cols in groups.values() for column in cols]
    panel = panel.dropna(subset=needed).sort_values("week").reset_index(drop=True)

    # 1. Brand share of price formation, full sample.
    brand = _shares(panel, outcome, groups)
    boot_brand = _block_bootstrap(panel, outcome, groups, config["bootstrap"], ["brand"])

    # 2. Values.
    v3 = json.loads(Path(inputs["total_return_v3_manifest"]).read_text(encoding="utf-8"))
    caps = v3["market_cap_usd_m"]
    cap = float(caps[config["valuation_base"]["primary"]])
    level = float(v3["primary_result"]["sustained_gap_index_points"])
    world_cup = json.loads(Path(inputs["world_cup_estimate_manifest"]).read_text(encoding="utf-8"))
    world_cup_gap = world_cup["primary"]["primary_exposure_weighted_gap"]

    def money(share: float, base: float = cap) -> float:
        return share * base

    x = brand["signed_explained_share"]["brand"]

    # Indirect chain: Index lift -> % brand salience -> incremental brand value.
    chain = config["indirect_chain"]
    salience = _salience_map(inputs["brand_index_weekly"], inputs["trends_weekly_averaged"], chain["index_query"])
    counterfactual = pd.read_parquet(inputs["total_effect_weekly"])
    post_cf = counterfactual[counterfactual["period"].eq("post")].sort_values("week")
    trailing = int(chain["provisional_trailing_weeks"])
    post_cf = post_cf.iloc[:-trailing] if trailing else post_cf
    counterfactual_level = float(post_cf["synthetic_index"].mean())
    headroom = counterfactual_level - salience["zero_interest_index_level"]
    elasticity = float(chain["brand_value_elasticity_to_salience"])
    brand_value = money(x)
    uplift = level / headroom
    coefficient = elasticity * brand_value / headroom
    donor_levels = pd.read_parquet(inputs["donor_sensitivity"])["post_mean_gap"]
    bv_low, bv_high = money(boot_brand["brand_explained"]["p05"]), money(boot_brand["brand_explained"]["p95"])
    indirect = {
        "brand_value_usd_m": brand_value,
        "zero_interest_index_level": salience["zero_interest_index_level"],
        "index_points_per_search_interest_unit": salience["index_points_per_interest_unit"],
        "counterfactual_index_level": counterfactual_level,
        "counterfactual_search_interest": headroom / salience["index_points_per_interest_unit"],
        "sustained_lift_index_points": level,
        "salience_uplift_pct": 100 * uplift,
        "brand_value_elasticity_to_salience": elasticity,
        "incremental_brand_value_usd_m": elasticity * uplift * brand_value,
        "incremental_brand_value_90pct_usd_m": [elasticity * uplift * bv_low, elasticity * uplift * bv_high],
        "incremental_brand_value_donor_range_usd_m": [
            coefficient * float(donor_levels.min()), coefficient * float(donor_levels.max())],
        "coefficient_usd_m_per_index_point": coefficient,
        "coefficient_90pct_usd_m_per_point": [elasticity * bv_low / headroom, elasticity * bv_high / headroom],
        "world_cup_incremental_lift_index_points": world_cup_gap,
        "world_cup_incremental_brand_value_usd_m": (
            coefficient * world_cup_gap if world_cup_gap is not None else None),
        "incremental_brand_value_by_cap_base_usd_m": {
            name: elasticity * uplift * money(x, float(value)) for name, value in caps.items()},
    }
    values = {
        "brand_share_of_price_formation": x,
        "brand_share_of_total_variance": brand["total_share"]["brand"] * np.sign(x),
        "brand_value_usd_m": money(x),
        "brand_value_lower_bound_usd_m": money(brand["total_share"]["brand"] * np.sign(x)),
        "brand_value_90pct_usd_m": [money(boot_brand["brand_explained"]["p05"]),
                                    money(boot_brand["brand_explained"]["p95"])],
        "market_cap_base": config["valuation_base"]["primary"],
        "market_cap_usd_m": cap,
        "brand_value_by_cap_base_usd_m": {name: money(x, float(value)) for name, value in caps.items()},
    }

    # 3. Stability: sample windows, leaving one control group out, alternative brand measures.
    stability = []
    for start, end in config["stability"]["sample_windows"]:
        sample = panel[(panel["week"] >= pd.Timestamp(start)) & (panel["week"] <= pd.Timestamp(end))]
        result = _shares(sample, outcome, groups)
        stability.append({"check": f"sample {start} to {end}", "weeks": len(sample), "r2": result["r2"],
                          "brand_share_of_explained": result["signed_explained_share"].get("brand", 0.0),
                          "brand_value_usd_m": money(result["signed_explained_share"].get("brand", 0.0))})
    for dropped in [name for name in groups if name != "brand"]:
        reduced = {name: cols for name, cols in groups.items() if name != dropped}
        result = _shares(panel, outcome, reduced)
        stability.append({"check": f"without {dropped}", "weeks": len(panel), "r2": result["r2"],
                          "brand_share_of_explained": result["signed_explained_share"]["brand"],
                          "brand_value_usd_m": money(result["signed_explained_share"]["brand"])})
    for alternative in config["stability"].get("brand_measures", []):
        alt_groups = {**groups, "brand": [alternative]}
        sample = panel.dropna(subset=[alternative])
        result = _shares(sample, outcome, alt_groups)
        stability.append({"check": f"brand measured as {alternative}", "weeks": len(sample), "r2": result["r2"],
                          "brand_share_of_explained": result["signed_explained_share"]["brand"],
                          "brand_value_usd_m": money(result["signed_explained_share"]["brand"])})
    stability = pd.DataFrame(stability)
    stability["incremental_brand_value_usd_m"] = (
        stability["brand_value_usd_m"] * elasticity * uplift)
    shares = stability["brand_share_of_explained"]

    weights = pd.DataFrame([
        {"model": "brand_full_sample", "group": name, "dominance_r2": value,
         "share_of_explained": brand["explained_share"][name],
         "signed_share_of_explained": brand["signed_explained_share"].get(name)}
        for name, value in brand["weights"].items()
    ])
    _write(weights, target, "dominance_weights")
    _write(stability, target, "stability")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": ("brand value = signed group general-dominance share of weekly Lenovo returns x company value; "
                   "incremental brand value = brand value x sponsorship salience uplift x elasticity"),
        "decision": "ADR-0031, ADR-0032 (owner-selected; variance share read as value share and value proportional to salience by assumption)",
        "accepted_for_accounting_or_causal_claim": False,
        "coefficients": {"brand_full_sample": brand["coefficients"]},
        "samples": {"brand_weeks": len(panel), "brand_model_r2": brand["r2"]},
        "primary_result": indirect,
        "salience_map": salience,
        "values": values,
        "bootstrap": {"spec": config["bootstrap"], "brand": boot_brand},
        "stability_summary": {
            "brand_share_min": float(shares.min()), "brand_share_max": float(shares.max()),
            "brand_value_min_usd_m": money(float(shares.min())),
            "brand_value_max_usd_m": money(float(shares.max())),
            "incremental_brand_value_min_usd_m": money(float(shares.min())) * elasticity * uplift,
            "incremental_brand_value_max_usd_m": money(float(shares.max())) * elasticity * uplift,
        },
        "caveats": [
            "A share of explained return variance is not a share of value: a stable brand explains little variance yet can be worth much.",
            "Dominance weights are sign-blind; shares are signed by the full-model coefficient so value-destroying co-movement is not counted as value.",
            "Brand value is assumed proportional to search salience (elasticity 1) unless configured otherwise.",
            "The salience uplift is the synthetic-control lift, whose attribution is not yet accepted.",
            "The share depends on which other regressor groups are included; see stability.",
            "The model explains a minority of weekly return variance, so the explained-share base is small and noisy.",
            "Values scale with the market-capitalisation base; the primary base is fixed by rule (mean post-announcement).",
        ],
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
    }
    (target / "brand_value_dominance_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/brand_value_dominance_v1.yaml")
    args = parser.parse_args()
    build_brand_value_dominance(args.config)
