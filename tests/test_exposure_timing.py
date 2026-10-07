"""Exposure-timing diagnostic (ADR-0042): back-cast construction and published outputs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from srmp.experiments.sponsorship_exposure_timing_v1 import backcast_property

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/curated/experimental/sponsorship_exposure_timing_v1"


def test_backcast_repeats_the_observed_profile_scaled_by_year():
    weeks = pd.date_range("2023-01-02", "2025-12-29", freq="W-MON")
    observed_weeks = pd.date_range("2024-09-30", "2025-12-29", freq="W-MON")
    observed = pd.Series(np.arange(1, len(observed_weeks) + 1, dtype=float), index=observed_weeks)
    spec = {"profile_window": ["2024-09-30", "2025-09-28"], "pre_fifa_years": [2023, 2024]}
    combined, baseline = backcast_property(observed, weeks, {2023: 0.5, 2024: 1.0}, pd.Timestamp("2023-06-05"), spec)
    after = weeks >= observed_weeks.min()
    assert np.allclose(combined[after], observed.reindex(weeks[after]))          # observed weeks are untouched
    assert (combined[weeks < pd.Timestamp("2023-06-05")] == 0).all()             # nothing before activation
    same_iso = combined[weeks == pd.Timestamp("2023-10-02")].iloc[0] / combined[weeks == pd.Timestamp("2024-09-30")].iloc[0]
    assert np.isclose(same_iso, 0.5)                                             # 2023 scaled by 0.5 vs the 2024 profile
    assert np.isclose(baseline[weeks == pd.Timestamp("2024-09-30")].iloc[0], 0.75 * observed.iloc[0])  # mean pre-FIFA scale


def test_published_diagnostic_is_complete_and_never_changes_the_headline():
    manifest = json.loads((OUT / "exposure_timing_manifest.json").read_text(encoding="utf-8"))
    headline = json.loads((ROOT / "data/curated/experimental/sponsorship_total_effect_v1/estimate_manifest.json")
                          .read_text(encoding="utf-8"))
    assert manifest["headline_lift_index_points"] == headline["total_effect"]["lift_index_points"]
    assert manifest["status"] == "fifa_specific_effect_primary_ADR_0043"
    coefficients = pd.read_parquet(OUT / "exposure_timing_coefficients.parquet")
    assert set(coefficients["test"]) == {"pre_period_nonfifa", "post_period_incremental", "full_sample"}
    weekly = pd.read_parquet(OUT / "exposure_timing_weekly.parquet")
    before = pd.to_datetime(weekly["week"]) < pd.Timestamp("2024-10-14")   # announcement week: 15 October 2024
    assert (weekly.loc[before, "fifa_impressions"] == 0).all()


def test_fifa_specific_decomposition_adds_up_and_bands_bracket_the_primary():
    fs = json.loads((OUT / "exposure_timing_manifest.json").read_text(encoding="utf-8"))["fifa_specific_effect"]
    d = fs["decomposition_index_points"]
    assert np.isclose(d["fifa"] + d["other_sponsorships"] + d["events"] + d["residual"], d["total_gap"])
    assert fs["primary_specification"] == "full_sample:levels_with_trend"
    low, high = fs["statistical_band_95_index_points"]
    assert low < fs["primary_index_points"] < high
    assert fs["primary_index_points"] <= fs["attribution_band_upper_index_points"]
    assert np.isclose(fs["primary_uplift_pct"], 100 * fs["primary_index_points"] / fs["counterfactual_index_level"])
