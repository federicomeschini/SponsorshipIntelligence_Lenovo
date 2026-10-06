import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from srmp.counterfactual import scm


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/world_cup_impact_v1"


def _manifest(name: str) -> dict:
    return json.loads((EXPERIMENT / name).read_text(encoding="utf-8"))


def test_world_cup_primary_evaluation_is_preregistered_and_readiness_tracks_coverage():
    manifest = _manifest("readiness_manifest.json")
    assert "primary sponsorship impact evaluation" in manifest["role"]
    assert manifest["canonical_contracts_replaced"] == []
    # Tournament dates come from the official calendar; activation stays client-owned.
    assert "activation_start" in manifest["missing_milestone_dates"]
    assert "tournament_start" not in manifest["missing_milestone_dates"]
    readiness = {row["source"]: row for row in manifest["source_readiness"]}
    for name in ("brand_index", "world_cup_exposure"):
        row = readiness[name]
        assert row["required_coverage_through"] == "2026-10-18"
        complete = row["status"] == "available_pending_coverage_check"
        assert complete == (name not in manifest["required_sources_waiting"])
    assert manifest["estimation_policy"]["minimum_credible_donors"] == 9
    assert manifest["estimation_policy"]["maximum_placebo_p_value"] == 0.10


def test_world_cup_estimand_is_frozen_before_outcomes_arrive():
    protocol = _manifest("preregistered_estimands.json")
    assert protocol["frozen_estimands"]["primary"]["name"] == (
        "sustained_world_cup_brand_index_uplift"
    )
    assert protocol["counterfactual_protocol"]["prohibit_post_outcome_tuning"] is True
    assert len(protocol["protocol_hash"]) == 64


def test_interim_estimate_never_hands_off_until_every_gate_passes():
    manifest = _manifest("estimate_manifest.json")
    accepted = pq.read_table(EXPERIMENT / "accepted_attribution.parquet")
    all_pass = all(gate["passed"] for gate in manifest["gates"])
    assert manifest["status"] == ("accepted" if all_pass else "interim_estimate_gates_not_met")
    assert accepted.num_rows == (1 if all_pass else 0)
    assert manifest["protocol_hash"] == _manifest("preregistered_estimands.json")["protocol_hash"]
    if manifest["treatment_week_status"] == "provisional":
        assert not all_pass
    estimates = pd.read_parquet(EXPERIMENT / "estimates.parquet")
    assert estimates.loc[0, "method"] == "augmented_scm"
    assert {"simplex_scm", "synthetic_did"} <= set(estimates["method"])
    placebos = pd.read_parquet(EXPERIMENT / "donor_placebos.parquet")
    assert len(placebos) == len(manifest["panel"]["base_donors"]) >= 9


def test_estimators_recover_a_known_effect_on_a_donor_mixture():
    rng = np.random.default_rng(7)
    weeks, donors, pre_weeks = 230, 11, 200
    factors = np.cumsum(rng.normal(size=(weeks, 3)), axis=0)
    panel = factors @ rng.uniform(0, 1, (donors, 3)).T + rng.normal(scale=0.5, size=(weeks, donors))
    target = panel[:, :3].mean(axis=1) + rng.normal(scale=0.3, size=weeks)
    pre = np.arange(weeks) < pre_weeks
    target[~pre] += 2.0
    y, x, _, sd = scm.standardize(target, panel, pre)
    multiplier, _ = scm.select_ridge_lambda(y, x, pre, [0.001, 0.01, 0.1, 1, 10], 26)
    for fit in (scm.fit_ascm(y, x, pre, multiplier), scm.fit_simplex(y, x, pre),
                scm.fit_sdid(y, x, pre, ~pre)):
        assert abs(fit.gap_z[~pre].mean() * sd - 2.0) < 0.5, fit.method
