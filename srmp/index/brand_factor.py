"""Weekly Lenovo Brand Index as a mixed-frequency dynamic factor (ADR-0039).

A single latent weekly brand-strength factor f_t (AR(1), unit variance) drives
every weekly signal: x_it = lambda_i f_t + e_it. Each GWI quarterly reading is
a noisy measurement of the factor's *average over its quarter*:
y_q = lambda_q * (1/n_q) * sum_{t in q} f_t + u_q. The state carries the
factor and a running within-quarter sum, so the survey informs the weekly path
without being interpolated or pinned to any single week. Loadings and noise
variances are estimated by maximum likelihood; the Kalman smoother gives the
weekly index and its standard error.

Every weekly signal is a brand-level share of attention, log(Lenovo) minus
log(sum of rival brands), so PC-market demand cancels out. Lenovo product and
price searches are written alongside as a descriptive demand indicator only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from statsmodels.tsa.statespace.mlemodel import MLEModel


def _monday(values: pd.Series) -> pd.Series:
    values = pd.to_datetime(values)
    return values - pd.to_timedelta(values.dt.weekday, unit="D")


def log_share(frame: pd.DataFrame, numerator: list[str], denominator: list[str]) -> pd.Series:
    """log(sum of numerator columns) - log(sum of denominator columns), week by week."""
    return np.log(frame[numerator].sum(axis=1)) - np.log(frame[denominator].sum(axis=1))


def donor_shares_of_search(donors: pd.DataFrame, rivals: list[str]) -> pd.DataFrame:
    """Rival brands on the Brand Index basis: log(donor) - log(sum of the rival set without
    that donor). Lenovo is in no denominator, so a sponsorship lift cannot depress the donors.
    A zero search value gives a missing week, which the data-quality rules then exclude."""
    shares = pd.DataFrame({name: np.log(donors[name]) - np.log(donors[[r for r in rivals if r != name]].sum(axis=1))
                           for name in donors.columns}, index=donors.index)
    return shares.replace([np.inf, -np.inf], np.nan)


def joint_search_panel(config: dict[str, Any]) -> pd.DataFrame:
    """Weekly common-scale search interest (W-MON weeks x query_id), one Lenovo anchor
    shared by every rival panel; the anchor is averaged over the panels it appears in."""
    panel = pd.read_parquet(config["inputs"]["donor_trends"])
    panel["week"] = pd.to_datetime(panel["week"]) + pd.Timedelta(days=1)   # W-SUN -> W-MON
    return panel.pivot_table(index="week", columns="query_id", values="interest_common_scale", aggfunc="mean")


def registry_ids(config: dict[str, Any], policies: list[str]) -> list[str]:
    registry = pd.read_csv(config["inputs"]["donor_registry"])
    return registry.loc[registry["inclusion_policy"].isin(policies), "query_id"].tolist()


def _weekly_signals(config: dict[str, Any], weeks: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict[str, str]]:
    search = joint_search_panel(config)
    wiki = pd.read_parquet(config["inputs"]["wikipedia"])
    wiki["week"] = _monday(wiki["date"])
    wiki = wiki.pivot_table(index="week", columns="proxy_id", values="views", aggfunc="mean")
    columns, pillar_of = {}, {}
    for pillar, signals in config["weekly_signals"].items():
        for spec in signals:
            if spec["source"] == "trends_share":
                rivals = [q for q in registry_ids(config, spec["denominator_policies"]) if q in search]
                series = log_share(search, spec["numerator"], rivals)
            elif spec["source"] == "wikipedia_share":
                series = log_share(wiki, spec["numerator"], spec["denominator"])
            else:
                raise ValueError(f"unknown weekly signal source {spec['source']!r}")
            columns[spec["id"]] = series.reindex(weeks)
            pillar_of[spec["id"]] = pillar
    return pd.DataFrame(columns, index=weeks), pillar_of


def _product_demand(config: dict[str, Any], weeks: pd.DatetimeIndex, base: np.ndarray) -> pd.Series:
    """Geometric mean of Lenovo product/price search volumes, % of the base-period level
    (descriptive demand indicator, not in the index)."""
    trends = pd.read_parquet(config["inputs"]["trends"])
    trends["week"] = pd.to_datetime(trends["week"]) + pd.Timedelta(days=1)
    wide = trends.pivot_table(index="week", columns="query_id", values="interest_mean").reindex(weeks)
    logs = np.log(wide[config["product_demand_indicator"]["query_ids"]].clip(lower=0.5))
    return 100 * np.exp((logs - logs[base].mean()).mean(axis=1))


def _quarterly_signals(config: dict[str, Any], weeks: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict[str, str], pd.Series]:
    """Place each GWI reading on the last week of its quarter; return quarter-length per week."""
    survey = pd.read_parquet(config["inputs"]["survey"])
    survey = survey[survey["source"].eq("gwi")].copy()
    survey["quarter"] = pd.PeriodIndex(pd.to_datetime(survey["fieldwork_start"]), freq="Q")
    quarter_of_week = pd.PeriodIndex(weeks, freq="Q")
    last_week = pd.Series(weeks, index=weeks).groupby(quarter_of_week).max()
    n_weeks = pd.Series(weeks, index=weeks).groupby(quarter_of_week).size()
    frame, pillar_of = pd.DataFrame(index=weeks), {}
    for pillar, signals in config["quarterly_signals"].items():
        for spec in signals:
            values = pd.Series(np.nan, index=weeks)
            for row in survey.itertuples():
                if row.quarter in last_week.index and pd.notna(getattr(row, spec["column"])):
                    values.loc[last_week[row.quarter]] = float(getattr(row, spec["column"]))
            frame[spec["id"]] = values
            pillar_of[spec["id"]] = pillar
    n_per_week = pd.Series(np.asarray(n_weeks.reindex(quarter_of_week)), index=weeks)
    return frame, pillar_of, n_per_week


def _validity_screen(weekly: pd.DataFrame, quarterly: pd.DataFrame, quarter_of_week: pd.PeriodIndex) -> pd.DataFrame:
    """P4 gate: sign validity of each weekly signal against every GWI series."""
    q_weekly = weekly.groupby(quarter_of_week).mean()
    q_survey = quarterly.groupby(quarter_of_week).max()
    rows = []
    for signal in weekly:
        row = {"signal": signal}
        checks = []
        for survey in quarterly:
            paired = pd.concat([q_weekly[signal], q_survey[survey]], axis=1).dropna()
            level = float(paired.corr().iloc[0, 1])
            change = float(paired.diff().corr().iloc[0, 1])
            row[f"{survey}_level_corr"], row[f"{survey}_change_corr"] = level, change
            row["overlap_quarters"] = int(len(paired))
            checks += [level > 0, change > 0]
        row["admitted"] = bool(all(checks))
        rows.append(row)
    return pd.DataFrame(rows)


class MixedFrequencyFactor(MLEModel):
    """State [f_t, s_t]: f_t = phi f_{t-1} + eta_t; s_t = (1 - reset_t) s_{t-1} + f_t."""

    def __init__(self, data: pd.DataFrame, weekly: list[str], quarterly: list[str],
                 reset: np.ndarray, n_per_week: np.ndarray, noise_floor: float = 0.0):
        super().__init__(data, k_states=2, k_posdef=1, initialization="approximate_diffuse")
        self.weekly, self.quarterly = weekly, quarterly
        nobs, k = self.nobs, len(data.columns)
        transition = np.zeros((2, 2, nobs))
        transition[1, 1, :] = 1.0 - reset
        self["transition"] = transition
        self["selection"] = np.array([[1.0], [1.0]])
        self.reset = reset
        self.n_per_week = n_per_week
        self["design"] = np.zeros((k, 2, nobs))
        self.k = k
        self.noise_floor = noise_floor

    @property
    def param_names(self) -> list[str]:
        names = list(self.data.ynames) if isinstance(self.data.ynames, list) else [self.data.ynames]
        return (["phi"] + [f"loading.{n}" for n in names] + [f"log_sigma2.{n}" for n in names])

    @property
    def start_params(self) -> np.ndarray:
        return np.r_[0.9, np.full(self.k, 0.5), np.full(self.k, np.log(0.5))]

    def transform_params(self, unconstrained: np.ndarray) -> np.ndarray:
        params = unconstrained.copy()
        params[0] = np.tanh(unconstrained[0])
        return params

    def untransform_params(self, constrained: np.ndarray) -> np.ndarray:
        params = constrained.copy()
        params[0] = np.arctanh(np.clip(constrained[0], -0.9999, 0.9999))
        return params

    def update(self, params, **kwargs):
        params = super().update(params, **kwargs)
        phi, loadings, log_sigma2 = params[0], params[1:1 + self.k], params[1 + self.k:]
        # Built fresh with the parameters' dtype so complex-step gradients pass through unchanged.
        transition = np.zeros((2, 2, self.nobs), dtype=params.dtype)
        transition[1, 1, :] = 1.0 - self.reset
        transition[0, 0, :] = phi
        # s_t = (1 - reset) s_{t-1} + phi f_{t-1} + eta_t  (f_t substituted)
        transition[1, 0, :] = phi
        self["transition"] = transition
        self["state_cov"] = np.array([[1.0 - phi ** 2]])
        design = np.zeros((self.k, 2, self.nobs), dtype=params.dtype)
        n_weekly = len(self.weekly)
        design[:n_weekly, 0, :] = loadings[:n_weekly, None]
        design[n_weekly:, 1, :] = loadings[n_weekly:, None] / self.n_per_week[None, :]
        self["design"] = design
        # Floor on unique variance: prevents a Heywood case where one indicator absorbs the factor.
        self["obs_cov"] = np.diag(np.exp(log_sigma2) + self.noise_floor)


def _anchor_log_sd(raw_weekly: pd.DataFrame, weekly_pillars: dict[str, str], members: list[str],
                   pillar: str, base: np.ndarray) -> float:
    """Base-period sd of the anchor pillar in log-share units (mean of its members' log shares)."""
    names = [n for n in members if f"pillar_{weekly_pillars[n]}" == pillar]
    return float(raw_weekly[names].mean(axis=1)[base].std())


def _pillars(weekly: pd.DataFrame, weekly_pillars: dict[str, str], admitted: list[str], base: np.ndarray) -> pd.DataFrame:
    """Pillars first (mean of admitted signals, re-standardised), so a pillar with many
    correlated signals cannot outvote one with few; factor weights act on pillars."""
    pillars = {}
    for pillar in dict.fromkeys(weekly_pillars.values()):
        members = [n for n in admitted if weekly_pillars[n] == pillar]
        if members:
            series = weekly[members].mean(axis=1)
            pillars[f"pillar_{pillar}"] = (series - series[base].mean()) / series[base].std()
    return pd.DataFrame(pillars, index=weekly.index)


def _fit(weekly: pd.DataFrame, quarterly: pd.DataFrame, n_per_week: pd.Series, base: np.ndarray,
         config: dict[str, Any], anchor_log_sd: float) -> dict[str, Any]:
    """Fit the factor model on pillar-level weekly series plus quarterly survey series.

    Display mapping: the anchor pillar's common component lambda_a * f_t, converted
    from standard units to log-share units (x anchor_log_sd), is expressed relative
    to its base-period mean: index_t = 100 * exp(anchor_log_sd * lambda_a * (f_t - mean_base f)).
    """
    weeks = weekly.index
    quarter_of_week = pd.PeriodIndex(weeks, freq="Q")
    data = pd.concat([weekly, quarterly], axis=1)
    reset = np.r_[1.0, (quarter_of_week[1:] != quarter_of_week[:-1]).astype(float)]
    floor = float(config["model"].get("noise_variance_floor", 0.0))
    model = MixedFrequencyFactor(data, list(weekly.columns), list(quarterly.columns), reset,
                                 n_per_week.to_numpy(), noise_floor=floor)
    result = model.fit(disp=False, maxiter=2000, method="lbfgs")
    names = list(data.columns)
    params = np.asarray(result.params, dtype=float)
    loadings = params[1:1 + len(names)].copy()
    sigma2 = np.exp(params[1 + len(names):]) + floor
    orient = 1.0 if loadings[names.index(config["model"]["orientation_pillar"])] > 0 else -1.0
    loadings *= orient
    smoothed = orient * result.smoothed_state[0]
    smoothed_sd = np.sqrt(result.smoothed_state_cov[0, 0])
    slope = anchor_log_sd * loadings[names.index(config["display_scale"]["anchor_pillar"])]
    log_level = slope * (smoothed - smoothed[base].mean())
    index_level = 100 * np.exp(log_level)
    return {
        "names": names, "phi": float(params[0]), "loadings": loadings, "sigma2": sigma2,
        "factor": smoothed, "data": data, "llf": float(result.llf),
        "converged": bool(result.mle_retvals.get("converged", True)),
        "index_level": index_level, "index_se": index_level * abs(slope) * smoothed_sd,
        "log_points_per_factor_sd": float(slope),
    }


def _survey_fit(index_level: np.ndarray, quarterly: pd.DataFrame) -> dict[str, dict[str, float]]:
    weeks = quarterly.index
    q_index = pd.Series(index_level, index=weeks).groupby(pd.PeriodIndex(weeks, freq="Q")).mean()
    fit = {}
    for column in quarterly:
        q_obs = quarterly[column].dropna()
        q_obs.index = pd.PeriodIndex(q_obs.index, freq="Q")
        paired = pd.concat([q_index.rename("index"), q_obs.rename("survey")], axis=1).dropna()
        fit[column] = {"quarters": int(len(paired)), "correlation": float(paired.corr().iloc[0, 1]),
                       "change_correlation": float(paired.diff().corr().iloc[0, 1])}
    return fit


def build_brand_factor_index(config_path: str = "config/brand_index.yaml") -> dict[str, Any]:
    config_file = Path(config_path)
    config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    search_end = joint_search_panel(config).index.max()
    weeks = pd.date_range(pd.Timestamp(config["sample_start"]), search_end, freq="W-MON")

    raw_weekly, signal_pillars = _weekly_signals(config, weeks)
    quarterly, quarterly_pillars, n_per_week = _quarterly_signals(config, weeks)
    base = np.asarray((weeks >= pd.Timestamp(config["standardisation_base"][0]))
                      & (weeks <= pd.Timestamp(config["standardisation_base"][1])))

    # Standardise: weekly signals on the pre-announcement base; survey on its pre-announcement quarters.
    weekly, moments = raw_weekly.copy(), {}
    for column in weekly:
        mean, sd = weekly.loc[base, column].mean(), weekly.loc[base, column].std()
        weekly[column] = (weekly[column] - mean) / sd
        moments[column] = (mean, sd)
    survey_base = weeks < pd.Timestamp(config["standardisation_base"][1])
    for column in quarterly:
        mean, sd = quarterly.loc[survey_base, column].mean(), quarterly.loc[survey_base, column].std()
        quarterly[column] = (quarterly[column] - mean) / sd
        moments[column] = (mean, sd)

    quarter_of_week = pd.PeriodIndex(weeks, freq="Q")
    screen = _validity_screen(weekly, quarterly, quarter_of_week)
    admitted = screen.loc[screen["admitted"], "signal"].tolist()
    if not admitted:
        raise ValueError("P4 validity screen admitted no weekly signal; the index cannot be built.")
    pillars = _pillars(weekly, signal_pillars, admitted, base)
    pillar_names = {name: name.removeprefix("pillar_") for name in pillars.columns}
    anchor = config["display_scale"]["anchor_pillar"]
    fit = _fit(pillars, quarterly, n_per_week, base, config,
               _anchor_log_sd(raw_weekly, signal_pillars, admitted, anchor, base))

    # Effective factor-analysis weights: signal-to-noise lambda / sigma^2, normalised (weekly series).
    names, loadings, sigma2 = fit["names"], fit["loadings"], fit["sigma2"]
    pillar_of = {**pillar_names, **quarterly_pillars}
    snr = loadings / sigma2
    weekly_mask = np.array([n in pillar_names for n in names])
    loading_table = pd.DataFrame({
        "signal": names, "pillar": [pillar_of[n] for n in names],
        "frequency": ["weekly" if n in pillar_names else "quarterly" for n in names],
        "members": [", ".join(s for s in admitted if signal_pillars[s] == pillar_names[n]) if n in pillar_names else n
                    for n in names],
        "loading": loadings, "noise_variance": sigma2,
        "share_of_variance_explained": loadings ** 2 / (loadings ** 2 + sigma2),
        "effective_weekly_weight": np.where(weekly_mask, snr / np.abs(snr[weekly_mask]).sum(), np.nan),
        "observations": [int(fit["data"][n].notna().sum()) for n in names],
    })

    # Sensitivities: same model, one assumption changed each.
    sensitivity_rows, sensitivity_summary = [], []
    for spec in config.get("sensitivities", []):
        keep = list(weekly.columns) if spec.get("force_admit") == "all" else admitted
        q = quarterly.iloc[:, :0] if spec.get("drop_quarterly") else quarterly
        alt = _fit(_pillars(weekly, signal_pillars, keep, base), q, n_per_week, base, config,
                   _anchor_log_sd(raw_weekly, signal_pillars, keep, anchor, base))
        sensitivity_rows.append(pd.DataFrame({"week": weeks.date, "sensitivity": spec["id"],
                                              "index_level": alt["index_level"], "index_se": alt["index_se"]}))
        post = weeks >= pd.Timestamp(config["standardisation_base"][1])
        sensitivity_summary.append({
            "id": spec["id"], "description": spec["description"], "weekly_signals": keep,
            "survey_used": not spec.get("drop_quarterly", False),
            "correlation_with_headline": float(np.corrcoef(alt["index_level"], fit["index_level"])[0, 1]),
            "post_announcement_mean": float(alt["index_level"][post].mean()),
            "survey_fit": _survey_fit(alt["index_level"], quarterly)})

    weekly_out = pd.DataFrame({
        "week": weeks.date, "index_level": fit["index_level"], "index_se": fit["index_se"], "factor": fit["factor"],
        "weekly_signals_observed": weekly[admitted].notna().sum(axis=1).to_numpy(),
        "survey_quarter_end": quarterly.notna().any(axis=1).to_numpy(),
    })
    # Each raw signal as % of its base-period share (descriptive; 100 = pre-announcement level).
    for column in raw_weekly:
        weekly_out[f"log_share_{column}"] = raw_weekly[column].to_numpy()
        weekly_out[f"signal_{column}"] = (100 * np.exp(raw_weekly[column] - raw_weekly.loc[base, column].mean())).to_numpy()
    weekly_out["product_search_demand"] = _product_demand(config, weeks, base).to_numpy()

    target = Path(config["outputs"]["directory"])
    target.mkdir(parents=True, exist_ok=True)
    tables = {"weekly": weekly_out, "loadings": loading_table, "screen": screen,
              "sensitivities": pd.concat(sensitivity_rows, ignore_index=True) if sensitivity_rows else pd.DataFrame()}
    for key, frame in tables.items():
        frame.to_parquet(target / f"{config['outputs'][key]}.parquet", index=False)
        frame.to_csv(target / f"{config['outputs'][key]}.csv", index=False)

    manifest = {
        "index_id": config["index_id"], "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_file), "config_sha256": hashlib.sha256(config_file.read_bytes()).hexdigest(),
        "method": "mixed-frequency dynamic factor model (weekly AR(1) factor; GWI as quarterly-average measurements), MLE + Kalman smoother",
        "sample": [str(weeks.min().date()), str(weeks.max().date())], "weeks": len(weeks),
        "converged": fit["converged"], "log_likelihood": fit["llf"], "phi": fit["phi"],
        "display_scale": {**config["display_scale"], "log_points_per_factor_sd": fit["log_points_per_factor_sd"],
                          "reading": "100 = pre-announcement average; 110 = brand share of attention about 10% above it"},
        "standardisation_base": config["standardisation_base"], "moments": {k: [float(a), float(b)] for k, (a, b) in moments.items()},
        "survey_fit": _survey_fit(fit["index_level"], quarterly),
        "validity_screen": {"rule": "admit a weekly signal only if its quarterly mean correlates positively with every GWI series in levels and in quarter-on-quarter changes over the overlap (P4)",
                            "admitted": admitted, "excluded": screen.loc[~screen["admitted"], "signal"].tolist()},
        "sensitivities": sensitivity_summary,
        "caveats": [
            "Weekly signals are shares of attention against rival brands; a shock that moves Lenovo's rivals moves the index in the opposite direction.",
            "One common factor: dimensions that do not co-move with the others receive small loadings rather than their own pillar weight.",
            "GWI engagement/consideration are a non-canonical anchor (ADR-0011); the survey ends at 2026Q1, so later weeks rest on the weekly signals alone.",
            "Idiosyncratic errors are i.i.d.; persistent signal-specific movements may be partly absorbed by the factor.",
            "Product and price search volume is reported as a demand indicator and is not part of the index.",
        ],
    }
    (target / config["outputs"]["manifest"]).write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/brand_index.yaml")
    args = parser.parse_args()
    build_brand_factor_index(args.config)
