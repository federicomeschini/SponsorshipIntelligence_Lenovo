# Experimental sponsorship-to-monetization path v1

> **SUPERSEDED (2026-10-07).** The current review artifact for this experiment is [`15_exposure_and_survey_lift.ipynb`](15_exposure_and_survey_lift.ipynb), which reads the current outputs. This document is the July 2026 record; its figures are in the superseded search-salience index's units (ADR-0040) and must not be quoted.

> **Units changed by ADR-0040 (2026-10-07).** Brand Index figures below are in the superseded search-salience index's points; the experiment now runs on the brand-level Brand Index (1 point ≈ 1% of brand share of attention).

> **STALE: not synchronized with the October 2026 production state (labelled 2026-10-06).**
> - *Affected:* counterfactual gate (the announcement candidate no longer passes: p = 2/12), exposure coverage (now to 20 July 2026), the remark that the workspace has no Git repository
> - *Why not updated yet:* the October 2026 refresh (ADR-0027) re-ran this experiment; the narrative was not rewritten in the same session
> - *Consequence for interpretation:* the bridge remains blocked for valuation, now for an additional reason (attribution not distinguishable)
> - *Required action:* rewrite as a review notebook (tracked under "Open documentation actions" in `README.md`).

## Status and purpose

This is a logical experimental branch, not a Git branch: the workspace has no
Git repository. It is isolated under `srmp/experiments`, `config/experiments`,
and `data/curated/experimental`, and replaces none of C-INDEX, C-EXPOSURE, or
C-ROI.

The aim is to connect three distinct pieces of evidence without collapsing
their meanings:

1. Blinkfire impressions describe property-level exposure.
2. The consumer survey describes observational appeal and purchase-intent lift
   among sponsorship-aware versus unaware respondents.
3. The Brand Index describes Lenovo's broad weekly brand-performance proxy.

The experiment seeks to build a reproducible bridge from exposure to survey
mechanism evidence, use that evidence only to allocate an independently
identified total Brand Index effect, and then value that effect through an
approved royalty-relief schedule.

## What is implemented

### Exposure transformation

The confirmed Blinkfire scope contains impressions and views, not engagement
or post-level measures. Weekly impressions receive geometric adstock:

    A[p,t] = impressions[p,t] + 0.80 * A[p,t-1]

The 0.80 parameter is a fixed experimental scenario. It is not estimated from
the five survey-linked observations.

### Survey mechanism measure

Awareness is excluded because the aware segment is defined through sponsorship
awareness. For each property and survey wave:

    L[p,q] = 0.5 * appeal_lift[p,q] + 0.5 * purchase_intent_lift[p,q]

where each lift is aware minus unaware. The measure is observational and is not
a causal effect. The 2024 rows are retained descriptively but excluded from the
comparable panel because their response scale differs from 2025-26.

### Time alignment

Exact fieldwork dates are unavailable. Each survey is aligned to the final
Monday on or before its reported month-end, with exposure summarized over the
preceding 13 weeks. This approximation is explicit in every output row.

### Property allocation scenario

For each eligible property-wave, the evidence score is:

    S[p,q] = mean_trailing_13w_adstock[p,q] * max(L[p,q], 0)

Property scores average across available waves so a property is not rewarded
merely for having more surveys:

    S[p] = mean_q S[p,q]
    allocation_share[p] = S[p] / sum_j S[j]

This construction uses only exposure preceding the relevant survey; later
exposure cannot leak backward. The share distributes an independently estimated
total effect. It is not a causal attribution estimate and never enters Brand
Index weights.

## Current empirical result

The panel contains seven property-wave observations. Two 2024 observations
precede Blinkfire coverage and use the old survey scale. Five observations are
eligible under the 2025-plus scale: two FWC, two FWWC, and one FCWC.

| Property | Comparable waves | Mean funnel lift | Experimental allocation share |
|---|---:|---:|---:|
| FCWC | 1 | 42.25 pp | 82.49% |
| FWC | 2 | 40.23 pp | 16.99% |
| FWWC | 2 | 44.27 pp | 0.52% |

The FCWC share is driven by very large preceding digital impressions, not by a
materially larger survey lift. FWWC has the largest mean lift but little
preceding measured digital exposure. Broadcast exposure is absent, so these
shares must not be presented as final property value shares. With only five
eligible observations, a fixed-effects exposure-lift regression is not
estimable credibly and is deliberately not run.

## Monetization engine and gate

Once a total sponsorship-attributable Brand Index change is independently
identified, the experiment allocates it as:

    delta_index[p] = allocation_share[p] * delta_index_attrib
    delta_royalty_bps[p] = royalty_bps_per_index_point * delta_index[p]

Total incremental value is:

    value = sum_years revenue * (delta_royalty_bps / 10000)
                      / (1 + discount_rate)^year

The total output also reports:

    value_multiple = value / sponsorship_fee
    net_ROI = (value - sponsorship_fee) / sponsorship_fee

The engine is implemented and unit-tested, but the current valuation table is
empty by design. It refuses to emit money until all inputs are explicit.

## Where we are blocked

The expanded synthetic-control experiment supplies a candidate
exposure-weighted change of +1.033 Index points. It clears the donor-placebo
threshold at p=0.0833, but this is the smallest attainable p-value with 11
donors. More importantly, the controlled FIFA-exposure timing diagnostic is
not supported and the primary World Cup outcome is incomplete. Explicit
acceptance is therefore withheld and the candidate is not used for valuation.
The full result is documented in
[experimental_sponsorship_counterfactual_v1.md](experimental_sponsorship_counterfactual_v1.md).

The current configuration still requires:

- an accepted sponsorship-attributable Brand Index change; the current
  counterfactual passes its interim fit/placebo screen but remains a sensitivity
  candidate pending timing coherence and the World Cup evaluation;
- an approved royalty schedule with at least two Index/rate points; the current
  schedule has zero approved points;
- the brand-attributable revenue base;
- the sponsorship fee;
- a discount rate; and
- a persistence horizon.

Method quality would also improve with exact survey fieldwork dates, more
comparable survey waves, and broadcast/GRP exposure. Those are not required to
execute a valuation scenario, but they are required before treating it as a
decision-grade estimate.

## Reproduction and outputs

Run:

    python -m srmp.experiments.sponsorship_monetization_v1

The configuration is
`config/experiments/sponsorship_monetization_v1.yaml`. Outputs are written to
`data/curated/experimental/sponsorship_monetization_v1`:

- `exposure_adstock_weekly`: scenario adstock for all properties;
- `funnel_lift_exposure_panel`: survey, preceding exposure, and Brand Index
  context at each wave;
- `property_allocation_scenario`: provisional evidence shares;
- `monetization_scenarios`: empty until the valuation gate opens; and
- `experiment_manifest.json`: status, assumptions hash, caveats, and missing
  inputs.

## Experimental financial bridge

`brand_financial_bridge_v1` tests whether quarterly Brand Index changes
map to Lenovo's directly reported adjusted profit, with category-demand, HSI,
Nasdaq-100-in-HKD, revenue and seasonality controls. Stock prices are used only
as factor-adjusted abnormal-return corroboration.

The primary controlled result is +0.0035 percentage points of adjusted
net-income margin per Brand Index point, but its approximate 95% interval is
-0.980 to +0.987 points and specifications change sign. It is therefore not
used to populate the monetisation gate. See
`brand_financial_bridge_v1.md`.
