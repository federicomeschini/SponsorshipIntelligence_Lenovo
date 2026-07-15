"""Small shared helpers for reproducible public-API pulls."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import requests
import yaml


USER_AGENT = "SRMP/0.1 (OpenEconomics sponsorship research)"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return value


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def get_json(url: str, *, retries: int = 4, timeout: int = 60) -> tuple[bytes, Any]:
    """GET JSON with bounded retry for rate limits and transient failures."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            if response.status_code == 429:
                time.sleep(max(6, 6 * (attempt + 1)))
                continue
            response.raise_for_status()
            return response.content, response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Public API pull failed after {retries} attempts: {url}") from last_error


def read_or_pull_json(path: Path, url: str) -> tuple[bytes, Any, bool]:
    """Reuse immutable raw data when present; otherwise perform and persist a pull."""
    if path.exists():
        content = path.read_bytes()
        return content, json.loads(content), True
    content, payload = get_json(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return content, payload, False


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
