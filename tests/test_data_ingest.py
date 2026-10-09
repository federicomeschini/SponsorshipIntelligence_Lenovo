import csv
import json
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]


def test_segmented_survey_metrics_are_explicitly_noncanonical():
    staged = ROOT / "data/staged/survey"
    status = json.loads((staged / "anchor_status.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((staged / "segmented_perception_wave_metrics.csv").open(encoding="utf-8")))
    assert status["status"] == "blocked_missing_approved_wave_anchor"
    assert status["canonical_anchor_created"] is False
    assert len(rows) == 42
    assert {row["property_id"] for row in rows} == {"fwc", "fwwc", "fcwc"}
    assert {row["canonical_anchor_eligible"] for row in rows} == {"false"}


def test_constructed_wave_anchor_is_funnel_based_and_noncanonical():
    staged = ROOT / "data/staged/survey"
    status = json.loads((staged / "constructed_anchor_status.json").read_text(encoding="utf-8"))
    table = pq.read_table(staged / "brand_index_wave_anchor_constructed.parquet")
    assert status["status"] == "constructed_noncanonical_anchor_available"
    assert status["canonical_anchor_created"] is False
    # Funnel replaces pillars (ADR-0011); GWI populates engagement + consideration only.
    assert status["funnel_stages"] == ["awareness", "engagement", "appeal", "consideration", "purchase_intent"]
    assert status["populated_stages"] == ["engagement", "consideration"]
    assert status["deviations_from_contract"]
    assert table.num_rows == 37  # GWI quarterly waves Q1 2017 - Q1 2026
    assert set(table.column_names) >= set(status["funnel_stages"])
    assert not any(table.column("canonical_anchor_eligible").to_pylist())
    # The unpopulated funnel stages are genuinely null, not fabricated.
    assert table.column("awareness").null_count == 37


def test_complete_available_blinkfire_export_is_reconciled_and_normalized():
    staged = ROOT / "data/staged/blinkfire"
    manifest = json.loads((staged / "pull_manifest.json").read_text(encoding="utf-8"))
    table = pq.read_table(staged / "blinkfire_exposure_daily.parquet")
    assert manifest["status"] == "complete_client_scope"
    assert manifest["total_row_validation"] == "passed"
    # Base export (Oct 2024 - 11 Jun 2026), the pre-deal export (Jan - Sep 2024), the World Cup export
    # (11 Jun - 20 Jul 2026, replacing 11 Jun) and the post-tournament export (21 Jul - 30 Sep 2026).
    assert manifest["dated_rows"] == 619 + 274 + 40 - 1 + 72
    assert [len(item["overlapping_dates_replaced"]) for item in manifest["exports"]] == [0, 0, 1, 0]
    assert all(item["total_row_validation"] == "passed" for item in manifest["exports"])
    assert (manifest["date_min"], manifest["date_max"]) == ("2024-01-01", "2026-09-30")
    assert manifest["properties"] == 13
    assert table.num_rows == manifest["dated_rows"] * 13
    assert table.column_names == ["date", "property_id", "source_label", "impressions", "views"]
    weekly = pq.read_table(staged / "blinkfire_exposure_weekly.parquet")
    weekly_manifest = json.loads((staged / "weekly_manifest.json").read_text(encoding="utf-8"))
    assert weekly.num_rows == weekly_manifest["row_count"] == 13 * len({row.as_py() for row in weekly.column("week")})
    assert weekly_manifest["contract_status"] == "not_C_EXPOSURE_until_adstock_is_added"


def test_trends_anonymous_backend_produced_complete_curated_draw_set():
    raw = ROOT / "data/raw/trends"
    manifest = json.loads((raw / "pull_manifest.json").read_text(encoding="utf-8"))
    queue = list(csv.DictReader((raw / "manual_export_queue.csv").open(encoding="utf-8")))
    assert manifest["backend"] == "anonymous_web"
    # A complete OR near-complete draw set is acceptable: the sparsest co-brand
    # queries (e.g. Club World Cup) can have windows with nothing to rescale.
    assert manifest["status"] in ("complete_draw_set", "incomplete_draw_set")
    # 17 queries (ADR-0010): brand 1, category 5, co-branded 5, SCM donor 6.
    assert manifest["queries"] == 17
    assert manifest["draws_required_per_query"] == 10
    # W-01: 17 queries x 10 overlap-ratio rescaled draw windows; allow a few
    # dropped windows on the sparsest queries, but the bulk must succeed.
    assert manifest["fetched_draws_ok"] >= 153  # >= 90% of 170
    # The audited manual-export queue remains available as the documented fallback.
    assert len(queue) == 170
    assert len({row["export_filename"] for row in queue}) == 170
    curated = pq.read_table(ROOT / "data/curated/trends/trends_weekly_averaged.parquet")
    query_ids = {q for q in curated.column("query_id").to_pylist()}
    # Every query still yields a curated series (its full-horizon reference draw).
    assert len(query_ids) == 17
    # The SCM donor pool (O-05) must be present and separable from Lenovo outcomes.
    assert {"donor_dell", "donor_asus", "donor_hp", "donor_samsung"} <= query_ids
    # The rescaled draws must yield a genuine (non-degenerate) instability spread.
    sds = [s for s in curated.column("interest_sd").to_pylist() if s is not None]
    assert max(sds) > 0.0


def test_gdelt_volume_and_tone_pull_is_complete_and_audited():
    raw = ROOT / "data/raw/gdelt"
    staged = ROOT / "data/staged/gdelt"
    manifest = json.loads((raw / "pull_manifest.json").read_text(encoding="utf-8"))
    table = pq.read_table(staged / "gdelt_brand_daily.parquet")
    assert manifest["status"] == "doc_api_complete"
    # October 2026 refresh: 2022-01-01 to 2026-10-05.
    assert table.num_rows == manifest["row_count"] == 1707
    assert manifest["calendar_day_count"] == 1739
    assert manifest["missing_calendar_day_count"] == 32
    assert all(pull["status_code"] == 200 for pull in manifest["pulls"])
    assert (raw / "gdelt_bigquery_fallback.sql").exists()
