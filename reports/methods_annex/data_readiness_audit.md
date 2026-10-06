# Data readiness audit — 2026-07-14

> **SUPERSEDED for data coverage by [`00_data_inputs.ipynb`](00_data_inputs.ipynb) (2026-10-06).** The survey-readiness findings below remain valid (survey inputs unchanged since July 2026); all coverage dates are July values.

## Current position

The supplied consumer-research workbook is a segmented crosstab, not a
population brand-index anchor. The GWI workbook supplies a usable but
non-canonical quarterly engagement/consideration calibration series. Google
Trends now supplies the high-frequency proxy core. The client has confirmed
that the supplied wide Blinkfire summary is the complete available D2 scope.

## Data acquired in this review

- D4 Wikimedia: 14,895 daily rows from 2022-01-01 through 2026-07-13 for Lenovo (English and Chinese), ThinkPad, Lenovo Legion, and five donor candidates (HP, Dell, Asus, Samsung Electronics, Huawei). Raw year-bounded API responses and SHA-256 manifests are retained.
- D6 market data: 4,529 daily rows from 2022-01-03 through 2026-07-14 for 0992.HK, Hang Seng, NASDAQ-100, and USD/HKD. Raw provider responses and manifests are retained.
- D7 events: four officially sourced milestones covering the 2024 FIFA partnership announcement and the 2025 Club World Cup partnership, opening, and final.
- D2 reference normalization: 13 source labels in the supplied Blinkfire export are mapped to stable property IDs.
- D2 staged exposure: 8,047 `date × property_id` rows, with the source TOTAL row reconciled exactly. Measures remain impressions and views.
- D2 weekly exposure: 1,157 `property_id × W-MON week` rows with impressions, views, view rate, and observed-day coverage.
- D1 descriptive survey: 42 segmented wave metrics with explicit scale versions and `canonical_anchor_eligible: false`.
- D5 GDELT: 1,634 daily Lenovo news-volume/tone rows. Twenty-two calendar dates are absent from the provider response and are reported, not filled as zeros.
- D3 Google Trends: 163 of 170 configured overlap windows were retrieved across
  17 worldwide queries. All ten windows are present for the six Lenovo
  brand/product/price queries; the seven failures are confined to the sparse
  `Lenovo Club World Cup` property query.
- L2 provisional index: 236 W-MON observations from 2022-01-03 through
  2026-07-06. The validated `Lenovo` parent-brand Trends series supplies
  weekly movement; the 37-quarter GWI composite supplies orientation and scale.
  Product-portfolio and commercial-intent components are retained separately.

Wikipedia and GDELT were screened and excluded from the headline index because
their relationship to the available GWI composite was wrong-sign or unstable.
NASDAQ-100 must be converted to HKD in L5 before factor returns are estimated.

## Acquisition attempts that did not complete

- Acer's current English Wikipedia title returned no historical pageview endpoint at the 2022 boundary. It was excluded rather than silently backfilled; five other donor candidates remain.
- Seven of ten overlap windows for the sparse `Lenovo Club World Cup` query
  failed. This does not affect C-INDEX, but it limits that property-specific
  outcome until the windows are refreshed or manually exported.

## Blocking missing inputs

1. Approved wave-level survey extract: composite, all five funnel-stage scores,
   exact fieldwork start/end, weights, questionnaire version, and comparability
   crosswalk. This blocks a canonical brand-equity index, but not the current
   provisional brand-salience index.
2. Sponsorship fee and approved royalty-rate schedule/revenue base. These block
   L7 ROI.

## Experimental sponsorship-to-monetization path

An isolated `sponsorship_monetization_v1` path now joins confirmed exposure,
appeal/purchase-intent lift, and Brand Index context without changing canonical
contracts. It produces five comparable exposure-linked property-wave rows and
a provisional exposure-times-lift allocation scenario. Five observations are
insufficient for a credible exposure-lift regression. Monetary output is gated
and currently empty pending an independently identified attributable Index
change, approved royalty slope, revenue base, fee, discount rate, and
persistence horizon. See
`reports/methods_annex/experimental_sponsorship_monetization_v1.md`.

## Non-blocking but required before final inference

- Blinkfire engagement-rate/post-level specifications must be removed or redesigned around the confirmed impressions/views scope.
- A completed event calendar for 2026 World Cup activations/matches with exact UTC moments; the 2024 stage-reveal time should be verified separately from the publication timestamp.
- Product-launch calendar and other L4 controls.
- Broadcast/GRP exposure, if available; otherwise CV-01/CV-02 remain mandatory.
- Acer historical title mapping or a replacement sixth SCM donor.
- HKEX session/calendar mapping and event-study implementation.
