import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/sponsorship_total_return_v2"


def test_dynamic_total_return_supersedes_single_multiplication():
    manifest = json.loads(
        (EXPERIMENT / "total_return_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["accepted_for_planning"] is True
    assert manifest["accepted_for_accounting_or_causal_claim"] is False
    result = manifest["primary_planning_result"]
    assert 650 < result["observed_path_fully_matured_value_usd_m"] < 850
    assert 1_100 < result["full_contract_planning_value_usd_m"] < 1_400


def test_scenarios_are_ordered_and_base_is_pre_tournament():
    scenarios = pd.read_parquet(EXPERIMENT / "total_return_scenarios.parquet")
    ordered = scenarios.set_index("scenario").loc[
        ["low", "base", "high"], "full_contract_planning_value_usd_m"
    ]
    assert ordered.is_monotonic_increasing
    anchors = pd.read_parquet(EXPERIMENT / "response_curve_anchors.parquet")
    base = anchors[anchors["scenario"].eq("base")]
    assert base["source"].eq("endpoint_2025-12-31").all()


def test_regularized_response_curves_are_nonnegative_and_monotone():
    curves = pd.read_parquet(EXPERIMENT / "response_curve_weekly.parquet")
    for _, group in curves.groupby("scenario"):
        values = group.sort_values("lag_weeks")["cumulative_response"].to_numpy()
        assert (values >= 0).all()
        assert (np.diff(values) >= -1e-12).all()


def test_counterfactual_is_translated_to_innovation_units():
    weekly = pd.read_parquet(EXPERIMENT / "sponsorship_dynamic_weekly.parquet")
    assert len(weekly) == 90
    assert weekly["sponsorship_bi_innovation"].notna().all()
    assert 0.6 < weekly["sponsorship_bi_innovation"].sum() < 0.9
