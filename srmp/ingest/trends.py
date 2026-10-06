"""D3 Google Trends acquisition with W-01 draw accounting.

Two backends produce the same draw-level schema:

* ``anonymous_web`` — automated pull of the public Trends endpoints. The raw
  ``/api/explore`` call rejects cookieless requests, so the client first visits
  the explore page to obtain the ``NID`` cookie (that page itself may return
  429 while still setting the cookie), then reads the widget token and fetches
  ``/api/widgetdata/multiline`` with bounded retry/back-off. Each draw is an
  independent request pair so that Google's per-request re-normalisation shows
  up as between-draw variance, exactly as separate UI exports would.
* ``manual_csv`` — audited UI exports dropped into the manual directory. When
  present these win, because a human curated them.

Both paths feed the shared ``trends_draws`` staging table and, when a complete
draw set exists, the ``trends_weekly_averaged`` curated series.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import requests

from srmp.ingest._public import load_yaml, write_json

_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _queries(config: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for family, family_config in config["families"].items():
        for query in family_config["queries"]:
            output.append({**query, "family": family, "target_stage": family_config["target_stage"]})
    return output


def _expected_files(config: dict[str, Any]) -> list[str]:
    draws = int(config["acquisition"]["draws_per_query"])
    return [f"{query['query_id']}__{geo['geo_id']}__draw{draw:02d}.csv"
            for query in _queries(config) for geo in config["geos"] for draw in range(1, draws + 1)]


def _parse_export(path: Path, query: dict[str, Any], geo: dict[str, Any], draw: int) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = next((index for index, line in enumerate(lines)
                         if line.startswith(("Day,", "Week,", "Month,"))), None)
    if header_index is None:
        raise ValueError(f"D3 Trends export violation: no time-series header in {path.name}")
    reader = csv.reader(lines[header_index:])
    header = next(reader)
    if len(header) != 2:
        raise ValueError(f"D3 Trends export violation: expected one query column in {path.name}")
    output = []
    for row in reader:
        if len(row) < 2 or not row[0].strip():
            continue
        raw = row[1].strip()
        suppressed = raw == "<1"
        interest = None if suppressed else float(raw)
        output.append(_row(query, geo, draw, date.fromisoformat(row[0].strip()),
                           interest, suppressed, path.name))
    return output


def _row(query: dict[str, Any], geo: dict[str, Any], draw: int, period: date,
         interest: float | None, suppressed: bool, source_file: str) -> dict[str, Any]:
    return {
        "query_id": query["query_id"], "term": query["term"], "family": query["family"],
        "target_stage": query["target_stage"], "property_id": query.get("property_id", ""),
        "geo_id": geo["geo_id"], "google_geo": geo["google_geo"], "draw": draw,
        "period": period, "interest": interest,
        "suppressed_below_one": suppressed, "source_file": source_file,
    }


# --- anonymous_web backend -------------------------------------------------

def _strip_prefix(text: str) -> Any:
    """Trends JSON responses are prefixed with an anti-hijack guard, e.g. )]}'."""
    return json.loads(text[text.find("{"):])


def _session_get(session: requests.Session, url: str, *, tries: int, base_delay: float) -> requests.Response | None:
    """GET reusing the cookie jar, backing off on 429 up to ``tries`` attempts."""
    last: requests.Response | None = None
    for attempt in range(tries):
        response = session.get(url, timeout=60)
        last = response
        if response.status_code == 200:
            return response
        # 429 or transient: linear back-off keyed to the polite request delay.
        time.sleep(base_delay * (attempt + 1))
    return last


