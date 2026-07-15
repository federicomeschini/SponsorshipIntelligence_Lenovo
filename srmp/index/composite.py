"""L2 Tier A — quarterly funnel composite (single Brand Index value).

Aggregates the populated funnel-stage anchor into one quarterly index via PCA on
the standardized stages: the first principal component is the common brand-health
signal, oriented so higher = stronger and rescaled to a mean-100 / sd-15 index.

With only the two GWI population stages (engagement, consideration) available now,
PC1 is close to their standardized average; it becomes a genuine multi-stage PCA
once awareness/appeal/purchase_intent have population extracts. Built on the
NON-CANONICAL GWI anchor (ADR-0011/0013) — a provisional Brand Index, not the
client-approved one. Tier B (statespace) fuses the same anchor with the admitted
proxies into the weekly index on this composite's scale; chow_lin is the retained
single-indicator alternative.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from srmp.validation.proxy_gate import ANCHORED_STAGES


def build_funnel_composite(anchor_path: str, output_dir: str) -> dict[str, Any]:
    """PCA-aggregate the populated funnel stages into a quarterly Brand Index."""
    anchor = pq.read_table(anchor_path).to_pandas().sort_values("fieldwork_midpoint")
    stages = [s for s in ANCHORED_STAGES if s in anchor.columns and anchor[s].notna().any()]
    panel = anchor.dropna(subset=stages).reset_index(drop=True)
    if len(panel) < 3 or len(stages) < 1:
        raise ValueError("Composite needs >=3 waves and >=1 populated funnel stage.")

    raw = panel[stages].to_numpy(dtype=float)
    mean, sd = raw.mean(axis=0), raw.std(axis=0, ddof=0)
    standardized = (raw - mean) / sd

    if len(stages) == 1:
        loadings = np.array([1.0])
        scores = standardized[:, 0]
        variance_explained = 1.0
    else:
        # PCA on the correlation matrix (inputs already standardized).
        corr = np.corrcoef(standardized, rowvar=False)
        eigvals, eigvecs = np.linalg.eigh(corr)
        order = np.argsort(eigvals)[::-1]
        eigvals, eigvecs = eigvals[order], eigvecs[:, order]
        loadings = eigvecs[:, 0]
        # Orient so the component increases with the stages (positive loadings).
        if loadings.sum() < 0:
            loadings = -loadings
        scores = standardized @ loadings
        variance_explained = float(eigvals[0] / eigvals.sum())

    # Brand-index scale: mean 100, sd 15, higher = stronger brand.
    z = (scores - scores.mean()) / scores.std(ddof=0)
    index_level = 100.0 + 15.0 * z

    rows = [{
        "wave_id": panel.loc[i, "wave_id"],
        "fieldwork_midpoint": pd.Timestamp(panel.loc[i, "fieldwork_midpoint"]).date(),
        "composite_index": round(float(index_level[i]), 4),
        "composite_z": round(float(z[i]), 6),
        **{f"stage_{s}": round(float(panel.loc[i, s]), 6) for s in stages},
        "source_version": "tier_a_pca_provisional", "canonical_anchor_eligible": False,
    } for i in range(len(panel))]

    schema = pa.schema(
        [("wave_id", pa.string()), ("fieldwork_midpoint", pa.date32()),
         ("composite_index", pa.float64()), ("composite_z", pa.float64())]
        + [(f"stage_{s}", pa.float64()) for s in stages]
        + [("source_version", pa.string()), ("canonical_anchor_eligible", pa.bool_())])
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, target / "brand_index_composite_quarterly.parquet")
    pacsv.write_csv(table, target / "brand_index_composite_quarterly.csv")

    manifest = {
        "contract": "C-INDEX (Tier A quarterly composite)",
        "status": "provisional_composite_built",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "PCA(PC1) of standardized funnel stages, mean-100/sd-15 scale",
        "stages_used": stages, "n_waves": len(panel),
        "pc1_loadings": {s: round(float(loadings[i]), 4) for i, s in enumerate(stages)},
        "pc1_variance_explained": round(variance_explained, 4),
        "wave_span": [rows[0]["wave_id"], rows[-1]["wave_id"]],
        "caveat": "Provisional single Brand Index on the non-canonical GWI anchor (ADR-0011/0013); "
                  "with two stages PC1 approximates their standardized average.",
    }
    (target / "composite_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", default="data/staged/survey/brand_index_wave_anchor_constructed.parquet")
    parser.add_argument("--output-dir", default="data/curated/index")
    args = parser.parse_args()
    build_funnel_composite(args.anchor, args.output_dir)
