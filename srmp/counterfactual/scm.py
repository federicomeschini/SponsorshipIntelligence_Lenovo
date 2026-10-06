"""L6 synthetic-control estimators on a single treated unit.

All estimators work in pre-treatment z-units: the treated series and every
donor are standardized with pre-treatment moments only, so nothing observed
after treatment can influence scaling, weights or penalties. Callers convert
gaps back to their display scale with the treated unit's pre-treatment sd.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize


def standardize(
    target: np.ndarray, donors: np.ndarray, pre: np.ndarray
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Return target z, donor z (T x J), and the target pre mean and sd."""
    target = np.asarray(target, dtype=float)
    donors = np.asarray(donors, dtype=float)
    y_mean, y_sd = float(target[pre].mean()), float(target[pre].std())
    x_mean, x_sd = donors[pre].mean(axis=0), donors[pre].std(axis=0)
    if y_sd <= 0 or (x_sd <= 0).any():
        raise ValueError("L6 SCM violation: zero-variance pre-treatment series.")
    return (target - y_mean) / y_sd, (donors - x_mean) / x_sd, y_mean, y_sd


def _simplex_least_squares(
    a: np.ndarray, b: np.ndarray, penalty: float = 0.0
) -> np.ndarray:
    """Minimize ||b - a w||^2 + penalty ||w||^2 over the probability simplex."""
    n = a.shape[1]
    gram, cross = a.T @ a, a.T @ b

    def objective(weights: np.ndarray) -> float:
        residual = b - a @ weights
        return float(residual @ residual + penalty * weights @ weights)

    def gradient(weights: np.ndarray) -> np.ndarray:
        return 2.0 * (gram @ weights - cross + penalty * weights)

    starts = [np.repeat(1.0 / n, n)]
    if n <= 40:
        starts.extend(np.eye(n))
    best: tuple[float, np.ndarray] | None = None
    for start in starts:
        result = minimize(
            objective, x0=start, jac=gradient, method="SLSQP",
            bounds=[(0.0, 1.0)] * n,
            constraints={"type": "eq", "fun": lambda w: w.sum() - 1.0,
                         "jac": lambda w: np.ones_like(w)},
            options={"ftol": 1e-12, "maxiter": 3000},
        )
        weights = np.clip(np.asarray(result.x, dtype=float), 0.0, None)
        if not np.isfinite(weights).all() or weights.sum() <= 0:
            continue
        weights /= weights.sum()
        value = objective(weights)
        if best is None or value < best[0]:
            best = (value, weights)
    if best is None:
        raise ValueError("L6 SCM violation: no feasible simplex solution.")
    return best[1]


def simplex_weights(y_pre: np.ndarray, x_pre: np.ndarray) -> np.ndarray:
    """Abadie-style non-negative, sum-to-one donor weights."""
    return _simplex_least_squares(x_pre, y_pre)


def ridge_augmented_weights(
    w: np.ndarray, y_pre: np.ndarray, x_pre: np.ndarray, lam: float
) -> np.ndarray:
    """Ridge augmentation of SCM weights (Ben-Michael, Feller and Rothstein 2021).

    gamma = w + (X0 X0' + lam I)^-1 X0 (X1 - X0' w), with donors as rows of X0.
    As lam grows the correction vanishes and gamma returns to the SCM weights.
    """
    x0 = x_pre.T  # J x T0
    imbalance = y_pre - x_pre @ w
    correction = np.linalg.solve(x0 @ x0.T + lam * np.eye(x0.shape[0]), x0 @ imbalance)
    return w + correction


@dataclass
class Fit:
    method: str
    synthetic_z: np.ndarray
    gap_z: np.ndarray
    weights: np.ndarray
    details: dict = field(default_factory=dict)


def fit_simplex(y: np.ndarray, x: np.ndarray, pre: np.ndarray) -> Fit:
    w = simplex_weights(y[pre], x[pre])
    synthetic = x @ w
    return Fit("simplex_scm", synthetic, y - synthetic, w)


def select_ridge_lambda(
    y: np.ndarray, x: np.ndarray, train: np.ndarray, multipliers: list[float], inner_weeks: int
) -> tuple[float, list[dict]]:
    """Pick the ridge penalty on an inner pre-period split; post data never enter."""
    train_index = np.flatnonzero(train)
    if len(train_index) <= inner_weeks + 26:
        raise ValueError("L6 ASCM violation: training window too short for inner validation.")
    inner_fit = np.zeros_like(train)
    inner_fit[train_index[:-inner_weeks]] = True
    inner_eval = np.zeros_like(train)
    inner_eval[train_index[-inner_weeks:]] = True
    w = simplex_weights(y[inner_fit], x[inner_fit])
    scale = float(inner_fit.sum())
    rows = []
    for multiplier in multipliers:
        lam = multiplier * scale
        gamma = ridge_augmented_weights(w, y[inner_fit], x[inner_fit], lam)
        error = y[inner_eval] - x[inner_eval] @ gamma
        rows.append({"multiplier": multiplier, "lambda": lam,
                     "inner_rmspe_z": float(np.sqrt(np.mean(error ** 2)))})
    best = min(rows, key=lambda row: (row["inner_rmspe_z"], -row["multiplier"]))
    return best["multiplier"], rows


