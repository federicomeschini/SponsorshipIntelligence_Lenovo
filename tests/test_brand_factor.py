"""Factor Brand Index (ADR-0039): share-of-attention signals, survey use and donor basis."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from srmp.index.brand_factor import MixedFrequencyFactor, donor_shares_of_search, log_share

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data/curated/index"


def test_log_share_cancels_a_common_demand_shock():
    frame = pd.DataFrame({"lenovo": [10.0, 20.0], "dell": [5.0, 10.0], "hp": [5.0, 10.0]})
    share = log_share(frame, ["lenovo"], ["dell", "hp"])
    assert np.allclose(share, 0.0)   # every brand doubles: share unchanged


def test_donor_shares_exclude_the_donor_itself_and_lenovo():
    donors = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 3.0], "c": [6.0, 6.0]})
    shares = donor_shares_of_search(donors, ["a", "b", "c"])
    assert np.isclose(shares.loc[1, "a"], np.log(2.0 / 9.0))
    assert np.isclose(shares.loc[1, "b"], np.log(3.0 / 8.0))
    assert "anchor_lenovo" not in shares


def test_mixed_frequency_model_recovers_a_known_factor():
    rng = np.random.default_rng(0)
    weeks = pd.date_range("2020-01-06", periods=260, freq="W-MON")
    factor = np.zeros(len(weeks))
    for t in range(1, len(weeks)):
        factor[t] = 0.9 * factor[t - 1] + rng.normal(0, np.sqrt(1 - 0.81))
    quarter = pd.PeriodIndex(weeks, freq="Q")
    data = pd.DataFrame({"weekly": factor + rng.normal(0, 0.5, len(weeks))}, index=weeks)
    survey = pd.Series(factor, index=weeks).groupby(quarter).transform("mean") + rng.normal(0, 0.1, len(weeks))
    last = pd.Series(weeks, index=weeks).groupby(quarter).transform("max").to_numpy() == weeks
    data["quarterly"] = np.where(last, survey, np.nan)
    n_per_week = pd.Series(weeks, index=weeks).groupby(quarter).transform("size").to_numpy().astype(float)
    reset = np.r_[1.0, (quarter[1:] != quarter[:-1]).astype(float)]
    result = MixedFrequencyFactor(data, ["weekly"], ["quarterly"], reset, n_per_week).fit(disp=False, maxiter=2000)
    smoothed = result.smoothed_state[0] * np.sign(np.asarray(result.params)[1])
    assert np.corrcoef(smoothed, factor)[0, 1] > 0.85
    assert np.asarray(result.params)[2] * np.asarray(result.params)[1] > 0   # survey loads with the same sign


def test_published_index_passes_its_own_gates():
    manifest = json.loads((INDEX / "brand_index_manifest.json").read_text(encoding="utf-8"))
    loadings = pd.read_parquet(INDEX / "brand_index_loadings.parquet")
    screen = pd.read_parquet(INDEX / "brand_index_validity_screen.parquet")
    weekly = pd.read_parquet(INDEX / "brand_index_weekly.parquet")
    assert manifest["converged"]
    assert (loadings["loading"] > 0).all(), "every signal, survey included, must load positively"
    assert set(manifest["validity_screen"]["admitted"]) == set(screen.loc[screen["admitted"], "signal"])
    assert all(fit["correlation"] > 0 for fit in manifest["survey_fit"].values())
    base = pd.to_datetime(weekly["week"]).between(*pd.to_datetime(manifest["standardisation_base"]))
    assert np.isclose(np.log(weekly.loc[base, "index_level"]).mean(), np.log(100), atol=1e-6)
    assert "product_search_demand" in weekly and "product" not in " ".join(manifest["validity_screen"]["admitted"])
