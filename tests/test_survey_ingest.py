import csv
import json
from pathlib import Path


def test_client_survey_staging_artifacts_are_complete_and_traceable():
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "data/staged/survey"
    manifest = json.loads((output_dir / "pull_manifest.json").read_text(encoding="utf-8"))

    statuses = {item["source_file"]: item["status"] for item in manifest["sources"]}
    assert statuses["lenovo_fifa_consumer_research_export_2026-05-21.xlsx"] == "usable_crosstab_export"
    assert statuses["lenovo_gwi_core_tech_brands_crosstab_export_2026-06-09.xlsx"] == "usable_gwi_crosstab_export"
    assert manifest["output_row_counts"]["consumer_research_tables"] == 21
    assert manifest["output_row_counts"]["consumer_research_wave_register"] == 7
    assert manifest["output_row_counts"]["gwi_core_tech_brands_crosstab"] == 570
    assert manifest["output_row_counts"]["gwi_lenovo_proxy_candidates"] == 74
    assert manifest["validation"]["status"] == "passed"
    gwi_check = manifest["validation"]["gwi_foglio1_duplicate_check"]
    assert gwi_check == [{
        "authoritative_sheet": "Foglio1",
        "duplicate_check_sheet": "Blank",
        "duplicate_check_range": "Blank!B13:AP29",
        "cells_compared": 697,
        "status": "passed_exact_match",
        "quarterly_periods_excluding_totals": 37,
        "candidate_proxy_series": 2,
    }]

    rows = list(csv.DictReader((output_dir / "consumer_research_crosstabs.csv").open(encoding="utf-8")))
    assert len(rows) == 340
    assert {row["source_sha256"] for row in rows} == {
        "3c7a066bc263806231cd89e8a04669035bb12bd7903cdd9d0c463cf03104e333"
    }
    net_rows = [row for row in rows if row["response_label"] == "NET" and row["statistic"] == "Column %"]
    assert len(net_rows) == 28
    assert all(float(row["value"]) == 1 for row in net_rows)

    gwi_rows = list(csv.DictReader((output_dir / "gwi_lenovo_proxy_candidates.csv").open(encoding="utf-8")))
    assert len(gwi_rows) == 74
    assert {row["source_sheet"] for row in gwi_rows} == {"Foglio1"}
    assert {row["proxy_construct"] for row in gwi_rows} == {"engagement", "consideration"}
    assert {row["admission_status"] for row in gwi_rows} == {"candidate_requires_l1_validation"}
