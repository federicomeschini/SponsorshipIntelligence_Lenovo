"""Shared contract identifiers and loud-failure helpers."""

CONTRACTS = {
    "index": "C-INDEX",
    "exposure": "C-EXPOSURE",
    "panel": "C-PANEL",
    "event_study": "C-EVENTSTUDY",
    "roi": "C-ROI",
}


class ContractViolation(ValueError):
    """Raised when an artifact violates a locked interface contract."""


def require_columns(columns: set[str], required: set[str], contract: str) -> None:
    """Fail loudly when a contract-required column is missing."""
    missing = sorted(required - columns)
    if missing:
        raise ContractViolation(f"{contract} violation: missing columns {missing}")
