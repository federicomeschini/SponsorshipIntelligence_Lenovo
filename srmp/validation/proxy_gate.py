"""L1 proxy validation gate (ARCHITECTURE §5.2).

Assembles the high-frequency Lenovo-brand proxies (Trends, Wikipedia, GDELT),
aggregates them to the survey's quarterly frequency, and correlates each against
the funnel-stage anchor in levels and first differences. Proxies clear the locked
gate when they track a stage strongly enough with a theory-consistent sign; the
best-matching stage is recorded as ``target_stage``.

The anchor here is the NON-CANONICAL constructed GWI anchor (ADR-0011), so the
registry is written with ``provisional: true`` and only the population funnel
stages GWI supplies (engagement, consideration) can be validated against.
Donor and property-outcome series are excluded (role separation, ADR-0010/0012).
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
import pyarrow.parquet as pq

from srmp.ingest._public import load_yaml

# Funnel stages that have a population anchor series (GWI). Crosstab stages
# (awareness/appeal/purchase_intent) are a sponsorship-lift companion, not an
# index anchor (ADR-0012), so they are not validation targets here.
ANCHORED_STAGES = ("engagement", "consideration")


def _weekly(dates: pd.Series) -> pd.Series:
    """Monday (W-MON) week-start for a series of dates."""
    d = pd.to_datetime(dates)
    return d - pd.to_timedelta(d.dt.weekday, unit="D")


def assemble_proxy_panel(
    trends_path: str = "data/curated/trends/trends_weekly_averaged.parquet",
    wikipedia_path: str = "data/staged/wikipedia/wikipedia_pageviews_daily.parquet",
    gdelt_path: str = "data/staged/gdelt/gdelt_brand_daily.parquet",
) -> pd.DataFrame:
    """Tidy weekly Lenovo-brand proxy panel: proxy_id, source, week, value."""
    frames: list[pd.DataFrame] = []

    trends = Path(trends_path)
    if trends.exists():
        table = pq.read_table(trends).to_pandas()
        # Keep only Lenovo funnel-outcome families; drop donors and property outcomes.
        table = table[~table["target_stage"].isin(["scm_donor", "property_outcome"])]
        for query_id, group in table.groupby("query_id"):
            frames.append(pd.DataFrame({
                "proxy_id": f"trends_{query_id}", "source": "trends",
                "week": _weekly(group["week"]), "value": group["interest_mean"].astype(float),
            }).dropna(subset=["value"]))

    wiki = Path(wikipedia_path)
    if wiki.exists():
        table = pq.read_table(wiki).to_pandas()
        table = table[table["entity_type"].isin(["treated_brand", "product_brand"])].copy()
        table["week"] = _weekly(table["date"])
        weekly = table.groupby(["proxy_id", "week"], as_index=False)["views"].sum()
        for proxy_id, group in weekly.groupby("proxy_id"):
            frames.append(pd.DataFrame({
                "proxy_id": f"wiki_{proxy_id}", "source": "wikipedia",
                "week": group["week"], "value": group["views"].astype(float),
            }))

    gdelt = Path(gdelt_path)
    if gdelt.exists():
        table = pq.read_table(gdelt).to_pandas()
        table["week"] = _weekly(table["date"])
        volume = table.groupby("week", as_index=False)["news_volume"].sum()
        frames.append(pd.DataFrame({"proxy_id": "gdelt_volume", "source": "gdelt",
                                    "week": volume["week"], "value": volume["news_volume"].astype(float)}))
        tone = table.groupby("week", as_index=False)["mean_tone"].mean()
        frames.append(pd.DataFrame({"proxy_id": "gdelt_tone", "source": "gdelt",
                                    "week": tone["week"], "value": tone["mean_tone"].astype(float)}))

    if not frames:
        raise FileNotFoundError("No proxy sources found to assemble the L1 panel.")
    return pd.concat(frames, ignore_index=True)


def _to_quarterly(panel: pd.DataFrame) -> pd.DataFrame:
    """Average each weekly proxy within its calendar quarter (quarter-start index)."""
    panel = panel.copy()
    period = pd.PeriodIndex(pd.to_datetime(panel["week"]), freq="Q")
    panel["quarter_start"] = period.start_time.normalize()
    quarterly = panel.groupby(["proxy_id", "source", "quarter_start"], as_index=False)["value"].mean()
    return quarterly


def _corr(a: np.ndarray, b: np.ndarray, method: str) -> float:
    if len(a) < 3:
        return float("nan")
    frame = pd.DataFrame({"a": a, "b": b})
    return float(frame["a"].corr(frame["b"], method=method))


def validate_proxies(anchor_path: str, output_path: str, config_path: str = "config/base.yaml",
                     **panel_paths: str) -> dict[str, Any]:
    """Run the §5.2 gate against the funnel anchor and write the proxy registry."""
    config = load_yaml(config_path)
    gate = config["validation_gate"]
    level_threshold = float(gate["corr_level_threshold"])
    diff_threshold = float(gate["corr_diff_threshold"])

    anchor = pq.read_table(anchor_path).to_pandas()
    anchor["quarter_start"] = pd.to_datetime(anchor["fieldwork_start"]).dt.normalize()
    stages = [stage for stage in ANCHORED_STAGES
              if stage in anchor.columns and anchor[stage].notna().any()]

    quarterly = _to_quarterly(assemble_proxy_panel(**panel_paths))
    decided_at = datetime.now(timezone.utc).isoformat()

    registry: list[dict[str, Any]] = []
    for (proxy_id, source), group in quarterly.groupby(["proxy_id", "source"]):
        merged = group.merge(anchor[["quarter_start", *stages]], on="quarter_start", how="inner")
        merged = merged.sort_values("quarter_start")
        # Every proxy here (salience, news volume, favourable tone) is expected to
        # move WITH the funnel stage, so admission requires a POSITIVE correlation
        # at the gate threshold (§5.2 "sign consistent with theory"). A strong
        # negative correlation is theory-inconsistent — flagged, never admitted.
        best: dict[str, Any] = {"stage": None, "corr_level": float("nan"),
                                "corr_diff": float("nan"), "signed_score": -2.0}
        strongest_abs = 0.0
        for stage in stages:
            paired = merged[["value", stage]].dropna()
            level = _corr(paired["value"].to_numpy(), paired[stage].to_numpy(), "pearson")
            diffs = paired.diff().dropna()
            diff = _corr(diffs["value"].to_numpy(), diffs[stage].to_numpy(), "pearson")
            for value in (level, diff):
                if pd.notna(value):
                    strongest_abs = max(strongest_abs, abs(value))
            signed = max(level if pd.notna(level) else -2.0, diff if pd.notna(diff) else -2.0)
            if signed > best["signed_score"]:
                best = {"stage": stage, "corr_level": level, "corr_diff": diff, "signed_score": signed}
        passes = ((pd.notna(best["corr_diff"]) and best["corr_diff"] >= diff_threshold)
                  or (pd.notna(best["corr_level"]) and best["corr_level"] >= level_threshold))
        near = best["signed_score"] >= min(diff_threshold, level_threshold) - 0.1
        wrong_sign = (not passes) and strongest_abs >= min(diff_threshold, level_threshold)
        status = ("admitted" if passes else
                  "rejected_wrong_sign" if wrong_sign else
                  "watchlist" if near else "rejected")
        registry.append({
            "proxy_id": proxy_id, "source": source, "target_stage": best["stage"],
            "corr_levels": round(best["corr_level"], 4) if pd.notna(best["corr_level"]) else None,
            "corr_diff": round(best["corr_diff"], 4) if pd.notna(best["corr_diff"]) else None,
            "n_quarters": int(merged.shape[0]), "status": status,
            "provisional": True, "decided_at": decided_at,
        })

    registry.sort(key=lambda row: (row["status"] != "admitted", row["proxy_id"]))
    schema = pa.schema([
        ("proxy_id", pa.string()), ("source", pa.string()), ("target_stage", pa.string()),
        ("corr_levels", pa.float64()), ("corr_diff", pa.float64()), ("n_quarters", pa.int64()),
        ("status", pa.string()), ("provisional", pa.bool_()), ("decided_at", pa.string()),
    ])
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(registry, schema=schema)
    pq.write_table(table, target)
    import pyarrow.csv as pacsv
    pacsv.write_csv(table, target.with_suffix(".csv"))

    summary = {
        "status": "provisional_gate_run_against_noncanonical_anchor",
        "generated_at_utc": decided_at, "anchor_path": anchor_path,
        "anchored_stages": stages, "thresholds": {"level": level_threshold, "diff": diff_threshold},
        "n_proxies": len(registry),
        "admitted": [r["proxy_id"] for r in registry if r["status"] == "admitted"],
        "watchlist": [r["proxy_id"] for r in registry if r["status"] == "watchlist"],
        "rejected": [r["proxy_id"] for r in registry if r["status"] == "rejected"],
        "rejected_wrong_sign": [r["proxy_id"] for r in registry if r["status"] == "rejected_wrong_sign"],
        "caveat": "Gate ran against the non-canonical GWI funnel anchor (ADR-0011); admission is "
                  "provisional until an approved analytical extract is supplied.",
    }
    (target.parent / "proxy_registry_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", default="data/staged/survey/brand_index_wave_anchor_constructed.parquet")
    parser.add_argument("--output", default="data/curated/proxy_registry.parquet")
    args = parser.parse_args()
    validate_proxies(args.anchor, args.output)
