# World Cup sponsorship impact preregistration

> **Protocol current; implementation status updated (2026-10-06).** The frozen protocol below still governs the evaluation. Since it was written: tournament milestones were filled from the official FIFA calendar (ADR-0027), the estimator was implemented with a post-hoc factor-model robustness check (ADR-0029), and interim results are reviewed in [`20_world_cup_impact_interim.ipynb`](20_world_cup_impact_interim.ipynb). Statements below that dates are null or that only a skeleton exists describe July 2026.

## Why this is the primary evaluation

The largest effect of the Lenovo sponsorship may occur during the World Cup,
not at the 2024 partnership announcement or the 2025 Club World Cup. The
existing synthetic-control result is therefore an interim diagnostic. It must
not be treated as the final sponsorship effect or used to close monetization.

This prospective protocol fixes the principal estimand, counterfactual design,
quality gates, and valuation handoff before the World Cup outcome dataset is
available. Dates remain null until an approved event and activation calendar is
provided; they will not be selected from observed Index or search peaks.

## Primary estimand

Let the accepted World Cup counterfactual gap be:

    gap[t] = actual_brand_index[t] - counterfactual_brand_index[t]

The primary impact measure is the sustained exposure-weighted uplift:

    delta_index_world_cup = sum_t(world_cup_adstock[t] * gap[t])
                            / sum_t(world_cup_adstock[t])

The registered window begins at the approved activation start and remains open
through the tournament plus at least thirteen post-tournament weeks. The
thirteen weeks measure persistence and prevent the estimate from being defined
only by a short search spike.

Secondary outcomes are the all-post mean gap, peak four-week mean, thirteen-
week persistence gap, co-branded search gap, and post-World-Cup appeal and
purchase-intent sponsorship lift.

## Counterfactual design frozen now

The common-anchor input and confounder skeleton are now implemented. The World
Cup design requires:

1. Jointly scaled Google Trends panels connected by a repeated common anchor,
   so cross-brand movements are measured on a coherent scale.
2. At least nine credible computing-category donors, screened for sponsorship
   contamination and structural breaks before the outcome is observed. Donors
   are competitor-brand salience proxies; sponsored properties are not donors.
3. At least 104 pre-event weeks, with the final 26 weeks held out to select and
   validate the counterfactual specification.
4. Augmented synthetic control as primary, with simplex SCM and synthetic
   difference-in-differences as robustness methods.
5. Donor-as-treated and fake-date placebos, with registered maximum placebo
   p-value 0.10 before any non-zero estimate may enter valuation.
6. Lenovo product-launch, promotion, CES, and non-sponsorship campaign controls.
   Blinkfire is separately aggregated into FIFA treatment intensity and all
   non-FIFA Lenovo sponsorship intensity; neither aggregate fits donor weights.
7. No tuning of donors, dates, transformations, or post windows after the
   World Cup outcome is observed.

Pre-period holdout validation is appropriate here because the model's job is
to predict the missing no-World-Cup path. This is distinct from the Brand Index
itself, which is a descriptive measure and is not selected by forecasting.

## Incoming data required

Two formerly missing inputs are now ready:

- a six-panel, 21-query, ten-draw common-anchor Trends artifact, with 11
  data-quality and contamination-screened base donors; and
- a 21-row Lenovo product/corporate/promotion event calendar. These are
  event-week indicators rather than media-spend intensity measures.

The current skeleton is still waiting for:

- approved activation, tournament, and primary post-window dates;
- updated World Cup Blinkfire exposure through the persistence window; and
- the exact World Cup event/activation/match calendar.

Broadcast/GRP exposure and a post-World-Cup survey are required for a decision-
grade mechanism and total-exposure interpretation, although the counterfactual
Index gap can technically be estimated without them. Their absence must remain
visible in any output.

The exact schemas are frozen in
`data/reference/world_cup_impact_data_contract.yaml`.

## Acceptance and monetization

An estimate can populate `delta_index_attrib` only when:

- all required sources and milestone dates pass readiness checks;
- the pre-period fit and 26-week holdout are acceptable;
- the result is robust across the three registered estimators;
- the donor-placebo p-value is at most 0.10;
- timing is coherent with activation and exposure; and
- the estimate remains interpretable after product-launch controls.

Until those gates pass, `accepted_attribution.parquet` remains empty. Once they
pass, the accepted Index change enters the existing royalty-schedule and BCF-
adjusted revenue pipeline. The royalty schedule and BCF inputs remain separate
valuation requirements.

## Current readiness

Status is `waiting_for_world_cup_data`. The canonical Brand Index, jointly
scaled donor panel and Lenovo product/campaign controls are available. The four
milestone dates, updated World Cup exposure, and exact World Cup event calendar
remain unresolved.

The re-estimated announcement/FCWC candidate is +1.033 exposure-weighted Index
points and clears the donor-placebo threshold at p=0.0833, the smallest possible
p-value with 11 donors. It is still not accepted for valuation: the controlled
FIFA-exposure timing coefficient is negative and not distinguishable from zero,
the announcement coincides with Tech World, and the primary World Cup outcome
and persistence window are incomplete.

Run the readiness skeleton with:

    python -m srmp.experiments.world_cup_impact_v1

The generated manifest and frozen estimands are in
`data/curated/experimental/world_cup_impact_v1`.

## Simulation branch

`world_cup_simulation_v1` uses the official 104-match calendar and
historical-Blinkfire-calibrated synthetic exposure to exercise the pipeline
against the currently observed Trends outcome. It is deliberately isolated and
does not satisfy the real-exposure or persistence requirements above.

The current simulation finds +0.367 Index points relative to the frozen
pre-announcement no-partnership path, but -0.160 points for incremental
tournament lift above the immediate pre-World-Cup sponsorship baseline. The
incremental placebo p-value is 0.333. Neither result is accepted for valuation.
Full construction and caveats are in `world_cup_simulation_v1.md`.
