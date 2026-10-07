"""Proxy-led weekly Lenovo Brand Index.

The current usable construct is not a weekly survey reconstruction.  It is a
weekly, proxy-led measure of Lenovo brand salience, calibrated onto the scale
of the available GWI engagement and consideration composite. Google Trends
supplies *all* week-to-week movement;
the survey is used only once, to orient and scale the proxy at quarterly
frequency.  No survey wave is pinned to an arbitrary week and no quarterly
survey value is mechanically interpolated.

Only the clean parent-brand query enters the headline index. Product, price,
co-branded and competitor searches remain useful diagnostics or outcomes, but
pooling them creates a broader construct and is therefore documented as a
separate experimental alternative.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


_GRID_START = pd.Timestamp("2022-01-03")
_CORE_QUERY = "brand_lenovo"
_COMPANION_QUERY_GROUPS = {
    "product_portfolio_proxy_z": (
        "category_lenovo_laptop",
        "category_thinkpad",
        "category_lenovo_legion",
    ),
    "commercial_intent_proxy_z": (
        "category_lenovo_laptop_price",
        "category_thinkpad_price",
    ),
}
_EXCLUDED = {
    "product_queries": "product demand is a companion pulse; it belongs to the experimental multi-signal construction rather than the headline salience index",
    "price_queries": "transaction/promotion intent, not broad brand salience",
    "co_branded_queries": "property-attributed outcomes; retain for sponsorship analysis",
    "competitor_queries": "benchmark/donor series, not Lenovo-index constituents",
    "wikipedia_and_gdelt": "did not show a stable positive relationship to the available GWI composite",
}


def _monday(values: pd.Series) -> pd.Series:
    values = pd.to_datetime(values)
    # Google Trends weekly points are Sunday-labelled starts. C-INDEX uses
    # W-MON, so Sunday advances to the following Monday; already-Monday inputs
    # stay unchanged.
    return values + pd.to_timedelta((7 - values.dt.weekday) % 7, unit="D")


def _zscore(values: pd.Series) -> tuple[pd.Series, float]:
    sd = float(values.std(ddof=0))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("Proxy-led index requires a Trends series with non-zero variation.")
    return (values - values.mean()) / sd, sd


def _proxy_components(trends_path: str) -> tuple[pd.DataFrame, pd.Series, pd.Series, dict[str, Any]]:
    trends = pq.read_table(trends_path).to_pandas()
    available = set(trends["query_id"].unique())
    required = {_CORE_QUERY, *(query for group in _COMPANION_QUERY_GROUPS.values() for query in group)}
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"Proxy-led index missing required Trends queries: {missing}")

    trends["week"] = _monday(trends["week"])
    trends = trends[trends["week"] >= _GRID_START]
    if trends.empty:
        raise ValueError("Proxy-led index has no Trends observations in the configured horizon.")

    group = trends[trends["query_id"].eq(_CORE_QUERY)].sort_values("week").set_index("week")
    proxy_z, raw_sd = _zscore(group["interest_mean"].astype(float))
    # Overlapping windows are alternate normalisations, not independent draws.
    # Their dispersion is therefore retained directly rather than divided by
    # sqrt(n), which would understate measurement uncertainty.
    proxy_window_sd = group["interest_sd"].fillna(0.0).astype(float) / raw_sd
    components = pd.DataFrame({"brand_salience_proxy_z": proxy_z})
    for component, queries in _COMPANION_QUERY_GROUPS.items():
        subset = trends[trends["query_id"].isin(queries)].copy()
        standardized = []
        for _, query_rows in subset.groupby("query_id"):
            query_rows = query_rows.sort_values("week").set_index("week")
            query_z, _ = _zscore(query_rows["interest_mean"].astype(float))
            standardized.append(query_z)
        components[component] = pd.concat(standardized, axis=1).mean(axis=1)
    components = components.dropna().sort_index()
    proxy_z = components["brand_salience_proxy_z"]
    proxy_window_sd = proxy_window_sd.reindex(components.index)
    metadata = {
        "headline_query": _CORE_QUERY,
        "companion_query_groups": {key: list(value) for key, value in _COMPANION_QUERY_GROUPS.items()},
        "window_accounting": {
            "min_window_estimates": int(group["draws_used"].min()),
            "max_window_estimates": int(group["draws_used"].max()),
            "mean_window_estimates": round(float(group["draws_used"].mean()), 3),
            "interpretation": "overlap-rescaled window estimates; not independent repeated draws",
        },
        "n_weeks": int(len(group)),
        "week_span": [group.index.min().date().isoformat(), group.index.max().date().isoformat()],
    }
    return components, proxy_z, proxy_window_sd, metadata


def _calibrate(proxy_z: pd.Series, composite_path: str) -> dict[str, Any]:
    composite = pq.read_table(composite_path).to_pandas()
    composite["quarter"] = pd.PeriodIndex(pd.to_datetime(composite["fieldwork_midpoint"]), freq="Q")
    survey = composite.set_index("quarter")["composite_z"].astype(float)
    proxy_quarterly = proxy_z.groupby(pd.PeriodIndex(proxy_z.index, freq="Q")).mean()
    paired = pd.DataFrame({"proxy_z": proxy_quarterly, "survey_z": survey}).dropna()
    if len(paired) < 8:
        raise ValueError("Proxy-led index needs at least eight overlapping survey quarters for calibration.")
    slope, intercept = np.polyfit(paired["proxy_z"], paired["survey_z"], 1)
    if slope <= 0:
        raise ValueError("Proxy-led index calibration produced a non-positive survey relationship.")
    fitted = intercept + slope * paired["proxy_z"]
    residual = paired["survey_z"] - fitted
    return {
        "intercept": float(intercept),
        "slope": float(slope),
        "n_quarters": int(len(paired)),
        "correlation": float(paired["proxy_z"].corr(paired["survey_z"])),
        "first_difference_correlation": float(paired.diff().corr().loc["proxy_z", "survey_z"]),
        "residual_sd": float(residual.std(ddof=1)),
        "survey_quarters": [str(quarter) for quarter in paired.index],
    }


def build_proxy_led_index(
    trends_path: str = "data/curated/trends/trends_weekly_averaged.parquet",
    composite_path: str = "data/curated/index/brand_index_composite_quarterly.parquet",
    output_dir: str = "data/curated/index",
) -> dict[str, Any]:
    """Build the search-salience index from grouped Google Trends proxies.

    Superseded as the Brand Index by the brand-level factor index (ADR-0040,
    ``srmp/index/brand_factor.py``); kept as the search-salience cross-check.
    The result is a proxy-led salience index on the survey composite's 100/15
    display scale.  It must be described as a salience/portfolio-interest index,
    not as direct weekly survey measurement or causal sponsorship impact.
    """
    components, proxy_z, proxy_window_sd, proxy_meta = _proxy_components(trends_path)
    calibration = _calibrate(proxy_z, composite_path)
    calibrated_z = calibration["intercept"] + calibration["slope"] * proxy_z
    # Mapping residual is the dominant uncertainty: it measures the observed
    # quarter-level mismatch between proxy salience and the GWI composite.
    index_se = 15.0 * np.sqrt(calibration["residual_sd"] ** 2 + (calibration["slope"] * proxy_window_sd) ** 2)
    quarter = pd.PeriodIndex(proxy_z.index, freq="Q")
    rows = [{
        "week": week.date(),
        "index_level": round(float(100.0 + 15.0 * calibrated_z.loc[week]), 4),
        "index_se": round(float(index_se.loc[week]), 4),
        "proxy_z": round(float(proxy_z.loc[week]), 6),
        "calendar_quarter": str(quarter[i]),
        "source_version": "v4_proxy_led_brand_calibrated",
        "anchored": False,
    } for i, week in enumerate(proxy_z.index)]
    schema = pa.schema([
        ("week", pa.date32()), ("index_level", pa.float64()), ("index_se", pa.float64()),
        ("proxy_z", pa.float64()), ("calendar_quarter", pa.string()),
        ("source_version", pa.string()), ("anchored", pa.bool_()),
    ])
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, target / "search_salience_index_weekly.parquet")
    pacsv.write_csv(table, target / "search_salience_index_weekly.csv")

    component_rows = [{
        "week": week.date(),
        **{name: round(float(components.loc[week, name]), 6) for name in components.columns},
    } for week in components.index]
    component_schema = pa.schema(
        [("week", pa.date32())] + [(name, pa.float64()) for name in components.columns]
    )
    component_table = pa.Table.from_pylist(component_rows, schema=component_schema)
    pq.write_table(component_table, target / "brand_index_components_weekly.parquet")
    pacsv.write_csv(component_table, target / "brand_index_components_weekly.csv")

    manifest = {
        "contract": "search-salience cross-check (C-INDEX until ADR-0040)",
        "status": "provisional_proxy_led_index_built",
        "role": "cross-check only; the Brand Index is data/curated/index/brand_index_weekly.parquet (ADR-0040)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": "v4_proxy_led_brand_calibrated",
        "construct": "Lenovo brand salience, proxy-led",
        "weekly_movement": "100% from the validated Lenovo parent-brand Google Trends proxy; survey values do not pin individual weeks",
        "survey_role": "quarterly orientation and display-scale calibration using the non-canonical GWI engagement/consideration composite",
        "calibration": {key: (round(value, 6) if isinstance(value, float) else value)
                        for key, value in calibration.items()},
        "retained_inputs": proxy_meta,
        "excluded_from_core_index": _EXCLUDED,
        "replaces": ["v1_chowlin_provisional", "v2_statespace_provisional", "v3_proxy_led_calibrated"],
        "caveat": "This is a proxy-led salience index, not direct weekly survey measurement, a complete brand-equity measure, or a causal sponsorship estimate.",
    }
    (target / "search_salience_index_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trends", default="data/curated/trends/trends_weekly_averaged.parquet")
    parser.add_argument("--composite", default="data/curated/index/brand_index_composite_quarterly.parquet")
    parser.add_argument("--output-dir", default="data/curated/index")
    args = parser.parse_args()
    build_proxy_led_index(args.trends, args.composite, args.output_dir)
