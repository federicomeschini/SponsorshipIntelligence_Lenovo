"""Clearly labelled World Cup calendar/exposure simulation and interim SCM test."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import yaml

from srmp.experiments.sponsorship_counterfactual_v1 import (
    _donor_placebos,
    _fit_simplex,
    _monday,
    _rmspe,
    _weekly_event_controls,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_frame(frame: pd.DataFrame, target: Path, name: str) -> None:
    target.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(target / f"{name}.parquet", index=False)
    frame.to_csv(target / f"{name}.csv", index=False)


def _description(values: list[dict[str, Any]] | None) -> str | None:
    if not values:
        return None
    return values[0].get("Description")


def fetch_calendar(config: dict[str, Any], refresh: bool = False) -> dict[str, Any]:
    raw_path = Path(config["calendar"]["raw_snapshot"])
    if raw_path.exists() and not refresh:
        return json.loads(raw_path.read_text(encoding="utf-8"))
    request = Request(
        config["calendar"]["api_url"],
        headers={"User-Agent": "SRMP-research-calendar/1.0"},
    )
    with urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payload, indent=2) + chr(10), encoding="utf-8")
    return payload


def prepare_calendar(payload: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    expected = int(config["calendar"]["expected_matches"])
    matches = payload.get("Results", [])
    selected = [
        row for row in matches
        if str(row.get("IdCompetition")) == str(config["calendar"]["competition_id"])
        and str(row.get("IdSeason")) == str(config["calendar"]["season_id"])
    ]
    if len(selected) != expected:
        raise ValueError(f"Expected {expected} official World Cup matches, found {len(selected)}.")
    rows = []
    for row in selected:
        match_number = int(row["MatchNumber"])
        rows.append({
            "event_id": f"fwc26_match_{match_number:03d}",
            "event_type": "match",
            "event_timestamp_utc": row["Date"],
            "property_id": "fwc",
            "source": config["calendar"]["api_url"],
            "status": "official_fifa_api_snapshot",
            "match_number": match_number,
            "stage": _description(row.get("StageName")),
            "home_team": (row.get("Home") or {}).get("Abbreviation"),
            "away_team": (row.get("Away") or {}).get("Abbreviation"),
            "stadium": _description((row.get("Stadium") or {}).get("Name")),
            "host_country": (row.get("Stadium") or {}).get("IdCountry"),
        })
    calendar = pd.DataFrame(rows)
    calendar["event_timestamp_utc"] = pd.to_datetime(
        calendar["event_timestamp_utc"], utc=True
    )
    calendar = calendar.sort_values(["event_timestamp_utc", "match_number"]).reset_index(drop=True)
    if calendar["match_number"].nunique() != expected:
        raise ValueError("Official calendar has duplicate or missing match numbers.")
    return calendar


def simulate_exposure(
    calendar: pd.DataFrame,
    history: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    fifa_ids = set(config["simulation"]["fifa_property_ids"])
    hist = history[history["property_id"].isin(fifa_ids)].copy()
    hist["week"] = pd.to_datetime(hist["week"])
    weekly_hist = hist.groupby("week", as_index=False)[["impressions", "views"]].sum()
    positive = weekly_hist[weekly_hist["impressions"] > 0].copy()
    if positive.empty:
        raise ValueError("Historical FIFA-family Blinkfire has no positive exposure.")
    positive["view_rate"] = np.where(
        positive["impressions"] > 0,
        positive["views"] / positive["impressions"],
        np.nan,
    )
    calibrations = {
        "historical_p90": float(positive["impressions"].quantile(0.90)),
        "historical_max": float(positive["impressions"].max()),
        "historical_max_x_1_5": 1.5 * float(positive["impressions"].max()),
    }
    view_rate = float(positive["view_rate"].median())

    matches = calendar.copy()
    match_dates = matches["event_timestamp_utc"].dt.tz_convert(None).dt.normalize()
    matches["week"] = match_dates - pd.to_timedelta(match_dates.dt.weekday, unit="D")
    stage_weights = config["simulation"]["stage_weights"]
    matches["stage_weight"] = matches["stage"].map(stage_weights)
    if matches["stage_weight"].isna().any():
        missing = sorted(matches.loc[matches["stage_weight"].isna(), "stage"].unique())
        raise ValueError(f"Stage weights are missing for {missing}.")
    weekly = matches.groupby("week", as_index=False).agg(
        match_count=("event_id", "size"),
        stage_score=("stage_weight", "sum"),
        stages=("stage", lambda x: "|".join(sorted(set(x)))),
    )
    maximum_score = float(weekly["stage_score"].max())
    delta = float(config["simulation"]["adstock_delta"])
    rows: list[dict[str, Any]] = []
    for scenario, spec in config["simulation"]["scenarios"].items():
        peak = calibrations[spec["peak_calibration"]]
        floor = float(spec["floor_share"])
        simulated = weekly.copy()
        intensity = floor + (1.0 - floor) * simulated["stage_score"] / maximum_score
        simulated["impressions"] = peak * intensity
        simulated["views"] = simulated["impressions"] * view_rate
        adstock = []
        state = 0.0
        for value in simulated["impressions"]:
            state = float(value) + delta * state
            adstock.append(state)
        simulated["adstock_impressions"] = adstock
        simulated["scenario"] = scenario
        simulated["property_id"] = "fwc"
        simulated["days_observed"] = 7
        simulated["measurement_scope"] = (
            "SIMULATED_match_calendar_profile_calibrated_to_historical_Blinkfire"
        )
        simulated["is_simulated"] = True
        rows.extend(simulated.to_dict("records"))
    exposure = pd.DataFrame(rows).sort_values(["scenario", "week"]).reset_index(drop=True)
    calibration = {
        "historical_start": str(positive["week"].min().date()),
        "historical_end": str(positive["week"].max().date()),
        "positive_history_weeks": int(len(positive)),
        "historical_impressions_p90": calibrations["historical_p90"],
        "historical_impressions_max": calibrations["historical_max"],
        "historical_median_view_rate": view_rate,
        "stage_weights": stage_weights,
        "adstock_delta": delta,
        "warning": "All World Cup exposure rows are simulated scenarios, not Blinkfire observations.",
    }
    return exposure, calibration


def estimate_interim_gap(
    index: pd.DataFrame,
    trends: pd.DataFrame,
    exposure: pd.DataFrame,
    events: pd.DataFrame,
    frozen_preannouncement: pd.DataFrame,
    calendar: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    index = index.copy()
    trends = trends.copy()
    index["week"] = pd.to_datetime(index["week"])
    trends["week"] = _monday(trends["week"])
    donor_ids = config["donors"]["base"]
    donors = trends[trends["query_id"].isin(donor_ids)].pivot(
        index="week", columns="query_id", values="interest_common_scale"
    )
    panel = index.set_index("week").join(donors[donor_ids], how="inner").sort_index()
    treatment_week = pd.Timestamp(config["milestones"]["activation_start"])
    pre_mask = pd.Series(panel.index < treatment_week, index=panel.index)
    post_mask = pd.Series(panel.index >= treatment_week, index=panel.index)
    if int(post_mask.sum()) < 2:
        raise ValueError("At least two observed World Cup weeks are required for the simulation.")

    pre_dates = panel.index[pre_mask]
    holdout_weeks = int(config["donors"]["validation_holdout_weeks"])
    holdout_start = pre_dates[-holdout_weeks]
    train_mask = pd.Series(panel.index < holdout_start, index=panel.index)
    holdout_mask = pd.Series(
        (panel.index >= holdout_start) & (panel.index < treatment_week),
        index=panel.index,
    )
    train_fit = _fit_simplex(panel["index_level"], panel[donor_ids], train_mask)
    train_sd = float(panel.loc[train_mask, "index_level"].std(ddof=0))
    holdout_gap = (
        train_fit["target_z"] - train_fit["synthetic_z"]
    ) * train_sd
    holdout_rmspe = _rmspe(holdout_gap[holdout_mask])

    fit = _fit_simplex(panel["index_level"], panel[donor_ids], pre_mask)
    pre_mean = float(panel.loc[pre_mask, "index_level"].mean())
    pre_sd = float(panel.loc[pre_mask, "index_level"].std(ddof=0))
    panel["synthetic_no_world_cup_index"] = pre_mean + fit["synthetic_z"] * pre_sd
    panel["world_cup_gap_index_points"] = (
        fit["target_z"] - fit["synthetic_z"]
    ) * pre_sd
    panel["period"] = np.where(pre_mask, "pre_world_cup", "observed_world_cup")
    panel = panel.reset_index()

    weekly_controls = _weekly_event_controls(events, carryover_weeks=1)
    panel = panel.merge(weekly_controls.reset_index(), on="week", how="left")
    control_columns = [
        "product_campaign_control", "promotion_calendar_control", "mixed_event_control"
    ]
    panel[control_columns] = panel[control_columns].fillna(0.0)
    panel["known_lenovo_event_week"] = panel[control_columns].max(axis=1)

    pre_gap = panel.loc[panel["period"].eq("pre_world_cup"), "world_cup_gap_index_points"]
    post_gap = panel.loc[panel["period"].eq("observed_world_cup"), "world_cup_gap_index_points"]
    pre_rmspe = _rmspe(pre_gap)
    post_rmspe = _rmspe(post_gap)
    ratio = post_rmspe / pre_rmspe

    indexed = panel.set_index("week")
    donor_placebos = _donor_placebos(
        indexed[donor_ids],
        pd.Series(indexed.index < treatment_week, index=indexed.index),
        pd.Series(indexed.index >= treatment_week, index=indexed.index),
    )
    placebo_p = (
        1.0 + float((donor_placebos["post_pre_rmspe_ratio"] >= ratio).sum())
    ) / (1.0 + len(donor_placebos))

    observed = panel[panel["period"].eq("observed_world_cup")].copy()
    frozen_preannouncement = frozen_preannouncement.copy()
    frozen_preannouncement["week"] = pd.to_datetime(frozen_preannouncement["week"])
    frozen_gap = frozen_preannouncement[["week", "index_gap"]].rename(
        columns={"index_gap": "frozen_preannouncement_gap_index_points"}
    )
    scenario_rows = []
    for scenario, simulated in exposure.groupby("scenario"):
        joined = observed.merge(
            simulated[["week", "impressions", "adstock_impressions", "match_count", "stages"]],
            on="week", how="left",
        ).merge(frozen_gap, on="week", how="left")
        joined["adstock_impressions"] = joined["adstock_impressions"].fillna(0.0)
        denominator = float(joined["adstock_impressions"].sum())
        weighted = (
            float(
                np.average(
                    joined["world_cup_gap_index_points"],
                    weights=joined["adstock_impressions"],
                )
            )
            if denominator > 0 else np.nan
        )
        no_known_events = joined["known_lenovo_event_week"].eq(0)
        scenario_rows.append({
            "scenario": scenario,
            "observed_outcome_weeks": int(len(joined)),
            "simulated_impressions_observed_window": float(joined["impressions"].sum()),
            "exposure_weighted_gap_index_points": weighted,
            "frozen_preannouncement_exposure_weighted_gap_index_points": float(
                np.average(
                    joined["frozen_preannouncement_gap_index_points"],
                    weights=joined["adstock_impressions"],
                )
            ),
            "all_observed_world_cup_mean_gap": float(
                joined["world_cup_gap_index_points"].mean()
            ),
            "frozen_preannouncement_all_observed_mean_gap": float(
                joined["frozen_preannouncement_gap_index_points"].mean()
            ),
            "known_event_week_excluded_mean_gap": float(
                joined.loc[no_known_events, "world_cup_gap_index_points"].mean()
            ),
        })
    scenario_results = pd.DataFrame(scenario_rows)

    cutoff_label = pd.Timestamp(config["milestones"]["outcome_data_through"], tz="UTC")
    cutoff = cutoff_label + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    covered_matches = int((calendar["event_timestamp_utc"] <= cutoff).sum())
    metrics = {
        "method": "simplex_SCM_simulation_only",
        "treatment_week": str(treatment_week.date()),
        "observed_outcome_start": str(observed["week"].min().date()),
        "observed_outcome_end_label": str(observed["week"].max().date()),
        "underlying_outcome_data_through": str(cutoff_label.date()),
        "observed_outcome_weeks": int(len(observed)),
        "calendar_matches_covered": covered_matches,
        "calendar_matches_total": int(len(calendar)),
        "calendar_match_coverage": covered_matches / len(calendar),
        "training_weeks": int(train_mask.sum()),
        "validation_holdout_weeks": int(holdout_mask.sum()),
        "validation_holdout_rmspe_index_points": holdout_rmspe,
        "full_pre_rmspe_index_points": pre_rmspe,
        "observed_post_rmspe_index_points": post_rmspe,
        "post_pre_rmspe_ratio": ratio,
        "donor_placebo_p_value": placebo_p,
        "known_lenovo_control_event_weeks_in_observed_window": int(
            observed["known_lenovo_event_week"].sum()
        ),
        "weights": fit["weights"],
        "interpretation": {
            "incremental_world_cup": (
                "Lenovo excess over a synthetic path refitted through the week "
                "before the tournament; it estimates tournament lift above the "
                "existing sponsorship baseline."
            ),
            "total_sponsorship_path": (
                "Lenovo excess during World Cup weeks relative to the frozen "
                "pre-announcement no-FIFA-partnership path; it also contains all "
                "other Lenovo-specific post-announcement shocks."
            ),
            "acceptance": (
                "Exposure is simulated and the outcome window is incomplete, "
                "so neither quantity is an accepted FIFA effect."
            ),
        },
    }
    weights = pd.DataFrame(
        [{"query_id": key, "weight": value} for key, value in fit["weights"].items()]
    )
    return panel, weights, donor_placebos, {"metrics": metrics, "scenarios": scenario_results}


def build_simulation(
    config_path: str = "config/experiments/world_cup_simulation_v1.yaml",
    refresh_calendar: bool = False,
) -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    output = Path(config["outputs"]["directory"])
    payload = fetch_calendar(config, refresh=refresh_calendar)
    calendar = prepare_calendar(payload, config)
    history = pd.read_parquet(config["inputs"]["historical_blinkfire"])
    exposure, calibration = simulate_exposure(calendar, history, config)
    index = pd.read_parquet(config["inputs"]["brand_index"])
    trends = pd.read_parquet(config["inputs"]["joint_donor_trends"])
    events = pd.read_csv(config["inputs"]["product_campaign_events"])
    frozen_preannouncement = pd.read_parquet(
        config["inputs"]["frozen_preannouncement_counterfactual"]
    )
    panel, weights, placebos, result = estimate_interim_gap(
        index, trends, exposure, events, frozen_preannouncement, calendar, config
    )
    scenarios = result.pop("scenarios")

    calendar_out = calendar.copy()
    calendar_out["event_timestamp_utc"] = calendar_out["event_timestamp_utc"].astype(str)
    _write_frame(calendar_out, output, "official_fifa_calendar")
    _write_frame(exposure, output, "simulated_world_cup_exposure")
    _write_frame(panel, output, "interim_world_cup_counterfactual")
    _write_frame(weights, output, "scm_weights")
    _write_frame(placebos, output, "donor_placebos")
    _write_frame(scenarios, output, "simulation_scenarios")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": "simulation_only_incomplete_outcome_not_for_valuation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_contracts_replaced": [],
        "accepted_for_valuation": False,
        "calendar": {
            "source": config["calendar"]["api_url"],
            "source_page": config["calendar"]["source_page"],
            "raw_snapshot": config["calendar"]["raw_snapshot"],
            "raw_sha256": _sha256(Path(config["calendar"]["raw_snapshot"])),
            "matches": int(len(calendar)),
            "start": str(calendar["event_timestamp_utc"].min()),
            "end": str(calendar["event_timestamp_utc"].max()),
        },
        "exposure_calibration": calibration,
        "counterfactual": result["metrics"],
        "scenario_results": scenarios.to_dict("records"),
        "inputs": {
            name: {"path": path, "sha256": _sha256(Path(path))}
            for name, path in config["inputs"].items()
        },
        "simulation_guardrails": [
            "Every exposure row is marked is_simulated=true and uses a SIMULATED measurement scope.",
            "No simulated exposure enters canonical Blinkfire, Brand Index, or monetization artifacts.",
            "The current outcome covers 87.5 percent of scheduled matches and no 13-week persistence window.",
            "Current non-FIFA exposure after 2026-06-08 is unavailable and is not fabricated.",
            "A passing placebo would still not make this an accepted causal or monetary estimate.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "simulation_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + chr(10), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default="config/experiments/world_cup_simulation_v1.yaml"
    )
    parser.add_argument("--refresh-calendar", action="store_true")
    args = parser.parse_args()
    build_simulation(args.config, refresh_calendar=args.refresh_calendar)
