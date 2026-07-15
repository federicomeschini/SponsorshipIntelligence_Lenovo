import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from srmp.experiments.sponsorship_monetization_v1 import calculate_valuation
from srmp.roi.royalty_schedule import derive_local_slope


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "data/curated/experimental/sponsorship_monetization_v1"


def test_experimental_bridge_is_isolated_and_truthfully_blocked():
    manifest = json.loads((EXPERIMENT / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "attribution_bridge_built_valuation_blocked"
    assert manifest["canonical_contracts_replaced"] == []
    assert set(manifest["inputs"]) == {"exposure", "survey_lift", "brand_index"}
    assert all(len(item["sha256"]) == 64 for item in manifest["inputs"].values())
    assert manifest["outputs"]["model_eligible_panel_rows"] == 5
    assert manifest["outputs"]["monetization_rows"] == 0
    assert manifest["counterfactual_gate"]["status"] == "candidate_passes_experimental_screen"
    assert manifest["counterfactual_gate"]["donor_placebo_p_value"] == 1 / 12
    assert manifest["counterfactual_gate"]["used_for_valuation"] is False
    assert manifest["royalty_schedule_gate"]["status"] == "blocked_schedule_not_approved"
    assert set(manifest["valuation_gate"]["missing_inputs"]) == {
        "delta_index_attrib", "royalty_bps_per_index_point",
        "brand_attributable_revenue", "sponsorship_fee", "discount_rate",
        "persistence_years",
    }

    panel = pq.read_table(EXPERIMENT / "funnel_lift_exposure_panel.parquet").to_pandas()
    assert len(panel) == 7
    assert "awareness_lift" not in panel.columns
    assert not panel["is_causal_effect"].any()
    assert panel.loc[panel["scale_version"].eq("2024_0_10"), "model_eligible"].eq(False).all()

    allocation = pq.read_table(
        EXPERIMENT / "property_allocation_scenario.parquet"
    ).to_pandas()
    assert set(allocation["property_id"]) == {"fwc", "fwwc", "fcwc"}
    assert abs(float(allocation["allocation_share"].sum()) - 1.0) < 1e-12
    assert allocation["allocation_role"].eq("scenario_only_not_causal_attribution").all()


def test_valuation_engine_runs_only_with_complete_explicit_assumptions():
    allocation = pd.DataFrame({
        "property_id": ["fwc", "fcwc"],
        "allocation_share": [0.4, 0.6],
    })
    assumptions = {
        "scenario_id": "test",
        "delta_index_attrib": 2.0,
        "royalty_bps_per_index_point": 3.0,
        "brand_attributable_revenue": 1_000_000.0,
        "sponsorship_fee": 50_000.0,
        "discount_rate": 0.10,
        "persistence_years": 2,
    }
    rows, missing = calculate_valuation(assumptions, allocation, "test-hash")
    assert missing == []
    assert list(rows["property_id"]) == ["TOTAL", "fwc", "fcwc"]
    assert rows.iloc[0]["delta_royalty_bps"] == 6.0
    assert abs(rows.iloc[1:]["incremental_value"].sum() - rows.iloc[0]["incremental_value"]) < 1e-9


def test_piecewise_royalty_schedule_returns_local_bps_slope():
    result = derive_local_slope([
        {"index_level": 80, "royalty_rate": 0.01},
        {"index_level": 100, "royalty_rate": 0.03},
        {"index_level": 120, "royalty_rate": 0.04},
    ], reference_index=90)
    assert result["status"] == "royalty_slope_available"
    assert abs(result["royalty_bps_per_index_point"] - 10.0) < 1e-12
