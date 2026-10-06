"""Helpers for human-review notebooks (AGENTS.md).

Notebooks call ``stamp_sources`` on every production file they read. The
printed ``REVIEW_SOURCES=`` line records each file's hash in the saved
notebook, and ``tests/test_review_artifacts.py`` fails when a source has
changed since the notebook was last executed.

    python -m srmp.review                 # execute every review notebook in place
    python -m srmp.review 10_total_sponsorship_effect.ipynb
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = ROOT / "reports" / "methods_annex"
STAMP_PREFIX = "REVIEW_SOURCES="


TEXT_SUFFIXES = {".csv", ".json", ".yaml", ".yml", ".md", ".txt"}


def sha256(path: str | Path) -> str:
    """Content hash; text files are hashed with LF line endings so a git
    checkout that converts line endings does not make a notebook look stale."""
    full = ROOT / path
    data = full.read_bytes()
    if full.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def stamp_sources(paths: list[str]) -> pd.DataFrame:
    """Record the production files a notebook reads; print the machine-checked stamp."""
    rows = []
    for path in paths:
        full = ROOT / path
        generated = None
        if full.suffix == ".json":
            generated = json.loads(full.read_text(encoding="utf-8")).get("generated_at_utc")
        rows.append({"file": path, "sha256": sha256(path)[:12], "last_generated_utc": generated,
                     "size_kb": round(full.stat().st_size / 1024, 1)})
    print(STAMP_PREFIX + json.dumps({path: sha256(path) for path in paths}))
    print(f"Executed {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    return pd.DataFrame(rows)


def stamped_sources(notebook: Path) -> dict[str, str]:
    """Read the stamp back from a saved notebook's outputs."""
    content = json.loads(notebook.read_text(encoding="utf-8"))
    for cell in content["cells"]:
        for output in cell.get("outputs", []):
            text = output.get("text", "")
            text = "".join(text) if isinstance(text, list) else text
            for line in text.splitlines():
                if line.startswith(STAMP_PREFIX):
                    return json.loads(line[len(STAMP_PREFIX):])
    return {}


def execute(notebooks: list[Path], timeout: int = 900) -> None:
    import nbformat
    from nbclient import NotebookClient

    for path in notebooks:
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(notebook, timeout=timeout, kernel_name="python3",
                       resources={"metadata": {"path": str(ROOT)}}).execute()
        nbformat.write(notebook, path)
        print(f"executed {path.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="notebook file names; default all in reports/methods_annex")
    args = parser.parse_args()
    targets = [REVIEW_DIR / name for name in args.names] or sorted(REVIEW_DIR.glob("*.ipynb"))
    execute(targets)
