"""Validated piecewise-linear mapping from Brand Index to royalty rate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def derive_local_slope(
    schedule: list[dict[str, Any]],
    reference_index: float,
) -> dict[str, Any]:
    """Return the local royalty bps per Index point without extrapolation.

    Schedule rows use ``index_level`` and a decimal ``royalty_rate`` (for
    example, 0.025 for 2.5%). At least two approved points are required.
    """
    if len(schedule) < 2:
        return {
            "status": "blocked_insufficient_schedule_points",
            "required_points": 2,
            "available_points": len(schedule),
            "royalty_bps_per_index_point": None,
        }
    points = sorted(
        [(float(row["index_level"]), float(row["royalty_rate"])) for row in schedule]
    )
    index_levels = [point[0] for point in points]
    if len(set(index_levels)) != len(index_levels):
        raise ValueError("Royalty schedule contains duplicate Brand Index levels.")
    if any(rate < 0 for _, rate in points):
        raise ValueError("Royalty schedule contains a negative royalty rate.")
    if any(points[i + 1][1] < points[i][1] for i in range(len(points) - 1)):
        raise ValueError("Royalty schedule must be non-decreasing with Brand Index strength.")
    if reference_index < points[0][0] or reference_index > points[-1][0]:
        return {
            "status": "blocked_reference_outside_approved_range",
            "approved_index_range": [points[0][0], points[-1][0]],
            "reference_index": float(reference_index),
            "royalty_bps_per_index_point": None,
        }
    segment = None
    for lower, upper in zip(points[:-1], points[1:]):
        if lower[0] <= reference_index <= upper[0]:
            segment = (lower, upper)
            break
    if segment is None:
        raise ValueError("Royalty schedule could not locate the reference segment.")
    lower, upper = segment
    slope = 10_000.0 * (upper[1] - lower[1]) / (upper[0] - lower[0])
    return {
        "status": "royalty_slope_available",
        "reference_index": float(reference_index),
        "segment": {
            "lower_index": lower[0], "lower_royalty_rate": lower[1],
            "upper_index": upper[0], "upper_royalty_rate": upper[1],
        },
        "royalty_bps_per_index_point": float(slope),
    }


def resolve_royalty_schedule(path: str, reference_index: float | None) -> dict[str, Any]:
    """Load an approved schedule and resolve its local slope, or report the gate."""
    source = Path(path)
    if not source.exists():
        return {
            "status": "blocked_schedule_file_missing",
            "path": str(source),
            "royalty_bps_per_index_point": None,
        }
    document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if document.get("status") != "approved":
        return {
            "status": "blocked_schedule_not_approved",
            "path": str(source),
            "schedule_status": document.get("status", "missing"),
            "available_points": len(document.get("schedule", [])),
            "royalty_bps_per_index_point": None,
        }
    if reference_index is None:
        return {
            "status": "blocked_reference_index_missing",
            "path": str(source),
            "royalty_bps_per_index_point": None,
        }
    result = derive_local_slope(document.get("schedule", []), float(reference_index))
    return {"path": str(source), "schedule_version": document.get("version"), **result}