def _fetch_series(session: requests.Session, term: str, google_geo: str,
                  start: str, end: str, *, delay: float, tries: int,
                  raw_path: Path) -> tuple[dict[date, tuple[float | None, bool]] | None, dict[str, Any]]:
    """Fetch one weekly interest-over-time series for a [start, end] window.

    Returns ``(points, http)`` where ``points`` maps each finished week to
    ``(interest, suppressed)``; ``interest`` is ``None`` on suppressed weeks.
    ``points`` is ``None`` when the window could not be retrieved. A raw
    response already persisted for this vintage is reused, never re-fetched.
    """
    if raw_path.exists():
        content = raw_path.read_bytes()
        return _parse_multiline(content.decode("utf-8")), {
            "cached_raw_response": True, "response_sha256": hashlib.sha256(content).hexdigest()}
    explore_params = {"hl": "en-US", "tz": "0", "req": json.dumps(
        {"comparisonItem": [{"keyword": term, "geo": google_geo, "time": f"{start} {end}"}],
         "category": 0, "property": ""}, separators=(",", ":"))}
    explore_url = "https://trends.google.com/trends/api/explore?" + urlencode(explore_params)
    explore = _session_get(session, explore_url, tries=tries, base_delay=delay)
    http = {"explore_status": explore.status_code if explore else None}
    if not explore or explore.status_code != 200:
        return None, http

    widgets = _strip_prefix(explore.text)["widgets"]
    timeseries = next((widget for widget in widgets if widget["id"] == "TIMESERIES"), None)
    if timeseries is None:
        http["error"] = "no_timeseries_widget"
        return None, http

    time.sleep(delay)
    data_params = {"hl": "en-US", "tz": "0",
                   "req": json.dumps(timeseries["request"], separators=(",", ":")),
                   "token": timeseries["token"]}
    data_url = "https://trends.google.com/trends/api/widgetdata/multiline?" + urlencode(data_params)
    data = _session_get(session, data_url, tries=tries, base_delay=delay)
    http["multiline_status"] = data.status_code if data else None
    if not data or data.status_code != 200:
        return None, http

    # Persist the raw response as an immutable provenance artifact.
    raw_path.write_bytes(data.content)
    http["response_sha256"] = hashlib.sha256(data.content).hexdigest()
    return _parse_multiline(data.text), http


def _parse_multiline(text: str) -> dict[date, tuple[float | None, bool]]:
    points: dict[date, tuple[float | None, bool]] = {}
    for point in _strip_prefix(text)["default"]["timelineData"]:
        if point.get("isPartial"):
            continue  # trailing incomplete week: excluded, matching finished-week exports
        period = datetime.fromtimestamp(int(point["time"]), tz=timezone.utc).date()
        suppressed = not bool(point.get("hasData", [True])[0])  # API equivalent of the UI "<1"
        points[period] = (None if suppressed else float(point["value"][0]), suppressed)
    return points


def _windows(start: date, end: date, sub_windows: int, fraction: float) -> list[tuple[date, date]]:
    """Overlapping weekly sub-windows tiling [start, end].

    Each is ``fraction`` of the horizon span long (floored so Trends still
    returns weekly resolution), stepped so ``sub_windows`` of them span the
    horizon with the last ending exactly at ``end``.
    """
    span = (end - start).days
    length = min(1800, max(365, int(span * fraction)))
    if sub_windows <= 1 or length >= span:
        return [(start, end)]
    step = (span - length) / (sub_windows - 1)
    windows = []
    for index in range(sub_windows):
        window_start = start + timedelta(days=round(index * step))
        windows.append((window_start, min(end, window_start + timedelta(days=length))))
    windows[-1] = (windows[-1][0], end)
    return windows


def _overlap_factor(reference: dict[date, tuple[float | None, bool]],
                    window: dict[date, tuple[float | None, bool]],
                    min_overlap: int) -> tuple[float | None, int]:
    """Overlap-ratio rescaling factor mapping ``window`` onto ``reference`` (W-01).

    Uses weeks present and unsuppressed in both, with a positive window value.
    The factor is the ratio of summed reference to summed window interest over
    that overlap; ``None`` when the overlap is too thin to be trusted.
    """
    ref_sum = win_sum = 0.0
    used = 0
    for period, (win_value, win_suppressed) in window.items():
        ref = reference.get(period)
        if ref is None or win_suppressed or win_value is None or win_value <= 0:
            continue
        ref_value, ref_suppressed = ref
        if ref_suppressed or ref_value is None:
            continue
        ref_sum += ref_value
        win_sum += win_value
        used += 1
    if used < min_overlap or win_sum <= 0:
        return None, used
    return ref_sum / win_sum, used


