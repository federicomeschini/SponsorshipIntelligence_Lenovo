"""Brand value from relative importance in price formation, and the sponsorship's
incremental brand value through its lift of the Brand Index (ADR-0031, ADR-0032, ADR-0040).

Owner-selected chain:
1. Brand value (BV) = the brand's signed general-dominance share of the
   Lenovo-specific explained weekly return variance (market factors set aside;
   ADR-0044) x company value. The share of all explained variance (the "literal"
   reading, ADR-0031) is kept as a secondary reference only.
2. The sponsorship's sustained Index lift is converted to a percentage uplift in
   brand share of attention. The Brand Index is a ratio scale (proportional to
   Lenovo's brand share, true zero at 0; ADR-0040), so the uplift is
   lift / counterfactual index level.
3. Incremental BV = BV x brand-share uplift x the elasticity of brand value to
   brand share (1 = proportional, an explicit assumption).

The sponsorship's primary uplift is the FIFA-specific effect (ADR-0043): the part of
the gap explained by accumulated FIFA exposure. Its 95% interval and the whole gap
(residual also credited to FIFA) are reported as bands.
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


def _lenovo_specific(result: dict[str, Any]) -> float:
    """Signed brand share of the explained variance that is not market factors (ADR-0044)."""
    weights = result["weights"]
    rest = sum(v for k, v in weights.items() if k != "market")
    sign = result["coefficients"].get("brand", {}).get("sign", 1.0)
    return float(sign * weights.get("brand", 0.0) / rest) if rest > 0 else 0.0


def _placebos(frame: pd.DataFrame, outcome: str, groups: dict[str, list[str]], spec: dict[str, Any],
              actual: float) -> dict[str, Any]:
    """What share would a meaningless 'brand' get? Random series and time-shifted brand series.

    Reported as the share an unrelated regressor obtains and the probability that it reaches
    the actual (unsigned) share; a diagnostic of how well the market data identify the brand.
    """
    column = groups["brand"][0]
    rng = np.random.default_rng(int(spec["seed"]))
    unsigned = lambda f: abs(_lenovo_specific(_shares(f, outcome, groups)))  # noqa: E731
    noise = []
    for _ in range(int(spec["noise_draws"])):
        f = frame.copy()
        f[column] = rng.normal(size=len(f))
        noise.append(unsigned(f))
    shift = []
    k0 = int(spec["minimum_shift_weeks"])
    for k in range(k0, len(frame) - k0 + 1):
        f = frame.copy()
        f[column] = np.roll(frame[column].to_numpy(), k)
        shift.append(unsigned(f))
    summary = lambda d: {"median": float(np.median(d)), "mean": float(np.mean(d)), "p90": float(np.quantile(d, 0.9)),  # noqa: E731
                         "probability_at_or_above_actual": float(np.mean(np.asarray(d) >= abs(actual))), "draws": len(d)}
    return {"actual_unsigned_share": abs(actual), "random_series": summary(noise), "time_shifted_brand": summary(shift)}


def _block_bootstrap(
    frame: pd.DataFrame, outcome: str, groups: dict[str, list[str]], spec: dict[str, Any], keys: list[str],
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(int(spec["seed"]))
    n, block = len(frame), int(spec["block_weeks"])
    draws: dict[str, list[float]] = {f"{key}_{kind}": [] for key in keys for kind in ("explained", "total")}
    draws["brand_lenovo_specific"] = []
    for _ in range(int(spec["replications"])):
        starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        rows = np.concatenate([np.arange(start, start + block) for start in starts])[:n]
        result = _shares(frame.iloc[rows].reset_index(drop=True), outcome, groups)
        draws["brand_lenovo_specific"].append(_lenovo_specific(result))
        for key in keys:
            draws[f"{key}_explained"].append(result["signed_explained_share"].get(key, 0.0))
            draws[f"{key}_total"].append(result["total_share"].get(key, 0.0)
                                         * np.sign(result["signed_explained_share"].get(key, 0.0)))
    return {name: {"p05": float(np.quantile(values, 0.05)), "p50": float(np.quantile(values, 0.50)),
                   "p95": float(np.quantile(values, 0.95))} for name, values in draws.items()}


def _ratio_scale(manifest_path: str) -> dict[str, Any]:
    """Confirm the Brand Index is the ratio-scale share index the chain assumes (ADR-0040)."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    scale = manifest["display_scale"]
    if scale["type"] != "percent_of_base_share":
        raise ValueError("Brand Index is not a ratio-scale share index; the uplift chain is invalid.")
    return {"index_id": manifest["index_id"], "display_scale": scale["type"], "zero_index_level": 0.0,
            "reading": scale["reading"]}


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

    # ADR-0044: the brand's share of the Lenovo-specific explained movement is the measure.
    x_literal = brand["signed_explained_share"]["brand"]
    x = _lenovo_specific(brand)
    share_band = (boot_brand["brand_lenovo_specific"]["p05"], boot_brand["brand_lenovo_specific"]["p95"])
    placebo = _placebos(panel, outcome, groups, config["placebo"], x)

    # Indirect chain: Index lift -> % brand share of attention -> incremental brand value.
    chain = config["indirect_chain"]
    scale = _ratio_scale(inputs["brand_index_manifest"])
    counterfactual = pd.read_parquet(inputs["total_effect_weekly"])
    post_cf = counterfactual[counterfactual["period"].eq("post")].sort_values("week")
    trailing = int(chain["provisional_trailing_weeks"])
    post_cf = post_cf.iloc[:-trailing] if trailing else post_cf
    counterfactual_level = float(post_cf["synthetic_index"].mean())
    headroom = counterfactual_level - scale["zero_index_level"]
    elasticity = float(chain["brand_value_elasticity_to_brand_share"])
    brand_value = money(x)
    uplift = level / headroom
    coefficient = elasticity * brand_value / headroom
    donor_levels = pd.read_parquet(inputs["donor_sensitivity"])["post_mean_gap"]
    bv_low, bv_high = money(share_band[0]), money(share_band[1])
    indirect = {
        "brand_value_usd_m": brand_value,
        "zero_index_level": scale["zero_index_level"],
        "counterfactual_index_level": counterfactual_level,
        "sustained_lift_index_points": level,
        "brand_share_uplift_pct": 100 * uplift,
        "brand_value_elasticity_to_brand_share": elasticity,
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
        "note": "Total-effect chain (upper attribution band); the primary sponsorship value is fifa_specific_incremental_brand_value.",
    }
    values = {
        "brand_share_definition": config["brand_share_definition"],
        "brand_share": x,
        "brand_value_usd_m": money(x),
        "brand_share_90pct": list(share_band),
        "brand_value_90pct_usd_m": [bv_low, bv_high],
        "market_cap_base": config["valuation_base"]["primary"],
        "market_cap_usd_m": cap,
        "brand_value_by_cap_base_usd_m": {name: money(x, float(value)) for name, value in caps.items()},
        "literal_reading_reference": {
            "definition": "share of all explained variance, market factors included (ADR-0031; secondary since ADR-0044)",
            "brand_share": x_literal, "brand_value_usd_m": money(x_literal),
            "brand_value_90pct_usd_m": [money(boot_brand["brand_explained"]["p05"]), money(boot_brand["brand_explained"]["p95"])],
        },
    }

    # FIFA-specific incremental brand value (ADR-0043): primary uplift with statistical and attribution bands.
    fifa = json.loads(Path(inputs["fifa_specific_manifest"]).read_text(encoding="utf-8"))["fifa_specific_effect"]
    uplifts = {"primary": fifa["primary_uplift_pct"],
               "statistical_band_95_low": fifa["statistical_band_95_uplift_pct"][0],
               "statistical_band_95_high": fifa["statistical_band_95_uplift_pct"][1],
               "attribution_band_upper": fifa["attribution_band_upper_uplift_pct"]}
    fifa_specific = {
        "uplift_pct": uplifts,
        "index_points": {"primary": fifa["primary_index_points"],
                         "statistical_band_95": fifa["statistical_band_95_index_points"],
                         "attribution_band_upper": fifa["attribution_band_upper_index_points"]},
        "period": fifa["period"],
        "brand_value_usd_m": brand_value,
        "incremental_brand_value_usd_m": {name: elasticity * pct / 100 * brand_value for name, pct in uplifts.items()},
        "incremental_brand_value_brand_share_90pct_usd_m": [elasticity * uplifts["primary"] / 100 * bv_low,
                                                            elasticity * uplifts["primary"] / 100 * bv_high],
        "note": "Primary sponsorship valuation (ADR-0043, ADR-0044): FIFA-specific uplift x Lenovo-specific brand value.",
    }

    # 3. Stability: sample windows, leaving one control group out, alternative brand measures.
    stability = []

    def row(check: str, frame: pd.DataFrame, g: dict[str, list[str]]) -> dict[str, Any]:
        result = _shares(frame, outcome, g)
        share = _lenovo_specific(result) if any(k != "market" and k != "brand" for k in g) else float("nan")
        return {"check": check, "weeks": len(frame), "r2": result["r2"], "brand_share": share,
                "brand_value_usd_m": money(share), "literal_share": result["signed_explained_share"].get("brand", 0.0)}

    for start, end in config["stability"]["sample_windows"]:
        sample = panel[(panel["week"] >= pd.Timestamp(start)) & (panel["week"] <= pd.Timestamp(end))]
        stability.append(row(f"sample {start} to {end}", sample, groups))
    for dropped in [name for name in groups if name not in ("brand", "market")]:
        stability.append(row(f"without {dropped}", panel, {k: v for k, v in groups.items() if k != dropped}))
    for name, cols in config["stability"].get("extra_lenovo_groups", {}).items():
        sample = panel.dropna(subset=cols)
        stability.append(row(f"with {name} as an extra Lenovo-specific group", sample, {**groups, name: cols}))
    for alternative in config["stability"].get("brand_measures", []):
        sample = panel.dropna(subset=[alternative])
        stability.append(row(f"brand measured as {alternative}", sample, {**groups, "brand": [alternative]}))
    stability = pd.DataFrame(stability)
    stability["incremental_brand_value_usd_m"] = stability["brand_value_usd_m"] * elasticity * uplifts["primary"] / 100
    shares = stability["brand_share"].dropna()

    weights = pd.DataFrame([
        {"model": "brand_full_sample", "group": name, "dominance_r2": value,
         "share_of_explained": brand["explained_share"][name],
         "share_of_lenovo_specific": (value / sum(v for k, v in brand["weights"].items() if k != "market")
                                      if name != "market" else None),
         "signed_share_of_explained": brand["signed_explained_share"].get(name)}
        for name, value in brand["weights"].items()
    ])
    _write(weights, target, "dominance_weights")
    _write(stability, target, "stability")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": ("brand value = signed general-dominance share of the Lenovo-specific explained weekly return movement "
                   "(market factors set aside) x company value; incremental brand value = brand value x brand-share uplift x elasticity"),
        "decision": "ADR-0031, ADR-0032, ADR-0040, ADR-0044 (owner-selected; variance share read as value share and value proportional to brand share by assumption)",
        "accepted_for_accounting_or_causal_claim": False,
        "coefficients": {"brand_full_sample": brand["coefficients"]},
        "samples": {"brand_weeks": len(panel), "brand_model_r2": brand["r2"]},
        "primary_result": indirect,
        "fifa_specific_incremental_brand_value": fifa_specific,
        "index_scale": scale,
        "values": values,
        "placebo": placebo,
        "bootstrap": {"spec": config["bootstrap"], "brand": boot_brand},
        "external_reference": config.get("external_reference"),
        "stability_summary": {
            "brand_share_min": float(shares.min()), "brand_share_max": float(shares.max()),
            "brand_value_min_usd_m": money(float(shares.min())),
            "brand_value_max_usd_m": money(float(shares.max())),
        },
        "caveats": [
            "A share of explained return variance is not a share of value; the brand's role is read from price formation by assumption.",
            "The Lenovo-specific drivers explain a small part of weekly returns, so the brand's share of them is imprecise: see the bootstrap band and the placebo test, where an unrelated series obtains a comparable share.",
            "The measured Lenovo-specific drivers leave most Lenovo-specific movement unexplained; counting it in the denominator would shrink the share sharply.",
            "Dominance weights are sign-blind; shares are signed by the full-model coefficient so value-destroying co-movement is not counted as value.",
            "Brand value is assumed proportional to brand share of attention (elasticity 1) unless configured otherwise.",
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
