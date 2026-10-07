import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def test_l1_gate_admits_only_sign_consistent_proxies():
    registry = pq.read_table(ROOT / "data/curated/proxy_registry.parquet").to_pylist()
    admitted = [row for row in registry if row["status"] == "admitted"]
    assert admitted, "expected admitted proxies once Trends is present"
    assert not any(row["status"] == "admitted" and (row["corr_levels"] or 0) < 0
                   and (row["corr_diff"] or 0) < 0 for row in registry)


def test_tier_a_composite_is_single_pca_index():
    manifest = json.loads((ROOT / "data/curated/index/composite_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "provisional_composite_built"
    assert manifest["pc1_variance_explained"] >= 0.5
    table = pq.read_table(ROOT / "data/curated/index/brand_index_composite_quarterly.parquet")
    assert table.num_rows == manifest["n_waves"] >= 3


def test_proxy_led_index_uses_validated_brand_trend_and_not_survey_pinning():
    manifest = json.loads((ROOT / "data/curated/index/search_salience_index_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "provisional_proxy_led_index_built"
    assert manifest["weekly_movement"].startswith("100% from the validated Lenovo")
    assert manifest["calibration"]["slope"] > 0
    assert manifest["calibration"]["n_quarters"] >= 8
    assert manifest["retained_inputs"]["headline_query"] == "brand_lenovo"
    assert manifest["calibration"]["correlation"] > 0
    assert "price_queries" in manifest["excluded_from_core_index"]
    rows = pq.read_table(ROOT / "data/curated/index/search_salience_index_weekly.parquet").to_pylist()
    assert len(rows) == 248
    assert str(rows[0]["week"]) == "2022-01-03"
    assert str(rows[-1]["week"]) == "2026-09-28"
    assert all(row["source_version"] == "v4_proxy_led_brand_calibrated" for row in rows)
    assert not any(row["anchored"] for row in rows)
    components = pq.read_table(
        ROOT / "data/curated/index/brand_index_components_weekly.parquet"
    )
    assert components.num_rows == len(rows)
    assert set(components.column_names) == {
        "week", "brand_salience_proxy_z", "product_portfolio_proxy_z",
        "commercial_intent_proxy_z",
    }


def test_proxy_led_index_has_mapping_uncertainty():
    rows = pq.read_table(ROOT / "data/curated/index/search_salience_index_weekly.parquet").to_pylist()
    assert min(row["index_se"] for row in rows) > 0
    assert max(row["index_level"] for row in rows) > min(row["index_level"] for row in rows)
