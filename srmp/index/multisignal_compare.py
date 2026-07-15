"""Experimental Lenovo-only multi-signal Brand Index comparison.

This module deliberately does not replace the canonical proxy-led salience
index. It builds three transparent experimental composites from the same four
Lenovo-performance dimensions:

* evidence_weighted: non-negative, sum-to-one ridge weights with a fixed
  strong-shrinkage penalty, calibrated against the GWI composite;
* pca: first principal component of the same standardized dimensions;
* entropy: Shannon-entropy weights, which reward information dispersion rather
  than agreement with the survey.

Every method is separately calibrated to the GWI composite's mean-100 / SD-15
display scale. Calibration is a scale mapping, not a weekly survey anchor.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import matplotlib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from scipy.optimize import minimize

matplotlib.use("Agg")
import matplotlib.pyplot as plt


COMPONENTS = (
    "brand_salience_proxy_z",
    "product_portfolio_proxy_z",
    "commercial_intent_proxy_z",
    "earned_news_tone_z",
)
METHODS = ("evidence_weighted", "pca", "entropy")
_EVIDENCE_RIDGE = 5.0


@dataclass
class MethodFit:
    """Fitted transform mapping component rows to an uncalibrated score."""

    method: str
    transform: Callable[[pd.DataFrame], pd.Series]
    weights: dict[str, float]
    metadata: dict[str, object]


def _zscore(values: pd.Series) -> pd.Series:
    sd = float(values.std(ddof=0))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("Multi-signal component has zero or invalid variation.")
    return (values - values.mean()) / sd


def _load_weekly_components(
    components_path: str,
    gdelt_path: str,
) -> pd.DataFrame:
    """Combine Trends dimensions with a directional earned-news-tone dimension."""
    components = pq.read_table(components_path).to_pandas()
    components["week"] = pd.to_datetime(components["week"])
    components = components.set_index("week").sort_index()

    gdelt = pq.read_table(gdelt_path).to_pandas()
    gdelt["date"] = pd.to_datetime(gdelt["date"])
    gdelt["week"] = gdelt["date"] - pd.to_timedelta(gdelt["date"].dt.weekday, unit="D")
    tone = gdelt.groupby("week")["mean_tone"].mean()
    # GDELT has a small number of provider-missing days. A week with no
    # returned tone is set to the observed-period mean, i.e. neutral after
    # standardization, rather than dropping an otherwise complete index week.
    tone = tone.reindex(components.index)
    tone = tone.fillna(float(tone.mean())).rename("earned_news_tone_z")
    components = components.join(_zscore(tone), how="left")
    components = components.loc[:, COMPONENTS].sort_index()
    if len(components) < 100:
        raise ValueError("Multi-signal comparison requires a complete weekly component panel.")
    return components


def _load_survey(composite_path: str) -> pd.Series:
    composite = pq.read_table(composite_path).to_pandas()
    composite["quarter"] = pd.PeriodIndex(
        pd.to_datetime(composite["fieldwork_midpoint"]), freq="Q"
    )
    return composite.set_index("quarter")["composite_z"].astype(float)


def _quarterly(weekly: pd.DataFrame, survey: pd.Series) -> pd.DataFrame:
    quarters = pd.PeriodIndex(weekly.index, freq="Q")
    panel = weekly.groupby(quarters).mean()
    panel["survey_z"] = survey
    panel = panel.dropna().sort_index()
    if len(panel) < 12:
        raise ValueError("Multi-signal comparison requires at least 12 overlapping survey quarters.")
    return panel


def _standardize_fit(
    train: pd.DataFrame,
    values: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    mean = train.loc[:, COMPONENTS].mean()
    sd = train.loc[:, COMPONENTS].std(ddof=0).replace(0, np.nan)
    if sd.isna().any():
        raise ValueError("Cannot standardize zero-variance multi-signal component.")
    return (values.loc[:, COMPONENTS] - mean) / sd, {"mean": mean, "sd": sd}


def _evidence_fit(train: pd.DataFrame, ridge: float) -> MethodFit:
    x_train, scaling = _standardize_fit(train, train)
    y = _zscore(train["survey_z"]).to_numpy(float)
    matrix = x_train.to_numpy(float)
    n = len(COMPONENTS)

    def objective(weights: np.ndarray) -> float:
        residual = y - matrix @ weights
        return float(residual @ residual + ridge * (weights @ weights))

    result = minimize(
        objective,
        x0=np.repeat(1.0 / n, n),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n,
        constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1.0},
        options={"ftol": 1e-12, "maxiter": 500},
    )
    if not result.success:
        raise ValueError(f"Evidence-weight fit failed: {result.message}")
    weights = result.x

    def transform(values: pd.DataFrame) -> pd.Series:
        standardized = (values.loc[:, COMPONENTS] - scaling["mean"]) / scaling["sd"]
        return pd.Series(standardized.to_numpy(float) @ weights, index=values.index)

    return MethodFit(
        method="evidence_weighted",
        transform=transform,
        weights={name: float(weight) for name, weight in zip(COMPONENTS, weights)},
        metadata={"ridge": ridge, "optimizer": "SLSQP_nonnegative_sum_to_one"},
    )


def _pca_fit(train: pd.DataFrame) -> MethodFit:
    x_train, scaling = _standardize_fit(train, train)
    _, _, right = np.linalg.svd(x_train.to_numpy(float), full_matrices=False)
    loadings = right[0]
    raw = x_train.to_numpy(float) @ loadings
    if np.corrcoef(raw, train["survey_z"].to_numpy(float))[0, 1] < 0:
        loadings = -loadings

    def transform(values: pd.DataFrame) -> pd.Series:
        standardized = (values.loc[:, COMPONENTS] - scaling["mean"]) / scaling["sd"]
        return pd.Series(standardized.to_numpy(float) @ loadings, index=values.index)

    return MethodFit(
        method="pca",
        transform=transform,
        weights={name: float(weight) for name, weight in zip(COMPONENTS, loadings)},
        metadata={"method": "first_principal_component", "weight_interpretation": "signed loading"},
    )


def _entropy_fit(train: pd.DataFrame) -> MethodFit:
    minimum = train.loc[:, COMPONENTS].min()
    span = train.loc[:, COMPONENTS].max() - minimum
    span = span.replace(0, np.nan)
    if span.isna().any():
        raise ValueError("Cannot entropy-weight zero-range multi-signal component.")
    normalized_train = (train.loc[:, COMPONENTS] - minimum) / span
    positive = normalized_train + 1e-12
    probability = positive / positive.sum(axis=0)
    entropy = -(probability * np.log(probability)).sum(axis=0) / np.log(len(train))
    divergence = 1.0 - entropy
    weights = divergence / divergence.sum()

    def transform(values: pd.DataFrame) -> pd.Series:
        normalized = (values.loc[:, COMPONENTS] - minimum) / span
        return normalized @ weights

    return MethodFit(
        method="entropy",
        transform=transform,
        weights={name: float(weights[name]) for name in COMPONENTS},
        metadata={"method": "Shannon_entropy", "weight_interpretation": "higher temporal dispersion receives higher weight"},
    )


def _fit_method(method: str, train: pd.DataFrame, ridge: float = _EVIDENCE_RIDGE) -> MethodFit:
    if method == "evidence_weighted":
        return _evidence_fit(train, ridge)
    if method == "pca":
        return _pca_fit(train)
    if method == "entropy":
        return _entropy_fit(train)
    raise ValueError(f"Unknown index method: {method}")


def _leave_one_quarter_stability(method: str, panel: pd.DataFrame) -> dict[str, object]:
    """Report how much fitted weights depend on any one GWI quarter.

    This is a robustness diagnostic for a descriptive index. It intentionally
    does not evaluate or select a method as a forecast.
    """
    full_fit = _fit_method(method, panel)
    refit_weights: list[dict[str, float]] = []
    excluded_quarters: list[str] = []
    for quarter in panel.index:
        refit = _fit_method(method, panel.drop(index=quarter))
        refit_weights.append(refit.weights)
        excluded_quarters.append(str(quarter))

    refits = pd.DataFrame(refit_weights, index=excluded_quarters)
    weight_ranges = {
        component: {
            "min": float(refits[component].min()),
            "max": float(refits[component].max()),
            "sd": float(refits[component].std(ddof=0)),
            "max_abs_shift_from_full": float(
                (refits[component] - full_fit.weights[component]).abs().max()
            ),
        }
        for component in COMPONENTS
    }
    return {
        "review": "leave_one_quarter_out",
        "n_refits": int(len(refits)),
        "weight_ranges": weight_ranges,
    }


def _calibration(
    score: pd.Series,
    survey: pd.Series,
) -> dict[str, float]:
    paired = pd.DataFrame({"score": score, "survey_z": survey}).dropna()
    slope, intercept = np.polyfit(paired["score"], paired["survey_z"], 1)
    if slope <= 0:
        raise ValueError("Multi-signal calibration has a non-positive GWI relationship.")
    residual = paired["survey_z"] - (intercept + slope * paired["score"])
    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "correlation": float(paired["score"].corr(paired["survey_z"])),
        "first_difference_correlation": float(paired.diff().corr().loc["score", "survey_z"]),
        "residual_sd": float(residual.std(ddof=1)),
    }


def _write_figure(comparison: pd.DataFrame, output_path: str) -> None:
    fig, ax = plt.subplots(figsize=(13, 6))
    colors = {
        "evidence_weighted": "#2458a6",
        "pca": "#00897b",
        "entropy": "#a85d00",
    }
    for method in METHODS:
        ax.plot(
            comparison["week"], comparison[f"{method}_index_level"],
            label=method.replace("_", " ").title(), color=colors[method], linewidth=1.7,
        )
    ax.set_title("Lenovo Brand Index — multi-signal weighting comparison", loc="left", fontweight="bold")
    ax.set_ylabel("Index (GWI-calibrated scale)")
    ax.axhline(100, color="#999999", linewidth=0.8, linestyle=":")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=130)
    plt.close(fig)


def build_multisignal_comparison(
    components_path: str = "data/curated/index/brand_index_components_weekly.parquet",
    gdelt_path: str = "data/staged/gdelt/gdelt_brand_daily.parquet",
    composite_path: str = "data/curated/index/brand_index_composite_quarterly.parquet",
    output_dir: str = "data/curated/index",
    figure_path: str = "reports/figures/brand_index_method_comparison.png",
) -> dict[str, object]:
    """Build experimental weighting-method variants without replacing C-INDEX."""
    weekly = _load_weekly_components(components_path, gdelt_path)
    survey = _load_survey(composite_path)
    panel = _quarterly(weekly, survey)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    output = pd.DataFrame(index=weekly.index)
    quarterly_output = pd.DataFrame({"quarter": [str(quarter) for quarter in panel.index], "gwi_composite_z": panel["survey_z"].to_numpy()})
    manifest_methods: dict[str, object] = {}
    for method in METHODS:
        fit = _fit_method(method, panel)
        weekly_score = fit.transform(weekly)
        quarterly_score = fit.transform(panel)
        calibration = _calibration(quarterly_score, panel["survey_z"])
        output[f"{method}_index_level"] = 100.0 + 15.0 * (
            calibration["intercept"] + calibration["slope"] * weekly_score
        )
        output[f"{method}_index_se"] = 15.0 * calibration["residual_sd"]
        quarterly_output[f"{method}_score"] = quarterly_score.to_numpy()
        quarterly_output[f"{method}_calibrated_z"] = (
            calibration["intercept"] + calibration["slope"] * quarterly_score
        ).to_numpy()
        manifest_methods[method] = {
            "weights": {key: round(value, 6) for key, value in fit.weights.items()},
            "weight_metadata": fit.metadata,
            "calibration": {key: round(value, 6) for key, value in calibration.items()},
            "leave_one_quarter_stability": _leave_one_quarter_stability(method, panel),
        }

    output.index.name = "week"
    output = output.reset_index()
    comparison_rows = []
    for _, row in output.iterrows():
        comparison_rows.append({
            "week": row["week"].date(),
            **{column: round(float(row[column]), 6) for column in output.columns if column != "week"},
        })
    comparison_schema = pa.schema(
        [("week", pa.date32())]
        + [(column, pa.float64()) for column in output.columns if column != "week"]
    )
    comparison_table = pa.Table.from_pylist(comparison_rows, schema=comparison_schema)
    pq.write_table(comparison_table, target / "brand_index_method_comparison_weekly.parquet")
    pacsv.write_csv(comparison_table, target / "brand_index_method_comparison_weekly.csv")

    quarterly_table = pa.Table.from_pandas(quarterly_output, preserve_index=False)
    pq.write_table(quarterly_table, target / "brand_index_method_comparison_quarterly.parquet")
    pacsv.write_csv(quarterly_table, target / "brand_index_method_comparison_quarterly.csv")
    _write_figure(output, figure_path)

    manifest = {
        "status": "experimental_comparison_built",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "construct": "Lenovo-only multi-signal brand-performance composite",
        "status_of_current_canonical_index": "unchanged; this comparison does not replace v4_proxy_led_brand_calibrated",
        "components": {
            "brand_salience_proxy_z": "worldwide Lenovo parent-brand Google Trends",
            "product_portfolio_proxy_z": "Lenovo laptop, ThinkPad and Lenovo Legion Google Trends",
            "commercial_intent_proxy_z": "Lenovo laptop price and ThinkPad price Google Trends",
            "earned_news_tone_z": "weekly mean GDELT tone",
        },
        "excluded_from_components": {
            "relative_peer_position": "excluded by design: peer comparison is benchmarking, not Lenovo brand performance",
            "wikipedia": "attention is not reliably directional against the available GWI construct",
            "gdelt_volume": "news volume measures attention; it is retained as context rather than a directional performance component",
            "co_branded_trends": "property outcomes, not broad Lenovo brand performance",
            "blinkfire": "sponsorship exposure, retained as a potential explanatory variable rather than index input",
        },
        "survey_role": {
            "gwi_engagement_consideration": "PC1 composite used to calibrate each method's arbitrary score onto a 100/15 display scale; it does not anchor individual weeks",
            "consumer_research_awareness_appeal_purchase_intent": "segmented sponsorship-lift evidence; unsuitable for population calibration because of selection, changing scales and missing population totals",
        },
        "methods": manifest_methods,
        "caveat": "PCA and entropy create a single score without optimizing survey fit. Evidence weighting is supervised but has only 17 overlapping quarters. The comparison is descriptive: survey convergence and method/weight stability matter; it is not a forecast competition.",
    }
    (target / "brand_index_method_comparison_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--components", default="data/curated/index/brand_index_components_weekly.parquet")
    parser.add_argument("--gdelt", default="data/staged/gdelt/gdelt_brand_daily.parquet")
    parser.add_argument("--composite", default="data/curated/index/brand_index_composite_quarterly.parquet")
    parser.add_argument("--output-dir", default="data/curated/index")
    parser.add_argument("--figure", default="reports/figures/brand_index_method_comparison.png")
    args = parser.parse_args()
    build_multisignal_comparison(args.components, args.gdelt, args.composite, args.output_dir, args.figure)
