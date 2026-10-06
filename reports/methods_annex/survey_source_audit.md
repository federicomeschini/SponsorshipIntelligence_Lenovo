# Survey source audit

> **Current as of 2026-10-06:** no new survey exports have been received since this audit.

## Verdict

The consumer-research workbook is usable as a **segmented crosstab source**.
The GWI workbook is usable as a **non-canonical quarterly calibration series**,
using `Foglio1` as the source of truth. Neither workbook is a complete
population brand-equity anchor.

## Integrity

| Workbook | SHA-256 | Status |
|---|---|---|
| `lenovo_fifa_consumer_research_export_2026-05-21.xlsx` | `3c7a066bc263806231cd89e8a04669035bb12bd7903cdd9d0c463cf03104e333` | usable_crosstab_export (981 non-empty cells) |
| `lenovo_gwi_core_tech_brands_crosstab_export_2026-06-09.xlsx` | `f1eac9e09e90c47fe98e22784303079d9c689d4890ea090235fae6fc9587c1ad` | usable_gwi_crosstab_export (1350 non-empty cells) |

## Staged output

- 21 declared crosstab tables: 7 awareness, 7 appeal, 7 purchase-intent.
- 7 distinct filter/wave labels. The export states named months only, not exact fieldwork dates.
- CSV and Parquet artifacts in `data/staged/survey/` retain each source cell, workbook hash, sheet, and Excel coordinate.
- GWI `Foglio1` has 37 quarterly periods (Q1 2017–Q1 2026) for Lenovo engagement and consideration. Its 17 × 41 block exactly matches `Blank!B13:AP29` (697/697 cells); `Foglio1` alone feeds the staged GWI outputs.

## Safe uses

- Compare sponsorship-aware and unaware segments **within the same table and wave**.
- Inspect source distributions and reported `T4B` / `NET` summaries.
- Use Country by Wave only as unweighted sample-composition context.
- Use the GWI engagement and consideration composite to orient and display-scale
  the provisional proxy-led brand-salience index. It does not pin weekly values.

## Do not do this

- Do not treat the output as population-level brand health: every outcome table is segmented by sponsorship awareness.
- Do not recombine segments with `Column n`; the export calls those counts unweighted while the percentages are weighted.
- Do not create a time series by joining the 2024 0-10 scales to the 2025-26 categorical scales.
- Do not infer fieldwork dates, wave comparability, a composite, or funnel-stage scores from these crosstabs beyond what they explicitly report.
- Do not present GWI as a complete survey anchor, direct weekly measurement, or
  causal evidence. Its current role is calibration only.

## Client data still required

A wave-level analytical extract with approved funnel-stage scores (awareness, engagement, appeal, consideration, purchase_intent), exact fieldwork start/end, weights, questionnaire-version metadata, and a comparability crosswalk.
