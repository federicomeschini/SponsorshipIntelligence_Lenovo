import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/world_cup_simulation_v1"


def test_world_cup_simulation_is_complete_but_never_accepted():
    manifest = json.loads(
        (EXPERIMENT / "simulation_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "simulation_only_incomplete_outcome_not_for_valuation"
    assert manifest["accepted_for_valuation"] is False
    assert manifest["canonical_contracts_replaced"] == []
    assert manifest["calendar"]["matches"] == 104
    assert manifest["counterfactual"]["calendar_matches_covered"] == 91
    assert manifest["counterfactual"]["calendar_match_coverage"] == 91 / 104
    assert len(manifest["scenario_results"]) == 3
    base = next(row for row in manifest["scenario_results"] if row["scenario"] == "base")
    assert base["exposure_weighted_gap_index_points"] < 0
    assert base["frozen_preannouncement_exposure_weighted_gap_index_points"] > 0


def test_simulated_exposure_is_unmistakably_labelled_and_calendar_is_official():
    exposure = pd.read_parquet(EXPERIMENT / "simulated_world_cup_exposure.parquet")
    assert exposure["is_simulated"].all()
    assert exposure["measurement_scope"].str.startswith("SIMULATED_").all()
    assert set(exposure["scenario"]) == {"low", "base", "high"}
    assert exposure.groupby("scenario")["week"].nunique().eq(6).all()
    calendar = pd.read_parquet(EXPERIMENT / "official_fifa_calendar.parquet")
    assert len(calendar) == 104
    assert calendar["match_number"].nunique() == 104
    assert calendar["status"].eq("official_fifa_api_snapshot").all()


def test_simulation_does_not_mutate_primary_world_cup_acceptance():
    primary = json.loads(
        (ROOT / "data/curated/experimental/world_cup_impact_v1/readiness_manifest.json")
        .read_text(encoding="utf-8")
    )
    assert primary["status"] == "waiting_for_world_cup_data"
    accepted = pd.read_parquet(
        ROOT / "data/curated/experimental/world_cup_impact_v1/accepted_attribution.parquet"
    )
    assert accepted.empty
