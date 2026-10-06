"""Prospective World Cup impact protocol, data readiness and interim estimation."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import yaml

from srmp.experiments.world_cup_impact_v1_estimator import estimate_world_cup_impact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _coverage_end(table: pa.Table) -> str | None:
    for column in ("week", "date"):
        if column in table.column_names:
            values = [value for value in table.column(column).to_pylist() if value is not None]
            return str(max(values))[:10] if values else None
    return None


def _source_status(name: str, source: dict[str, Any],
                   milestones: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_path = source.get("path")
    if not raw_path:
        return {
            "source": name,
            "status": "waiting_for_path",
            "required_for_estimation": bool(source.get("required_for_estimation")),
            "note": source.get("note"),
        }
    path = Path(raw_path)
    if not path.exists():
        return {
            "source": name,
            "status": "path_configured_file_missing",
            "path": str(path),
            "required_for_estimation": bool(source.get("required_for_estimation")),
            "note": source.get("note"),
        }
    result = {
        "source": name,
        "status": "available_pending_coverage_check",
        "path": str(path),
        "sha256": _sha256(path),
        "required_for_estimation": bool(source.get("required_for_estimation")),
        "note": source.get("note"),
    }
    if path.suffix == ".parquet":
        table = pq.read_table(path)
        result["rows"] = table.num_rows
        result["columns"] = table.column_names
        result["coverage_end"] = _coverage_end(table)
    required = source.get("required_coverage_through")
    if required:
        through = (milestones or {}).get(required, required)
        result["required_coverage_through"] = str(through) if through else None
        # Week labels mark the week start, so a week covers six further days.
        if through and result.get("coverage_end"):
            covered = datetime.fromisoformat(result["coverage_end"]).date().toordinal() + 6
            if covered < datetime.fromisoformat(str(through)).date().toordinal():
                result["status"] = "available_coverage_incomplete"
    return result


def build_world_cup_skeleton(
    config_path: str = "config/experiments/world_cup_impact_v1.yaml",
    contract_path: str = "data/reference/world_cup_impact_data_contract.yaml",
    output_dir: str = "data/curated/experimental/world_cup_impact_v1",
) -> dict[str, Any]:
    config_file, contract_file = Path(config_path), Path(contract_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    contract = yaml.safe_load(contract_file.read_text(encoding="utf-8"))
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    milestones = config["milestones"]
    missing_dates = [name for name, value in milestones.items() if value is None]
    sources = [
        _source_status(name, source, config["milestones"])
        for name, source in config["data_sources"].items()
    ]
    required_missing = [
        item["source"] for item in sources
        if item["required_for_estimation"] and item["status"] != "available_pending_coverage_check"
    ]
    post_window_ready = not missing_dates
    ready = not required_missing and post_window_ready

    accepted_schema = pa.schema([
        ("estimate_id", pa.string()),
        ("treatment_window", pa.string()),
        ("delta_index_attrib", pa.float64()),
        ("lower_bound", pa.float64()),
        ("upper_bound", pa.float64()),
        ("pre_rmspe", pa.float64()),
        ("placebo_p_value", pa.float64()),
        ("accepted_for_valuation", pa.bool_()),
        ("assumptions_hash", pa.string()),
    ])
    empty = pa.Table.from_pylist([], schema=accepted_schema)
    pq.write_table(empty, target / "accepted_attribution.parquet")
    pacsv.write_csv(empty, target / "accepted_attribution.csv")

    protocol_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    estimands = {
        "experiment_id": config["experiment_id"],
        "role": config["role"],
        "protocol_hash": protocol_hash,
        "frozen_estimands": config["estimands"],
        "counterfactual_protocol": config["counterfactual"],
        "monetization_handoff": config["monetization_handoff"],
        "rule": "No accepted attribution row is emitted until incoming data satisfy the contract and the preregistered estimator passes all gates.",
    }
    (target / "preregistered_estimands.json").write_text(
        json.dumps(estimands, indent=2, default=str) + "\n", encoding="utf-8"
    )

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": "ready_to_estimate" if ready else "waiting_for_world_cup_data",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "role": "primary sponsorship impact evaluation; earlier announcement/FCWC SCM remains interim",
        "canonical_contracts_replaced": [],
        "config": {"path": str(config_file), "sha256": _sha256(config_file)},
        "data_contract": {"path": str(contract_file), "sha256": _sha256(contract_file), "id": contract["contract"]},
        "protocol_hash": protocol_hash,
        "missing_milestone_dates": missing_dates,
        "required_sources_waiting": required_missing,
        "source_readiness": sources,
        "accepted_attribution_rows": 0,
        "estimation_policy": {
            "post_outcome_tuning_prohibited": True,
            "minimum_credible_donors": config["counterfactual"]["minimum_credible_donors"],
            "validation_holdout_weeks": config["counterfactual"]["validation_holdout_weeks"],
            "minimum_post_weeks_after_tournament": config["counterfactual"]["minimum_post_weeks_after_tournament"],
            "maximum_placebo_p_value": config["counterfactual"]["maximum_placebo_p_value"],
        },
        "major_caveat": "The largest sponsorship impact may occur during the World Cup. Current 2024-announcement/FCWC estimates are interim and cannot close the sponsorship valuation.",
    }
    (target / "readiness_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiments/world_cup_impact_v1.yaml")
    parser.add_argument("--contract", default="data/reference/world_cup_impact_data_contract.yaml")
    parser.add_argument("--output-dir", default="data/curated/experimental/world_cup_impact_v1")
    parser.add_argument("--readiness-only", action="store_true")
    args = parser.parse_args()
    readiness = build_world_cup_skeleton(args.config, args.contract, args.output_dir)
    if not args.readiness_only:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        estimate_world_cup_impact(config, readiness["protocol_hash"], args.output_dir)
