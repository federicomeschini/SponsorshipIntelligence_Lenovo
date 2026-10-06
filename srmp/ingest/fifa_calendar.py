"""Official FIFA World Cup 2026 match calendar, staged from FIFA's public API.

The raw snapshot is immutable; ``--refresh`` re-pulls it (for example after a
schedule change), otherwise the stored snapshot is re-staged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd
import yaml


def _description(values: list[dict[str, Any]] | None) -> str | None:
    return values[0].get("Description") if values else None


def fetch_calendar(config: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    raw_path = Path(config["raw_snapshot"])
    if raw_path.exists() and not refresh:
        return json.loads(raw_path.read_text(encoding="utf-8"))
    request = Request(config["api_url"], headers={"User-Agent": "SRMP-research-calendar/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def prepare_calendar(payload: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    expected = int(config["expected_matches"])
    selected = [
        row for row in payload.get("Results", [])
        if str(row.get("IdCompetition")) == str(config["competition_id"])
        and str(row.get("IdSeason")) == str(config["season_id"])
    ]
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} official World Cup matches, found {len(selected)}.")
    rows = [{
        "event_id": f"fwc26_match_{int(row['MatchNumber']):03d}",
        "event_type": "match",
        "event_timestamp_utc": row["Date"],
        "property_id": "fwc",
        "source": config["api_url"],
        "status": "official_fifa_api_snapshot",
        "match_number": int(row["MatchNumber"]),
        "stage": _description(row.get("StageName")),
        "home_team": (row.get("Home") or {}).get("Abbreviation"),
        "away_team": (row.get("Away") or {}).get("Abbreviation"),
        "stadium": _description((row.get("Stadium") or {}).get("Name")),
        "host_country": (row.get("Stadium") or {}).get("IdCountry"),
    } for row in selected]
    calendar = pd.DataFrame(rows)
    calendar["event_timestamp_utc"] = pd.to_datetime(calendar["event_timestamp_utc"], utc=True)
    calendar = calendar.sort_values(["event_timestamp_utc", "match_number"]).reset_index(drop=True)
    if calendar["match_number"].nunique() != expected:
        raise ValueError("Official calendar has duplicate or missing match numbers.")
    return calendar


def stage_calendar(config_path: str = "config/fifa_calendar.yaml", refresh: bool = False) -> dict[str, Any]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    calendar = prepare_calendar(fetch_calendar(config, refresh), config)
    target = Path(config["staged_output_dir"])
    target.mkdir(parents=True, exist_ok=True)
    out = calendar.copy()
    out["event_timestamp_utc"] = out["event_timestamp_utc"].astype(str)
    out.to_parquet(target / "official_fifa_calendar.parquet", index=False)
    out.to_csv(target / "official_fifa_calendar.csv", index=False)
    raw = Path(config["raw_snapshot"])
    manifest = {
        "source": config["api_url"], "source_page": config["source_page"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_snapshot": str(raw), "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "matches": int(len(calendar)),
        "first_match_utc": str(calendar["event_timestamp_utc"].min()),
        "final_match_utc": str(calendar["event_timestamp_utc"].max()),
    }
    (target / "pull_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/fifa_calendar.yaml")
    parser.add_argument("--refresh", action="store_true", help="re-pull the raw snapshot from the FIFA API")
    args = parser.parse_args()
    stage_calendar(args.config, args.refresh)
