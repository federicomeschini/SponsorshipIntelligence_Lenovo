"""Common-anchor Google Trends panels for competitor-brand counterfactuals."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import requests
import yaml

from srmp.ingest.trends import _BROWSER_UA, _session_get, _strip_prefix


def _fetch_panel(
    session: requests.Session,
    items: list[dict[str, str]],
    start: str,
    end: str,
    raw_path: Path,
    delay: float,
    tries: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(items) > 5:
        raise ValueError("Google Trends comparison panels support at most five terms.")
    request = {
        "comparisonItem": [
            {"keyword": item["term"], "geo": "", "time": f"{start} {end}"}
            for item in items
        ],
        "category": 0,
        "property": "",
    }
    explore_url = "https://trends.google.com/trends/api/explore?" + urlencode({
        "hl": "en-US", "tz": "0", "req": json.dumps(request, separators=(",", ":")),
    })
    explore = _session_get(session, explore_url, tries=tries, base_delay=delay)
    http = {"explore_status": explore.status_code if explore else None}
    if not explore or explore.status_code != 200:
        return [], http
    widget = next(
        (value for value in _strip_prefix(explore.text)["widgets"] if value["id"] == "TIMESERIES"),
        None,
    )
    if widget is None:
        return [], {**http, "error": "no_timeseries_widget"}
    time.sleep(delay)
    data_url = "https://trends.google.com/trends/api/widgetdata/multiline?" + urlencode({
        "hl": "en-US", "tz": "0",
        "req": json.dumps(widget["request"], separators=(",", ":")),
        "token": widget["token"],
    })
    response = _session_get(session, data_url, tries=tries, base_delay=delay)
    http["multiline_status"] = response.status_code if response else None
    if not response or response.status_code != 200:
        return [], http
    raw_path.write_bytes(response.content)
    http["response_sha256"] = hashlib.sha256(response.content).hexdigest()
    return _parse_panel_response(response.content, items), http


def _parse_panel_response(content: bytes, items: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = content.decode("utf-8")
    for point in _strip_prefix(text)["default"]["timelineData"]:
        if point.get("isPartial"):
            continue
        week = datetime.fromtimestamp(int(point["time"]), tz=timezone.utc).date()
        values = point["value"]
        has_data = point.get("hasData", [True] * len(values))
        for index, item in enumerate(items):
            rows.append({
                "query_id": item["query_id"],
                "brand_id": item["brand_id"],
                "term": item["term"],
                "week": week,
                "interest_panel_scale": float(values[index]),
                "suppressed_below_one": not bool(has_data[index]),
            })
    return rows


def _rescale(draws: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    anchor_id = config["common_anchor"]["query_id"]
    reference_panel = config["panels"][0]["panel_id"]
    anchor = draws[
        draws["query_id"].eq(anchor_id) & draws["panel_id"].eq(reference_panel)
    ]
    reference = anchor.groupby("week")["interest_panel_scale"].median()
    minimum = int(config["acquisition"]["min_anchor_overlap_weeks"])
    scale_rows: list[dict[str, Any]] = []
    scaled_parts: list[pd.DataFrame] = []
    for (panel_id, draw), group in draws.groupby(["panel_id", "draw"], sort=False):
        panel_anchor = group[group["query_id"].eq(anchor_id)].set_index("week")["interest_panel_scale"]
        overlap = pd.concat([reference.rename("reference"), panel_anchor.rename("panel")], axis=1).dropna()
        overlap = overlap[(overlap["reference"] > 0) & (overlap["panel"] > 0)]
        if len(overlap) < minimum:
            raise ValueError(
                f"Common-anchor panel {panel_id} draw {draw} has only {len(overlap)} usable weeks."
            )
        factor = float(overlap["reference"].sum() / overlap["panel"].sum())
        part = group.copy()
        part["anchor_scale_factor"] = factor
        part["interest_common_scale_draw"] = part["interest_panel_scale"] * factor
        scaled_parts.append(part)
        scale_rows.append({
            "panel_id": panel_id,
            "draw": int(draw),
            "anchor_overlap_weeks": len(overlap),
            "anchor_scale_factor": factor,
        })
    return pd.concat(scaled_parts, ignore_index=True), pd.DataFrame(scale_rows)


def pull_joint_trends(
    config_path: str = "config/joint_trends_donors.yaml",
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    acquisition = config["acquisition"]
    raw_dir = Path(acquisition["raw_output_dir"])
    staged_dir = Path(acquisition["staged_output_dir"])
    curated_path = Path(acquisition["curated_output"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    staged_dir.mkdir(parents=True, exist_ok=True)
    curated_path.parent.mkdir(parents=True, exist_ok=True)
    end = str(config["horizon"].get("end") or date.today())
    # One raw folder per data vintage; the July 2026 vintage predates this
    # layout and sits directly in the raw output directory.
    (raw_dir / end).mkdir(parents=True, exist_ok=True)
    anchor = config["common_anchor"]
    draws_required = int(acquisition["draws_per_panel"])
    delay = float(acquisition["request_delay_seconds"])
    tries = int(acquisition["max_retries"])
    session = requests.Session()
    session.headers.update({"User-Agent": _BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
    session.get("https://trends.google.com/trends/explore", timeout=60)
    rows: list[dict[str, Any]] = []
    fetch_log: list[dict[str, Any]] = []
    for panel in config["panels"]:
        items = [anchor, *panel["queries"]]
        for draw in range(draws_required):
            raw_name = f"{panel['panel_id']}__draw{draw:02d}.json"
            raw_path = raw_dir / end / raw_name
            if raw_path.exists():
                content = raw_path.read_bytes()
                fetched = _parse_panel_response(content, items)
                http = {
                    "cached_raw_response": True,
                    "response_sha256": hashlib.sha256(content).hexdigest(),
                }
            else:
                fetched, http = _fetch_panel(
                    session, items, str(config["horizon"]["start"]), end,
                    raw_path, delay, tries,
                )
            for row in fetched:
                row.update({"panel_id": panel["panel_id"], "draw": draw})
            rows.extend(fetched)
            fetch_log.append({
                "panel_id": panel["panel_id"], "draw": draw,
                "status": "ok" if fetched else "failed", "rows": len(fetched), **http,
            })
            if not http.get("cached_raw_response"):
                time.sleep(delay)
    if not rows:
        raise RuntimeError("All common-anchor Google Trends panel requests failed.")
    failed = [row for row in fetch_log if row["status"] != "ok"]
    successful_by_panel = pd.DataFrame(fetch_log).query("status == 'ok'").groupby("panel_id").size()
    insufficient = {
        panel["panel_id"]: int(successful_by_panel.get(panel["panel_id"], 0))
        for panel in config["panels"]
        if int(successful_by_panel.get(panel["panel_id"], 0)) < max(5, draws_required // 2)
    }
    if insufficient:
        raise RuntimeError(f"Insufficient common-anchor draws by panel: {insufficient}")
    raw_frame = pd.DataFrame(rows)
    scaled, factors = _rescale(raw_frame, config)
    curated = scaled.groupby(
        ["panel_id", "query_id", "brand_id", "term", "week"], as_index=False
    ).agg(
        interest_common_scale=("interest_common_scale_draw", "mean"),
        interest_common_scale_sd=("interest_common_scale_draw", "std"),
        draws_used=("draw", "nunique"),
        suppressed_draws=("suppressed_below_one", "sum"),
    )
    curated["common_anchor_query"] = anchor["term"]
    curated = curated[[
        "panel_id", "common_anchor_query", "query_id", "brand_id", "term", "week",
        "interest_common_scale", "interest_common_scale_sd", "draws_used", "suppressed_draws",
    ]].sort_values(["panel_id", "query_id", "week"])
    pq.write_table(pa.Table.from_pandas(raw_frame, preserve_index=False), staged_dir / "panel_draws.parquet")
    pacsv.write_csv(pa.Table.from_pandas(factors, preserve_index=False), staged_dir / "anchor_scale_factors.csv")
    table = pa.Table.from_pandas(curated, preserve_index=False)
    pq.write_table(table, curated_path)
    pacsv.write_csv(table, curated_path.with_suffix(".csv"))
    with (raw_dir / "fetch_log.json").open("w", encoding="utf-8") as handle:
        json.dump(fetch_log, handle, indent=2)
        handle.write("\n")
    donor_rows = curated[~curated["query_id"].eq(anchor["query_id"])]
    manifest = {
        "source": "Google Trends common-anchor comparison panels",
        "status": "complete_joint_scale_panel" if not failed else "usable_incomplete_joint_scale_panel",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_file),
        "composition_id": config["composition_id"],
        "common_anchor": anchor,
        "panels": len(config["panels"]),
        "donor_queries": int(donor_rows["query_id"].nunique()),
        "draws_per_panel": draws_required,
        "successful_draws_by_panel": {
            panel["panel_id"]: int(successful_by_panel.get(panel["panel_id"], 0))
            for panel in config["panels"]
        },
        "failed_draws": failed,
        "weeks_min": int(donor_rows.groupby("query_id")["week"].nunique().min()),
        "weeks_max": int(donor_rows.groupby("query_id")["week"].nunique().max()),
        "curated_path": str(curated_path),
        "curated_sha256": hashlib.sha256(curated_path.read_bytes()).hexdigest(),
        "scaling_rule": "Each panel/draw is multiplicatively mapped to the median Lenovo anchor path in the first panel using positive overlapping weeks.",
        "limitations": [
            "Google Trends is sampled and rounded; repeated draws quantify request instability, not sampling independence.",
            "A common Lenovo anchor establishes cross-panel scale but does not make search constructs identical across brands.",
        ],
    }
    (staged_dir / "pull_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/joint_trends_donors.yaml")
    args = parser.parse_args()
    print(json.dumps(pull_joint_trends(args.config), indent=2))
