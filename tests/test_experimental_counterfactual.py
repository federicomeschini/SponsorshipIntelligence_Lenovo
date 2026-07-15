import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/sponsorship_counterfactual_v1"


def test_scm_candidate_uses_joint_panel_and_passes_interim_placebo_screen():
    manifest = json.loads(
        (EXPERIMENT / "counterfactual_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "candidate_passes_experimental_screen"
    assert manifest["canonical_contracts_replaced"] == []
    assert manifest["diagnostics"]["pre_fit_pass"] is True
    assert manifest["diagnostics"]["placebo_pass"] is True
    assert manifest["diagnostics"]["donor_placebo_p_value"] <= 0.1
    assert manifest["diagnostics"]["timing_coherence_support"] == "not_supported"
    assert manifest["candidate_attribution"]["exposure_weighted_delta_index"] > 0

    weights = pq.read_table(EXPERIMENT / "scm_weights.parquet").to_pandas()
    assert set(weights["query_id"]) == {
        "donor_dell", "donor_asus", "donor_acer", "donor_hp",
        "donor_microsoft_surface", "donor_razer", "donor_logitech",
        "donor_macbook", "donor_corsair", "donor_steelseries", "donor_benq",
    }
    assert abs(float(weights["weight"].sum()) - 1.0) < 1e-9
    weekly = pq.read_table(EXPERIMENT / "counterfactual_weekly.parquet").to_pandas()
    assert len(weekly) == 236
    assert set(weekly["period"]) == {"pre", "post"}


def test_blinkfire_is_downstream_treatment_and_control_not_a_donor():
    manifest = json.loads(
        (EXPERIMENT / "counterfactual_manifest.json").read_text(encoding="utf-8")
    )
    roles = manifest["counterfactual_roles"]
    assert "competitor-brand" in roles["donors"]
    assert "excluded from donor weights" in roles["blinkfire"]
    assert set(manifest["exposure_controls"]["fifa_property_ids"]) == {
        "fcwc", "fifa", "fifae", "fifaewc", "fwc", "fwwc", "infantino",
    }
    assert set(manifest["exposure_controls"]["nonfifa_property_ids"]) == {
        "carolina_hurricanes", "ducati", "f1", "montreal_canadiens",
        "motogp", "ny_yankees",
    }

    weekly = pq.read_table(EXPERIMENT / "counterfactual_weekly.parquet").to_pandas()
    exposure = pd.read_parquet(
        ROOT / "data/curated/experimental/sponsorship_monetization_v1/exposure_adstock_weekly.parquet"
    )
    assert abs(
        float(weekly["fifa_adstock"].sum() + weekly["nonfifa_adstock"].sum())
        - float(exposure["adstock_impressions"].sum())
    ) < 1e-3

    regression = json.loads(
        (EXPERIMENT / "exposure_control_regression.json").read_text(encoding="utf-8")
    )
    assert regression["status"] == "descriptive_association_not_causal"
    assert regression["observations"] == 89
    assert set(regression["coefficients"]) == {
        "intercept", "fifa_log_adstock_z", "nonfifa_log_adstock_z", "linear_time_z",
        "product_campaign_control", "promotion_calendar_control", "mixed_event_control",
    }


def test_joint_panel_and_donor_quality_screen_are_complete():
    joint_manifest = json.loads(
        (ROOT / "data/staged/trends_joint_donors/pull_manifest.json").read_text(encoding="utf-8")
    )
    assert joint_manifest["status"] == "complete_joint_scale_panel"
    assert joint_manifest["panels"] == 6
    assert joint_manifest["donor_queries"] == 21
    assert all(value == 10 for value in joint_manifest["successful_draws_by_panel"].values())

    quality = pq.read_table(EXPERIMENT / "donor_quality_screen.parquet").to_pandas()
    registry = pd.read_csv(ROOT / "data/reference/counterfactual_donor_registry.csv")
    assert (registry["inclusion_policy"].eq("base")).sum() >= 9
    assert set(registry.loc[registry["inclusion_policy"].eq("excluded"), "query_id"]) >= {
        "donor_samsung", "donor_lg_gram",
    }
    assert set(quality.loc[quality["inclusion_policy"].eq("data_quality_excluded"), "query_id"]) >= {
        "donor_gigabyte", "donor_fujitsu", "donor_toshiba", "donor_framework",
        "donor_vaio", "donor_aoc_monitor",
    }


def test_property_synthetic_artifact_is_retired_from_brand_counterfactual():
    path = ROOT / "data/curated/experimental/fifa_property_synthetic_v1/experiment_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["status"] == "retired_as_brand_counterfactual_mechanism_only"
    assert manifest["permitted_use"] == "mechanism_diagnostic_only"
    assert "Brand Index points" in manifest["outcome"]["not"]
