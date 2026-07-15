"""Chart-builder entry points for V0–V7 dashboard views."""


def build_dashboard_view(view_id: str, curated_inputs: dict[str, str]) -> object:
    """Build a view from curated contracts without recomputing statistics."""
    raise NotImplementedError(f"Dashboard view {view_id} is not implemented yet")