def _pull_anonymous(config: dict[str, Any], raw_dir: Path, end: str) -> tuple[list[dict], list[dict]]:
    """Fetch, overlap-ratio rescale, and stack every query x geo draw window."""
    acquisition = config["acquisition"]
    draws = int(acquisition["draws_per_query"])
    delay = float(acquisition.get("request_delay_seconds", 8))
    tries = int(acquisition.get("max_retries", 6))
    fraction = float(acquisition.get("window_fraction", 0.34))
    min_overlap = int(acquisition.get("min_overlap_weeks", 12))
    start = str(config["horizon"]["start"])
    start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    raw_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": _BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
    # One handshake seeds the NID cookie for the whole run.
    session.get("https://trends.google.com/trends/explore", timeout=60)
    time.sleep(delay)

    # Draw 0 is the full-horizon reference; the rest tile the span and are
    # rescaled onto it so the stacked draws share one 0-100 normalisation.
    windows = [(start_date, end_date)] + _windows(start_date, end_date, draws - 1, fraction)

    rows: list[dict[str, Any]] = []
    fetch_log: list[dict[str, Any]] = []
    for query in _queries(config):
        for geo in config["geos"]:
            reference: dict[date, tuple[float | None, bool]] | None = None
            for draw, (window_start, window_end) in enumerate(windows):
                raw_name = f"{query['query_id']}__{geo['geo_id']}__draw{draw:02d}.json"
                points, http = _fetch_series(session, query["term"], geo["google_geo"],
                                             window_start.isoformat(), window_end.isoformat(),
                                             delay=delay, tries=tries, raw_path=raw_dir / raw_name)
                factor: float | None = 1.0
                overlap = None
                status = "ok" if points else "failed"
                if points and draw == 0:
                    reference = points
                elif points and reference is not None:
                    factor, overlap = _overlap_factor(reference, points, min_overlap)
                    if factor is None:
                        status = "unrescalable_thin_overlap"
                elif points:  # reference itself failed: cannot place this window on scale
                    factor, status = None, "no_reference"
                if points and factor is not None:
                    for period, (value, suppressed) in points.items():
                        rows.append({
                            "query_id": query["query_id"], "term": query["term"],
                            "family": query["family"], "target_stage": query["target_stage"],
                            "property_id": query.get("property_id", ""), "geo_id": geo["geo_id"],
                            "google_geo": geo["google_geo"], "draw": draw,
                            "window_start": window_start, "window_end": window_end,
                            "scale_factor": round(factor, 6), "period": period,
                            "interest": None if suppressed else round(value * factor, 4),
                            "suppressed_below_one": suppressed, "source_file": raw_name,
                        })
                fetch_log.append({
                    "query_id": query["query_id"], "geo_id": geo["geo_id"], "draw": draw,
                    "window_start": window_start.isoformat(), "window_end": window_end.isoformat(),
                    "weeks": len(points) if points else 0, "overlap_weeks": overlap,
                    "scale_factor": round(factor, 6) if factor is not None else None,
                    "status": status,
                    **{key: http.get(key) for key in ("explore_status", "multiline_status", "error")},
                })
                if not http.get("cached_raw_response"):
                    time.sleep(delay)
    return rows, fetch_log


def _probe_anonymous(query: str, start: str, end: str) -> dict[str, Any]:
    payload = {"comparisonItem": [{"keyword": query, "geo": "", "time": f"{start} {end}"}],
               "category": 0, "property": ""}
    url = "https://trends.google.com/trends/api/explore?" + urlencode({
        "hl": "en-US", "tz": "0", "req": json.dumps(payload, separators=(",", ":")),
    })
    response = requests.get(url, timeout=45, headers={"User-Agent": _BROWSER_UA})
    return {"url": url, "status_code": response.status_code,
            "response_sha256": hashlib.sha256(response.content).hexdigest(),
            "content_type": response.headers.get("content-type", "")}


