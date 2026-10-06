"""Co-brand association placebo test (ADR-0035).

"Lenovo FIFA" and "Lenovo World Cup" search interest is compared with the
same construct for brands that do not sponsor FIFA, all on one common-anchor
scale. The statistic is the log change from a pre-announcement baseline to
each test window; Lenovo's rank among the placebos gives a one-sided p-value.
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

from srmp.experiments.brand_financial_bridge_v1 import _sha256, _write
from srmp.experiments.sponsorship_counterfactual_v1 import _monday


def _window_mean(series: pd.Series, start: Any, end: Any) -> float:
    mask = series.index >= pd.Timestamp(start)
    if end is not None:
        mask &= series.index <= pd.Timestamp(end)
    return float(series[mask].mean())


def log_changes(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Log change per query and window; ``panel`` is week x query on one scale."""
    floor = float(config["log_floor"])
    baseline = config["baseline_window"]
    rows = []
    for query in panel.columns:
        series = panel[query].dropna()
        base = _window_mean(series, *baseline)
        for window, (start, end) in config["test_windows"].items():
            value = _window_mean(series, start, end)
            rows.append({"query_id": query, "window": window, "baseline_mean": base, "window_mean": value,
                         "log_change": float(np.log((value + floor) / (base + floor)))})
    return pd.DataFrame(rows)


def build_cobrand_placebo(config_path: str = "config/experiments/cobrand_placebo_v1.yaml") -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    inputs = config["inputs"]
    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)

    trends = pd.read_parquet(inputs["cobrand_trends"])
    trends["week"] = _monday(trends["week"])
    panel = trends.groupby(["week", "query_id"])["interest_common_scale"].mean().unstack().sort_index()
    trailing = int(config["provisional_trailing_weeks"])
    if trailing:
        panel = panel.iloc[:-trailing]
    changes = log_changes(panel, config)

    alpha = float(config["significance_level"])
    tests = []
    for construct, spec in config["constructs"].items():
        for window in config["test_windows"]:
            subset = changes[changes["window"].eq(window)].set_index("query_id")["log_change"]
            placebos = [subset[q] for q in spec["placebos"] if q in subset]
            treated = float(subset[spec["treated"]])
            p_value = (1 + sum(value >= treated for value in placebos)) / (1 + len(placebos))
            tests.append({
                "construct": construct, "window": window, "treated_log_change": treated,
                "treated_multiple": float(np.exp(treated)),
                "placebo_median_log_change": float(np.median(placebos)),
                "placebo_max_log_change": float(np.max(placebos)),
                "placebos": len(placebos), "p_value": p_value, "significant": p_value <= alpha,
            })
    tests = pd.DataFrame(tests)

    # Within-Lenovo: other sponsored properties, separately normalised queries.
    lenovo = pd.read_parquet(inputs["lenovo_property_trends"])
    lenovo = lenovo[lenovo["query_id"].isin(config["lenovo_property_queries"])].copy()
    lenovo["week"] = _monday(lenovo["week"])
    property_panel = lenovo.pivot_table(index="week", columns="query_id", values="interest_mean").sort_index()
    if trailing:
        property_panel = property_panel.iloc[:-trailing]
    properties = log_changes(property_panel, config)

    _write(changes, target, "log_changes")
    _write(tests, target, "placebo_tests")
    _write(properties, target, "lenovo_property_comparison")
    manifest = {
        "experiment_id": config["experiment_id"], "status": config["status"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tests": tests.to_dict("records"),
        "lenovo_property_comparison": properties.pivot(index="query_id", columns="window",
                                                       values="log_change").to_dict(),
        "interpretation": (
            "Measures whether people came to associate Lenovo with FIFA beyond what non-sponsor "
            "tech brands show. It is evidence of association, not of brand-salience lift."
        ),
        "inputs": {name: {"path": path, "sha256": _sha256(path)} for name, path in inputs.items()},
    }
    (target / "cobrand_placebo_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/cobrand_placebo_v1.yaml")
    args = parser.parse_args()
    build_cobrand_placebo(args.config)
