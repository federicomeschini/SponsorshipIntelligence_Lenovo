"""L3 geometric adstock transformation."""

from collections.abc import Iterable


def geometric_adstock(values: Iterable[float], delta: float) -> list[float]:
    """Return A_t = x_t + delta * A_(t-1), with locked parameter bounds."""
    if not 0 < delta < 1:
        raise ValueError("L3 adstock violation: delta must be strictly between 0 and 1")
    carry = 0.0
    result: list[float] = []
    for value in values:
        carry = float(value) + delta * carry
        result.append(carry)
    return result

