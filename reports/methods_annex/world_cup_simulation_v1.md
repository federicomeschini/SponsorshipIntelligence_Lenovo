# World Cup simulation v1

> **Retired (ADR-0036): the simulation was replaced by observed Blinkfire exposure in the world_cup_impact_v1 engine; the official calendar now comes from srmp/ingest/fifa_calendar.py.**

> **Status:** simulation only, incomplete outcome, never an accepted attribution
> or valuation input. This branch does not replace the preregistered World Cup
> evaluation or any canonical data contract.

## Purpose

This experiment answers a narrow question before real World Cup Blinkfire data
arrive: what would the current Lenovo Brand Index imply if tournament exposure
were represented by a credible, explicitly simulated match-calendar profile?

It combines a real official calendar, the observed Brand Index and donor Trends
through 5 July 2026, and synthetic exposure calibrated to historical Lenovo
FIFA-family Blinkfire. It preserves two distinct counterfactual estimands.

## Official calendar and current coverage

The calendar is pulled from FIFA's public calendar API using competition 17 and
season 285023. It contains all 104 matches:

- first match: 11 June 2026 at 19:00 UTC;
- final: 19 July 2026 at 19:00 UTC;
- 72 first-stage, 16 round-of-32, 8 round-of-16, 4 quarter-final,
  2 semi-final, 1 bronze-final and 1 final match.

The current Trends-derived outcome runs through 5 July beneath its 6 July week
label. It therefore covers 91 of 104 scheduled matches, or 87.5%, but none of
the required 13-week persistence window.

## Synthetic exposure construction

For week w:

    match_score[w] = sum_m stage_weight[m]

The stage weights are 1.00 for the first stage, 1.35 for round-of-32, 1.65 for
round-of-16, 2.10 for quarter-finals, 2.90 for semi-finals, 1.90 for the bronze
final and 4.25 for the final.

For scenario s:

    impressions[s,w] =
        peak[s] * (floor[s] + (1-floor[s]) * match_score[w]/max_score)

The calibration uses 64 positive historical FIFA-family Blinkfire weeks:

| Scenario | Peak calibration | Floor |
|---|---:|---:|
| Low | historical p90 = 70.8m | 15% |
| Base | historical maximum = 171.6m | 25% |
| High | 1.5 x historical maximum = 257.4m | 35% |

Views use the historical median aggregate view rate, 0.798. Simulated
impressions receive geometric adstock with delta 0.80. These are scenario
numbers, not reconstructed observations. Every row has `is_simulated=true` and
a `SIMULATED_` measurement scope.

## Two estimands that must not be mixed

### 1. Total sponsorship-path difference during World Cup weeks

This uses the synthetic path frozen before the October 2024 FIFA partnership
announcement:

    total_path_gap[t] =
        Lenovo_actual[t] - synthetic_no_FIFA_partnership[t]

Across the observed World Cup weeks:

| Exposure scenario | Weighted gap |
|---|---:|
| Low | +0.360 Index points |
| Base | +0.367 Index points |
| High | +0.373 Index points |

The unweighted five-week mean is +0.490 points. This is the remaining Lenovo
excess relative to a world without the partnership announcement. It also
contains every other Lenovo-specific post-announcement shock, so it is not a
pure World Cup effect.

### 2. Incremental tournament lift above the existing sponsorship baseline

The second synthetic path is refitted using data through 1 June 2026:

    incremental_WC_gap[t] =
        Lenovo_actual[t] - synthetic_pre_tournament_continuation[t]

This absorbs the pre-existing partnership level and asks whether the tournament
created an additional break:

| Exposure scenario | Weighted gap |
|---|---:|
| Low | -0.164 Index points |
| Base | -0.160 Index points |
| High | -0.157 Index points |

The unweighted mean is -0.175 points. Pre-period RMSPE is 0.380 points,
post/pre RMSPE ratio is 1.323, and the donor-placebo p-value is 0.333.
The 26-week validation-holdout RMSPE is also weak at 1.157 points.

The current data therefore show **no positive, distinctive incremental World
Cup lift**. This can change when the final, post-event and persistence weeks
arrive.

## Interpretation

The test currently says:

- Lenovo remains roughly +0.37 points above the old pre-announcement
  no-partnership path during World Cup weeks;
- there is no evidence yet of an additional tournament lift above the
  sponsorship baseline immediately before the World Cup; and
- neither estimate can enter monetisation.

Simulating exposure only changes how observed weekly gaps are weighted. It
cannot create an outcome effect and cannot solve missing non-FIFA exposure,
unobserved Lenovo campaigns, or the incomplete post-period.

## Isolation and reproduction

The simulation writes only to
`data/curated/experimental/world_cup_simulation_v1`. It does not modify
canonical Blinkfire, Brand Index, the primary World Cup accepted-attribution
table, or the monetisation configuration.

Run:

    python -m srmp.experiments.world_cup_simulation_v1

Use `--refresh-calendar` only to take a new official FIFA API snapshot.
Configuration and all assumptions are in
`config/experiments/world_cup_simulation_v1.yaml`.

## Still required for the real estimate

- observed World Cup Blinkfire FIFA and non-FIFA exposure;
- the final tournament weeks and at least 13 post-event weeks;
- confirmed Lenovo activation and media/campaign dates and intensity;
- broadcast/GRP exposure for a total-exposure interpretation;
- post-World-Cup survey evidence; and
- successful frozen fit, holdout, placebo and timing gates.
