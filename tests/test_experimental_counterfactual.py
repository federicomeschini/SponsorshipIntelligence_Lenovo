import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/sponsorship_counterfactual_v1"


def test_scm_candidate_uses_joint_panel_and_screen_status_follows_placebo_rule():
    manifest = json.loads(
        (EXPERIMENT / "counterfactual_manifest.json").read_text(encoding="utf-8")
    )
    diagnostics = manifest["diagnostics"]
    passes = diagnostics["pre_fit_pass"] and diagnostics["placebo_pass"]
    assert manifest["status"] == (
        "candidate_passes_experimental_screen" if passes else "candidate_not_distinguishable"
    )
    assert diagnostics["placebo_pass"] == (diagnostics["donor_placebo_p_value"] <= 0.1)
    assert manifest["canonical_contracts_replaced"] == []
    assert diagnostics["pre_fit_pass"] is True
    # October 2026 refresh (ADR-0027): p rose from 1/12 to 2/12, so the
    # announcement candidate no longer passes the interim screen.
    assert manifest["status"] == "candidate_not_distinguishable"
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
    assert len(weekly) == 248
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
    assert regression["observations"] == 95
    assert set(regression["coefficients"]) == {
        "intercept", "fifa_log_adstock_z", "nonfifa_log_adstock_z", "linear_time_z",
        "product_campaign_control", "promotion_calendar_control", "mixed_event_control",
    }


def test_joint_panel_and_donor_quality_screen_are_complete():
    joint_manifest = json.loads(
        (ROOT / "data/staged/trends_joint_donors/pull_manifest.json").read_text(encoding="utf-8")
    )
    assert joint_manifest["status"] in {"complete_joint_scale_panel", "usable_incomplete_joint_scale_panel"}
    # 6 screened panels (ADR-0021) plus 4 candidate panels (ADR-0035).
    assert joint_manifest["panels"] == 10
    assert joint_manifest["donor_queries"] == 37
    # Connector rule: a panel needs at least half its draws (minimum five).
    assert all(value >= 9 for value in joint_manifest["successful_draws_by_panel"].values())

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


SELECTION = ROOT / "data/curated/experimental/announcement_design_selection_v1"


def test_design_is_selected_on_pre_period_only_and_before_estimation():
    record = json.loads((SELECTION / "selection_record.json").read_text(encoding="utf-8"))
    assert record["post_period_outcomes_accessed"] is False
    assert pd.Timestamp(record["data_weeks_seen"][1]) < pd.Timestamp("2024-10-21")
    table = pq.read_table(SELECTION / "selection_table.parquet").to_pandas()
    best = table.sort_values("oos_rmspe_index_points").iloc[0]
    assert (best["method"], best["donor_pool"]) == (record["selected_method"], record["selected_pool"])
    manifest = json.loads((SELECTION / "estimate_manifest.json").read_text(encoding="utf-8"))
    primary = manifest["primary"]
    assert (primary["method"], primary["donor_pool"]) == (record["selected_method"], record["selected_pool"])
    # Primary inference is the unchanged v1 rule; only the design was re-selected.
    assert (primary["statistic"], primary["placebo_filter"], primary["window"]) == ("rmspe_ratio", "none", "all_post")
    assert manifest["passes_primary_test"] == (primary["p_value"] <= 0.10)


def test_phase_a_cannot_see_post_period_rows():
    import yaml
    from srmp.experiments import announcement_design_selection_v1 as module
    config = yaml.safe_load((ROOT / "config/experiments/announcement_design_selection_v1.yaml").read_text(encoding="utf-8"))
    panel, groups = module._load_panel(config)
    pre = panel[panel.index < pd.Timestamp(config["treatment"]["first_full_post_week"])]
    poisoned = pre.copy()
    selection = module.select_design(poisoned, groups, config)
    record = json.loads((SELECTION / "selection_record.json").read_text(encoding="utf-8"))
    assert selection["selected_method"] == record["selected_method"]
    assert selection["pre_period_end"] == record["data_weeks_seen"][1]


def test_expanded_donor_selection_excludes_pre_period_constant_series():
    record = json.loads((ROOT / "data/curated/experimental/announcement_design_selection_v2/selection_record.json")
                        .read_text(encoding="utf-8"))
    assert record["post_period_outcomes_accessed"] is False
    assert "donor_western_digital" not in record["selected_donors"]
    registry = pd.read_csv(ROOT / "data/reference/counterfactual_donor_registry.csv")
    assert registry.loc[registry["query_id"].eq("donor_western_digital"), "inclusion_policy"].item() == "data_quality_excluded"
    assert (registry["inclusion_policy"].eq("candidate_base")).sum() == 15


def test_cobrand_placebo_test_ranks_lenovo_against_non_sponsors():
    manifest = json.loads((ROOT / "data/curated/experimental/cobrand_placebo_v1/cobrand_placebo_manifest.json")
                          .read_text(encoding="utf-8"))
    tests = pd.DataFrame(manifest["tests"])
    assert set(tests["construct"]) == {"fifa", "world_cup"}
    assert (tests["placebos"] >= 11).all()
    assert ((tests["p_value"] > 0) & (tests["p_value"] <= 1)).all()
    assert (tests["significant"] == (tests["p_value"] <= 0.10)).all()
