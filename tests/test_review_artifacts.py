"""Review artifacts must exist, be safe to open, and match the current production files (AGENTS.md)."""

import json
from pathlib import Path

import pytest

from srmp.review import REVIEW_DIR, ROOT, sha256, stamped_sources

NOTEBOOKS = sorted(REVIEW_DIR.glob("*.ipynb"))


def _cells(notebook: Path) -> list[dict]:
    return json.loads(notebook.read_text(encoding="utf-8"))["cells"]


def test_review_notebooks_exist():
    assert {path.name for path in NOTEBOOKS} >= {
        "00_data_inputs.ipynb", "05_brand_index.ipynb", "10_total_sponsorship_effect.ipynb", "15_exposure_and_survey_lift.ipynb", "35_financial_links.ipynb", "20_world_cup_close_up.ipynb",
        "30_cobrand_association.ipynb", "40_brand_value.ipynb",
    }


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_is_read_only_by_default_and_fully_executed(notebook):
    code = [cell for cell in _cells(notebook) if cell["cell_type"] == "code"]
    sources = ["".join(cell["source"]) for cell in code]
    assert any("RUN_REBUILD = False" in source for source in sources), "rebuild must be opt-in"
    assert all(cell.get("execution_count") for cell in code), "every code cell must be executed"
    errors = [out for cell in code for out in cell.get("outputs", []) if out.get("output_type") == "error"]
    assert not errors, "saved outputs contain an error"


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_outputs_match_current_production_files(notebook):
    stamped = stamped_sources(notebook)
    assert stamped, "notebook must call stamp_sources on the files it reads"
    changed = [path for path, digest in stamped.items() if not (ROOT / path).exists() or sha256(path) != digest]
    assert not changed, (f"{notebook.name} is stale: {changed} changed after it was executed. "
                         "Re-run it with `python -m srmp.review` (or label it stale per AGENTS.md).")


def test_every_experiment_has_a_review_artifact():
    artifacts = " ".join(path.read_text(encoding="utf-8") for path in REVIEW_DIR.iterdir()
                         if path.suffix in {".ipynb", ".md"})
    experiments = [path.stem for path in (ROOT / "srmp" / "experiments").glob("*.py")
                   if path.stem not in {"__init__", "world_cup_impact_v1_estimator"}]
    missing = [name for name in experiments if name not in artifacts]
    assert not missing, f"experiments without a review artifact: {missing}"