def fit_ascm(y: np.ndarray, x: np.ndarray, pre: np.ndarray, multiplier: float) -> Fit:
    w = simplex_weights(y[pre], x[pre])
    lam = multiplier * float(pre.sum())
    gamma = ridge_augmented_weights(w, y[pre], x[pre], lam)
    synthetic = x @ gamma
    return Fit("augmented_scm", synthetic, y - synthetic, gamma,
               {"scm_weights": w, "ridge_lambda": lam, "ridge_multiplier": multiplier})


def fit_sdid(y: np.ndarray, x: np.ndarray, pre: np.ndarray, post: np.ndarray) -> Fit:
    """Synthetic difference-in-differences (Arkhangelsky et al. 2021), one treated unit.

    Unit weights carry a free intercept and the paper's ridge penalty
    zeta^2 * T0 with zeta = (T_post)^(1/4) * sd(first differences of donors);
    time weights balance donor pre-periods to their post-period mean. The
    weekly gap is the doubly-differenced path, so its post mean is the SDID
    average effect.
    """
    t0, t1 = int(pre.sum()), int(post.sum())
    if t1 < 1:
        raise ValueError("L6 SDID violation: at least one post period is required.")
    x_pre, y_pre = x[pre], y[pre]
    sigma = float(np.std(np.diff(x_pre, axis=0), ddof=1))
    zeta = (t1 ** 0.25) * sigma
    omega = _simplex_least_squares(
        x_pre - x_pre.mean(axis=0), y_pre - y_pre.mean(), penalty=zeta ** 2 * t0
    )
    # Time weights: donors are the observations (J x T0); the common
    # intercept is concentrated out by demeaning across donors.
    donor_post_mean = x[post].mean(axis=0)
    a = x_pre.T - x_pre.T.mean(axis=0, keepdims=True)
    b = donor_post_mean - donor_post_mean.mean()
    lambda_time = _simplex_least_squares(a, b, penalty=(1e-6 * sigma) ** 2 * x.shape[1])
    treated_baseline = float(lambda_time @ y_pre)
    donor_baseline = x_pre.T @ lambda_time  # J
    gap = (y - treated_baseline) - (x - donor_baseline) @ omega
    synthetic = y - gap
    return Fit("synthetic_did", synthetic, gap, omega,
               {"time_weights": lambda_time, "zeta": zeta})


def _factors(x: np.ndarray, count: int) -> np.ndarray:
    """Leading principal-component time factors of the donor panel (T x count)."""
    u, s, _ = np.linalg.svd(x - x.mean(axis=0), full_matrices=False)
    return u[:, :count] * s[:count]


def fit_factor_model(y: np.ndarray, x: np.ndarray, pre: np.ndarray, count: int) -> Fit:
    """Generalized synthetic control / interactive fixed effects (Xu 2017).

    Common factors come from the untreated donors over all weeks; the treated
    unit's own loadings (plus an intercept) are fitted on pre-treatment weeks
    only. Unlike convex SCM weights, the loadings can exceed the donors' range,
    so a treated unit that reacts more strongly to a category-wide shock is
    projected to fall more when that shock unwinds.
    """
    factors = _factors(x, count)
    design = np.column_stack([np.ones(len(y)), factors])
    coef = np.linalg.lstsq(design[pre], y[pre], rcond=None)[0]
    synthetic = design @ coef
    return Fit("generalized_scm_factor", synthetic, y - synthetic, coef[1:],
               {"factor_count": count, "intercept": float(coef[0])})


def select_factor_count(
    y: np.ndarray, x: np.ndarray, train: np.ndarray, max_factors: int, block_weeks: int
) -> tuple[int, list[dict]]:
    """Choose the factor count by blocked cross-validation over the training weeks.

    Each contiguous block of ``block_weeks`` is held out in turn and predicted
    from loadings fitted on the remaining training weeks, so shocks anywhere in
    the pre-period (not only its final weeks) inform the choice. Post-treatment
    outcomes never enter.
    """
    train_index = np.flatnonzero(train)
    blocks = [train_index[start:start + block_weeks]
              for start in range(0, len(train_index), block_weeks)]
    rows = []
    for count in range(1, min(max_factors, x.shape[1] - 1) + 1):
        errors = []
        for block in blocks:
            fit_mask = train.copy()
            fit_mask[block] = False
            fit = fit_factor_model(y, x, fit_mask, count)
            errors.append(fit.gap_z[block])
        rows.append({"factor_count": count, "cv_rmspe_z": rmspe(np.concatenate(errors))})
    best = min(rows, key=lambda row: (row["cv_rmspe_z"], row["factor_count"]))
    return best["factor_count"], rows


def rmspe(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(values ** 2))) if len(values) else float("nan")
