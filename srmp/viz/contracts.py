"""Dashboard input contracts; statistics are computed upstream only."""


def load_curated_contract(path: str, contract: str) -> object:
    """Load and validate a curated artifact before chart construction."""
    raise NotImplementedError(f"{contract} visualization contract loader is not implemented yet")