def _write_curated(config: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    curated_dir = Path(config["acquisition"]["curated_output_dir"])
    curated_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row["query_id"], row["term"], row["family"], row["target_stage"],
               row["property_id"], row["geo_id"], row["period"])
        grouped.setdefault(key, []).append(row)
    averaged = []
    for key, draw_rows in grouped.items():
        values = [row["interest"] for row in draw_rows if row["interest"] is not None]
        averaged.append({
            "query_id": key[0], "term": key[1], "family": key[2], "target_stage": key[3],
            "property_id": key[4], "geo_id": key[5], "week": key[6],
            "interest_mean": statistics.mean(values) if values else None,
            "interest_sd": statistics.stdev(values) if len(values) > 1 else None,
            "draws_used": len(draw_rows),
            "suppressed_draws": sum(row["suppressed_below_one"] for row in draw_rows),
        })
    averaged.sort(key=lambda row: (row["query_id"], row["geo_id"], row["week"]))
    averaged_table = pa.Table.from_pylist(averaged)
    pacsv.write_csv(averaged_table, curated_dir / "trends_weekly_averaged.csv")
    pq.write_table(averaged_table, curated_dir / "trends_weekly_averaged.parquet")


def pull_trends(config_path: str, output_dir: str, manifest_path: str,
                backend: str = "auto") -> None:
    """Acquire D3 Trends draws.

    ``backend``: ``manual`` uses only audited UI exports; ``anonymous`` forces
    the automated web pull; ``auto`` (default) prefers manual exports when
    present and otherwise runs the anonymous pull. ``probe`` only checks
    anonymous reachability without ingesting.
    """
    config = load_yaml(config_path)
    raw_dir = Path(output_dir)
    manual_dir = Path(config["acquisition"]["manual_export_dir"])
    staged_dir = Path(config["acquisition"]["staged_output_dir"])
    expected = _expected_files(config)
    manual_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    manual_csvs = sorted(path.name for path in manual_dir.glob("*.csv")) if manual_dir.exists() else []
    # Only strictly-named draw exports count; stray/default-named files are ignored
    # here and reported in the manifest so they never block the automated backend.
    available = [name for name in manual_csvs if name in set(expected)]
    ignored_manual = sorted(set(manual_csvs) - set(available))

    end = str(config["horizon"].get("end") or date.today())
    query_map = {query["query_id"]: query for query in _queries(config)}
    geo_map = {geo["geo_id"]: geo for geo in config["geos"]}

    rows: list[dict[str, Any]] = []
    fetch_log: list[dict[str, Any]] = []
    probe = None
    use_manual = backend == "manual" or (backend == "auto" and available)
    use_anonymous = backend == "anonymous" or (backend == "auto" and not available)

    if backend == "manual" and ignored_manual:
        raise ValueError(f"D3 Trends export violation: unexpected files {ignored_manual}")

    if use_manual:
        backend_used = "manual_csv"
        for filename in available:
            query_id, geo_id, draw_text = filename.removesuffix(".csv").split("__")
            rows.extend(_parse_export(manual_dir / filename, query_map[query_id],
                                      geo_map[geo_id], int(draw_text[4:])))
        fetched = set(available)
    elif backend == "probe":
        backend_used = "probe"
        try:
            probe = _probe_anonymous(_queries(config)[0]["term"], str(config["horizon"]["start"]), end)
        except requests.RequestException as exc:
            probe = {"status_code": None, "error": type(exc).__name__, "message": str(exc)}
        fetched = set()
    elif use_anonymous:
        backend_used = "anonymous_web"
        # One raw folder per data vintage keeps earlier pulls immutable; the
        # July 2026 vintage predates this layout and sits directly in anonymous/.
        rows, fetch_log = _pull_anonymous(config, raw_dir / "anonymous" / end, end)
        fetched = set(available)
    else:
        backend_used = "none"
        fetched = set(available)

    # Manual-export queue keeps the UI fallback ready regardless of backend; a
    # draw is "available" only when its audited UI CSV is physically present.
    queue_rows = []
    for query in _queries(config):
        for geo in config["geos"]:
            params = {"date": f"{config['horizon']['start']} {end}", "q": query["term"]}
            if geo["google_geo"]:
                params["geo"] = geo["google_geo"]
            for draw in range(1, int(config["acquisition"]["draws_per_query"]) + 1):
                filename = f"{query['query_id']}__{geo['geo_id']}__draw{draw:02d}.csv"
                queue_rows.append({
                    "query_id": query["query_id"], "family": query["family"], "term": query["term"],
                    "geo_id": geo["geo_id"], "draw": draw, "export_filename": filename,
                    "status": "available" if filename in available else "missing",
                    "explore_url": "https://trends.google.com/trends/explore?" + urlencode(params),
                })
    with (raw_dir / "manual_export_queue.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(queue_rows[0]))
        writer.writeheader()
        writer.writerows(queue_rows)

    if fetch_log:
        with (raw_dir / "fetch_log.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fetch_log[0]))
            writer.writeheader()
            writer.writerows(fetch_log)

    staged_dir.mkdir(parents=True, exist_ok=True)
    if rows:
        table = pa.Table.from_pylist(rows)
        pacsv.write_csv(table, staged_dir / "trends_draws.csv")
        pq.write_table(table, staged_dir / "trends_draws.parquet")

    units = {(query["query_id"], geo["geo_id"])
             for query in _queries(config) for geo in config["geos"]}
    if backend_used == "anonymous_web":
        draws_ok = sum(1 for entry in fetch_log if entry["status"] == "ok")
        with_reference = {(entry["query_id"], entry["geo_id"]) for entry in fetch_log
                          if entry["draw"] == 0 and entry["status"] == "ok"}
        missing = [f"{entry['query_id']}__{entry['geo_id']}__draw{entry['draw']:02d}"
                   for entry in fetch_log if entry["status"] != "ok"]
        if not rows:
            status = "blocked_anonymous_all_draws_failed_manual_exports_required"
        elif not missing and with_reference == units:
            status = "complete_draw_set"
        else:  # every referenced unit is still on a common scale; some windows dropped
            status = "incomplete_draw_set"
    else:
        missing = sorted(set(expected) - fetched)
        status = "complete_draw_set" if not missing else "incomplete_draw_set"
    # A per-unit reference is enough to place its weeks on one scale, so curate
    # whatever units carry a reference draw even when some windows were dropped.
    if rows:
        _write_curated(config, rows)

    manifest = {
        "source": "Google Trends", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path, "composition_id": config["composition_id"],
        "backend": backend_used, "status": status,
        "workaround": "W-01 overlap-ratio rescaled draw windows (weekly)",
        "queries": len(_queries(config)), "geos": len(config["geos"]),
        "draws_required_per_query": config["acquisition"]["draws_per_query"],
        "expected_export_count": len(expected), "available_export_count": len(fetched),
        "fetched_draws_ok": sum(1 for entry in fetch_log if entry["status"] == "ok") if fetch_log else None,
        "fetched_draws_failed": sum(1 for entry in fetch_log if entry["status"] != "ok") if fetch_log else None,
        "missing_exports": missing, "ignored_manual_files": ignored_manual,
        "anonymous_probe": probe,
        "official_api_status": "closed_alpha_credentials_not_configured",
        "manual_export_instructions": "Export one-query Interest over time CSVs from the Google Trends UI using the configured worldwide geo and exact query text; save with the expected filenames.",
    }
    write_json(manifest_path, manifest)
    write_json(staged_dir / "pull_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/queries_trends.yaml")
    parser.add_argument("--output-dir", default="data/raw/trends")
    parser.add_argument("--manifest", default="data/raw/trends/pull_manifest.json")
    parser.add_argument("--backend", default="auto", choices=["auto", "manual", "anonymous", "probe"])
    args = parser.parse_args()
    pull_trends(args.config, args.output_dir, args.manifest, backend=args.backend)
