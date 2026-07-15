import json
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/world_cup_impact_v1"


def test_world_cup_primary_evaluation_is_preregistered_and_waiting():
    manifest = json.loads(
        (EXPERIMENT / "readiness_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "waiting_for_world_cup_data"
    assert "primary sponsorship impact evaluation" in manifest["role"]
    assert manifest["canonical_contracts_replaced"] == []
    assert set(manifest["missing_milestone_dates"]) == {
        "activation_start", "tournament_start", "tournament_end",
        "primary_post_window_end",
    }
    assert set(manifest["required_sources_waiting"]) == {
        "world_cup_exposure", "world_cup_event_calendar",
    }
    readiness = {row["source"]: row["status"] for row in manifest["source_readiness"]}
    assert readiness["jointly_scaled_donor_trends"] == "available_pending_coverage_check"
    assert readiness["product_launch_controls"] == "available_pending_coverage_check"
    assert manifest["estimation_policy"]["minimum_credible_donors"] == 9
    assert manifest["estimation_policy"]["maximum_placebo_p_value"] == 0.10

    accepted = pq.read_table(EXPERIMENT / "accepted_attribution.parquet")
    assert accepted.num_rows == 0
    assert "accepted_for_valuation" in accepted.column_names


def test_world_cup_estimand_is_frozen_before_outcomes_arrive():
    protocol = json.loads(
        (EXPERIMENT / "preregistered_estimands.json").read_text(encoding="utf-8")
    )
    assert protocol["frozen_estimands"]["primary"]["name"] == (
        "sustained_world_cup_brand_index_uplift"
    )
    assert protocol["counterfactual_protocol"]["prohibit_post_outcome_tuning"] is True
    assert len(protocol["protocol_hash"]) == 64
