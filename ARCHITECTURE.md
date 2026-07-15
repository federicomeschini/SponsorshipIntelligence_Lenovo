# ARCHITECTURE.md — Sponsorship ROI Measurement Platform (SRMP)

**Status:** v1.0 — canonical architecture reference
**Owner:** Federico Meschini (OpenEconomics)
**Audience:** autonomous coding agents and human developers working in this repo
**Case study brand:** Lenovo (HKEX 0992.HK / ADR LNVGY) — FIFA World Cup + full sponsorship portfolio

---

## 0. How agents must use this document

1. **This document is the source of truth.** If a task conflicts with this document, stop and flag the conflict in the task output; do not silently deviate.
2. **Methodological choices are locked** unless marked `[OPEN]`. Locked choices are marked `[LOCKED]` with a rationale. Agents may propose changes via `DECISIONS.md` entries but must implement the locked version.
3. **Every module has an interface contract (§6).** Respect input/output schemas exactly. If an upstream artifact violates its schema, fail loudly with a validation error; never coerce silently.
4. **Known failure modes have approved workarounds (§9).** When you hit one of these problems, apply the documented workaround — do not invent a new one without logging a decision.
5. **Guardrails in §11 are hard constraints.** They exist for methodological integrity, not style. Violating them produces outputs that are commercially indefensible.

---

## 1. Problem statement and scope

### 1.1 Objective

Build a BI-like analytical platform that quantifies the **return on sponsorship** for a sponsoring brand of long-duration, World-Cup-like events. The platform must show *why* value was created (exposure → perception → financial performance), not just *that* metrics moved.

### 1.2 The causal chain (the product's spine)

```
Exposure (impressions, engagement)          [Blinkfire, per property, weekly]
        │  stage 1: dose–response
        ▼
Brand perception (Brand Index + funnel stages)    [quarterly survey, disaggregated to weekly]
        │  stage 2: perception–finance link
        ▼
Financial performance                        [abnormal stock returns; income-approach valuation]
```

Every screen, table, and estimate in the platform maps to one arrow or one node of this chain. Anything that does not is out of scope.

### 1.3 In scope

- Weekly mixed-frequency Brand Index construction (survey anchor + high-frequency proxies).
- Exposure→perception elasticity with adstock decay (brand level and property level).
- Event-study financial layer on 0992.HK abnormal returns.
- Synthetic-control / placebo counterfactual layer.
- ROI synthesis via incremental-cash-flow valuation, cross-checked by royalty relief.
- Portfolio benchmarking: FIFA vs. all other Lenovo sponsorship properties.

### 1.4 Out of scope (v1)

- Broadcast/TV audience measurement (Blinkfire covers digital/social/owned; broadcast is a declared blind spot — see R-06).
- Multi-brand cross-sectional models (single-brand design; see R-04).
- Real-time streaming ingestion (batch weekly refresh is sufficient).
- Marketing-mix modelling of non-sponsorship media spend (confounder handled via controls, not modelled structurally).

---

## 2. Design principles `[LOCKED]`

| # | Principle | Consequence |
|---|-----------|-------------|
| P1 | **Exposure is treatment intensity, never monetary value.** | Advertising Value Equivalency (AVE) and Blinkfire's `media_value` field are banned as inputs to any model. They may appear only as an "industry-claimed value" comparison line in the UI. |
| P2 | **Stock prices are never regressed in levels.** | The financial layer operates exclusively on abnormal returns from a factor model (event-study framework). Any regression involving raw or log price levels is a defect. |
| P3 | **Survey and proxy roles must be explicit.** | The current weekly index is proxy-led: the parent-brand proxy supplies weekly movement, while GWI supplies orientation and display-scale calibration. It must not be described as weekly survey measurement or as an interpolation that passes through survey values. Funnel-stage evidence remains at survey frequency. |
| P4 | **Every proxy must pass the validation gate (§5.2) before entering the index.** | No proxy is admitted on plausibility alone. Quarterly correlation with the survey (composite AND stage-level) is a hard gate. |
| P5 | **Causal claims require a counterfactual.** | "Index went up during the event" is descriptive. Causal language in outputs is permitted only for estimates backed by fixed-effects panel variation, event-study abnormal returns, or synthetic control. |
| P6 | **Uncertainty is a first-class output.** | Every estimate ships with confidence/credible bands. The weekly index ships with smoother variance (tight at survey waves, fanning between them). Dashboards must render the bands. |
| P7 | **Honest scope caveats are rendered in the UI**, not buried in an annex. | Broadcast exposure gap, single-brand n, associational stage-2 — each has a standard caveat string (§10.4) attached to the relevant view. |
| P8 | **Reproducibility.** | Deterministic pipelines, pinned dependencies, seeded resampling, raw data immutability (raw → staged → curated, never edit raw). |

---

## 3. Data inventory and contracts

### 3.1 Sources

| ID | Source | Frequency | Grain | Role | Access |
|----|--------|-----------|-------|------|--------|
| D1 | Brand perception survey | Quarterly | brand × funnel_stage × wave | Structural anchor; funnel-stage attribution | Internal (client-provided) |
| D2 | Blinkfire Analytics | Daily→weekly | property × platform × post | Exposure treatment: impressions, engagements, post metadata | API/export |
| D3 | Google Trends | Weekly (stitched) | query × week × geo | Salience/consideration proxy; property-level outcome via co-branded queries | pytrends/gtrends, multi-draw protocol (W-01) |
| D4 | Wikipedia pageviews | Daily | article × language × day | Salience proxy (absolute counts, stable) | Wikimedia REST API |
| D5 | GDELT | Daily | mention-level, aggregated to brand × day | News volume + tone (only signed proxy) | GDELT 2.0 API/BigQuery |
| D6 | Stock market data | Daily | ticker × day | Financial outcome: 0992.HK, HSI, global tech factor, FX | Standard market data provider |
| D7 | Event calendar | Event-level | milestone × date | Event-study windows; adstock pulse dating | Manually curated (`data/reference/events.csv`) |

### 3.2 Key data facts the code must respect

- **D1:** ~8–12 usable waves over the analysis horizon. Stage-level scores REQUIRED, not just the composite. Exact fieldwork dates (start/end) required per wave — the index anchors to the fieldwork midpoint, not the quarter label.
- **D2:** covers ALL Lenovo sponsorship properties (FIFA, F1, MotoGP/Ducati, esports, others). Property taxonomy must be normalized into `property_id`. The `media_value` column is ingested for the comparison line only and is tagged `banned_as_feature: true` in the feature registry.
- **D3:** Trends values are window-normalized 0–100 and resampled per request → non-deterministic. Apply workaround W-01 always.
- **D6:** HKEX trading calendar and timezone. Event timestamps (matches, announcements) must be converted to HKT and mapped to the *next trading session* if outside trading hours (workaround W-07).

### 3.3 Two query families for Google Trends `[LOCKED]`

| Family | Examples | Construct proxied | Maps to funnel stage |
|--------|----------|-------------------|----------------|
| Brand queries | "Lenovo", "联想" (per geo config) | Salience / awareness | awareness |
| Category-purchase queries | "Lenovo laptop", "ThinkPad price", "Lenovo Legion" | Consideration / intent | consideration |
| Co-branded property queries | "Lenovo FIFA", "Lenovo F1", "Lenovo Ducati" | Property-attributed salience | property panel outcome (L4b) |

Never pool families into one headline series. The parent-brand family is the
weekly headline proxy; category-purchase, co-branded and competitor families
remain separate companion observables for product diagnostics, property
outcomes and donor screening.

---

## 4. System architecture — layers

```
L0 Ingestion ─► L1 Validation gate ─► L2 Index construction ─► L4 Elasticity ─► L7 ROI synthesis
                                            │                        ▲
                                            ▼                        │
                                      L3 Adstock/exposure ───────────┘
                                            │
L6 Counterfactual/placebo ◄─────────────────┤
L5 Financial (event study) ◄────────────────┘ (event calendar D7 feeds L3, L5, L6)
```

### L0 — Ingestion and staging

- One connector module per source (`srmp/ingest/{survey,blinkfire,trends,wikipedia,gdelt,market,events}.py`).
- Raw pulls are immutable, timestamped parquet in `data/raw/`. Staged (typed, deduplicated, normalized IDs) in `data/staged/`. Curated analysis tables in `data/curated/`.
- Every connector emits a `pull_manifest.json` (source, query params, pull timestamp, row counts, hash) for reproducibility.

### L1 — Proxy validation gate `[LOCKED]`

Purpose: decide which high-frequency proxies are admitted into index construction.

Procedure (per candidate proxy series):
1. Aggregate proxy to survey-wave frequency using fieldwork-window means (not calendar quarters).
2. Compute Pearson and Spearman correlation with (a) the composite index, (b) EACH funnel-stage score, in levels and in first differences.
3. Admission rule: `|corr| >= 0.4` (differences) with at least one funnel stage, OR `|corr| >= 0.5` (levels) with composite, with sign consistent with theory. Record the best-matching funnel stage as the proxy's `target_stage`.
4. Out-of-sample check: re-estimate the gate excluding the last 2 waves; the admitted set must be stable. Instability → proxy quarantined (`status: watchlist`).
5. Output: `data/curated/proxy_registry.parquet` with columns `proxy_id, family, target_stage, corr_levels, corr_diff, status {admitted, watchlist, rejected}, decided_at`.

Notes for agents:
- Expect casualties. Trends brand queries typically correlate 0.5–0.7 with awareness funnel stages and ~0 with affinity funnel stages. A rejection is a valid, reportable result.
- Validate against FUNNEL STAGES first; composite-only validation wrongly discards good stage-specific instruments.
- With n≈8–12 waves, do not report p-values as if asymptotics held; report correlations with bootstrap intervals and treat the gate as a screening device, not inference.

### L2 — Index construction (proxy-led, survey-calibrated)

**Quarterly calibration series.** Standardize the available GWI engagement and
consideration series over their full 2017–2026 history and aggregate them with
PC1. This is a non-canonical, two-stage survey composite used only to orient and
display-scale the weekly proxy. It is not treated as a complete brand-equity
anchor.

**Weekly headline index `[CURRENT]`.**
- Construct: Lenovo brand salience, not total brand equity.
- Weekly movement: worldwide Google Trends interest for the exact parent-brand
  query `Lenovo`, after W-01 overlap-window rescaling and robust averaging.
- Calibration: aggregate the weekly proxy to quarter, estimate a positive
  affine mapping to the GWI composite, then display on the survey composite's
  mean-100 / SD-15 scale. Survey points do not pin or interpolate individual
  weeks.
- Uncertainty combines the quarter-level calibration residual with the observed
  dispersion across overlap-rescaled Trends windows. Those windows are
  alternate normalisations, not independent repeated draws.
- Product, price, co-branded and competitor queries are companion series and
  are not pooled into the headline index. Wikipedia and GDELT remain excluded
  after failing the direction/stability screen against the available GWI
  composite.

**Acceptance criteria.** Positive calibration slope; at least eight overlapping
quarters; leave-one-quarter sensitivity report; all finished W-MON weeks
present; non-zero uncertainty; source and exclusions recorded in the manifest.
Forecast performance is not an acceptance criterion for this descriptive index.

### L3 — Exposure and adstock

- Aggregate Blinkfire to `property_id × week`: `impressions`, `engagements`, `engagement_rate = engagements/impressions`, `posts`.
- Adstock transform `[LOCKED functional form]`: geometric decay `A_t = x_t + δ A_{t-1}`, with `δ ∈ (0,1)` estimated (grid search over δ maximizing stage-1 fit, or NLS). The estimated half-life `ln(0.5)/ln(δ)` is a first-class reportable ("sponsorship halo half-life").
- Produce both per-property adstock and total brand adstock (sum across properties).
- Volume metrics (impressions) proxy reach; `engagement_rate` proxies affinity — keep both, never divide one role to the other.

### L4 — Elasticity (stage 1: exposure → perception)

**L4a — brand-level distributed lag.** Weekly index (from L2) on adstocked total exposure + controls:
`ΔBI_t = β·log(1 + A_t) + γ'·controls_t + seasonal terms + e_t`
- Controls: product-launch dummies, GDELT tone (to absorb news shocks), quarter dummies.
- Use HAC (Newey–West) standard errors; lag length by data-driven rule, logged.
- Deliverable: dose–response curve (X incremental impressions → Y index points) with bands, plus the decay curve from L3.

**L4b — property-level fixed-effects panel `[the identification core]`.**
- Panel: `property_id × week`. Outcome: co-branded Trends series (D3 family 3) and property engagement rate. Treatment: property adstocked exposure.
- Specification: `y_{p,t} = β·log(1 + A_{p,t}) + α_p + τ_t + ε_{p,t}` — property FE absorb property popularity levels; week FE absorb brand-wide shocks (product launches, macro news). Estimate with `fixest::feols` (preferred) with two-way clustered SEs (property, week).
- This is the regression that answers "is FIFA worth it relative to F1/Ducati/esports?" Report per-property β heterogeneity via interactions or split samples.

### L5 — Financial layer (stage 2: perception/events → abnormal returns)

- Factor model estimated on pre-event window (≥120 trading days, ending ≥10 days before event): `r_t = a + b·r_HSI,t + c·r_globaltech,t + ν_t`. Global tech factor: MSCI ACWI IT or NASDAQ-100 in HKD terms — pick once, log in DECISIONS.md.
- Compute AR/CAR over windows `[-1,+1]`, `[-2,+5]`, `[0,+10]` around D7 milestones (partnership announcement 2023, tournament start, brand-relevant matches, activation launches). Standard tests: Boehmer–Musumeci–Poulsen (BMP) t; nonparametric rank test as robustness.
- Perception–finance link: regression of CARs (or quarterly abnormal returns) on Δ index is ASSOCIATIONAL at n≈waves. It is reported with the low-power caveat (§10.4/C-03) and complemented by literature-calibrated elasticities. Never headline it.
- **Profit bridge:** when direct company financials are available, relate changes in the Index to changes in revenue, adjusted profit or margin with category-demand, market, FX and seasonality controls. Stock price levels are never a profit proxy. Any single-company quarterly coefficient is a low-power reasonableness check and cannot replace an identified with-and-without cash-flow model, BCF or royalty-relief calibration unless it is stable across registered specifications.
- **Stock-response diagnostic:** estimate abnormal returns from a rolling prior-only factor model; isolate unexpected Index changes from prior-only forecasts; evaluate frozen 0/1/4/13-week cumulative-return horizons with earnings and campaign controls, overlapping-horizon HAC uncertainty, family-wise adjustment, reverse-timing placebo and endpoint/influence stability. A coefficient maps Index innovation to equity return, never directly to profit.

### L6 — Counterfactual and placebo layer

- **Brand counterfactual:** the donor pool is made only of comparable competitor-brand salience proxies with no known exposure to the Lenovo-FIFA treatment. It estimates the missing no-FIFA Lenovo Brand Index path. Blinkfire properties and co-branded property searches are never donor units.
- **Exposure controls:** after the donor weights are frozen, Blinkfire is aggregated into FIFA treatment intensity and all-other-Lenovo-sponsorship intensity. FIFA adstock weights the candidate Index gap; FIFA and non-FIFA adstock can enter a downstream timing regression that is explicitly descriptive because activation timing is endogenous.
- **Donor measurement and confounders:** comparison requests share a repeated Lenovo anchor and are mapped to one request scale before pre-treatment standardisation. Zero-heavy/constant series and treatment-contaminated brands are excluded through versioned quality and evidence registries. Lenovo product, corporate and promotion event indicators enter downstream timing and exclusion sensitivities, never the donor-weight fit.
- **Placebo bank `[LOCKED]`:** donor brands and fake treatment dates test the Brand Index counterfactual. Non-FIFA properties and quiet/race weeks belong to the separate property-mechanism layer; they may validate exposure-response timing but cannot represent Lenovo's untreated Brand Index. All placebo results are archived and summarized in the methods annex.

### L7 — ROI synthesis (income approach) `[LOCKED logic]`

1. Take the sponsorship-attributable Δ index from L6 (or its scenario distribution).
2. **Primary direct route when operating inputs exist:** estimate price, volume, retention/service, attributable cost-saving, activation-cost, tax and working-capital differences between with-sponsorship and without-sponsorship forecasts. Discount incremental after-tax free cash flow over the supported persistence horizon.
3. **Royalty-relief cross-check:** map Δ index to an implied royalty-rate change using the approved perception–royalty schedule, apply it to the consistent brand-attributable revenue base, and discount it over the same horizon.
4. If a multi-period excess-earnings route is used, deduct contributory asset charges and prohibit double counting with customer, technology and other intangible returns.
5. **Operational planning fallback:** when granular operating inputs are unavailable, translate the weekly sponsorship-attributable BI innovation path through a nonnegative distributed stock-response curve. Use a pre-outcome calibration for the base case, dated market capitalisation, full response maturation and explicit future-contract scenarios. A one-off average-gap multiplication is prohibited.
6. ROI multiple = incremental brand value / sponsorship fee. Stock CARs from L5 are corroborating market evidence; only the explicitly labelled dynamic fallback may translate them into market-implied planning value.
7. Sensitivity analysis is mandatory: tornado over attribution, operating elasticities, WACC, persistence and method-specific assumptions.

---

## 5. Repository layout

```
srmp/
├── ARCHITECTURE.md          # this file — canonical reference
├── DECISIONS.md             # append-only decision log (ADR-style)
├── config/
│   ├── base.yaml            # global config (schema §7)
│   ├── queries_trends.yaml  # query families × geos
│   └── events.csv → symlink to data/reference/events.csv
├── data/
│   ├── raw/                 # immutable pulls + pull_manifest.json
│   ├── staged/              # typed, normalized
│   ├── curated/             # analysis-ready (proxy_registry, panels, index)
│   └── reference/           # events.csv, property taxonomy, ticker map
├── srmp/
│   ├── ingest/              # one connector per source (L0)
│   ├── validation/          # proxy gate (L1)
│   ├── index/               # composite.py / proxy_led.py (L2)
│   ├── exposure/            # adstock, aggregation (L3)
│   ├── elasticity/          # brand_dl.py, property_panel.R (L4)
│   ├── financial/           # factor_model.py, event_study.py (L5)
│   ├── counterfactual/      # scm.py, placebos.py (L6)
│   ├── roi/                 # royalty_relief.py, sensitivity.py (L7)
│   └── viz/                 # dashboard data contracts + chart builders
├── reports/
│   ├── placebos/
│   └── methods_annex/
└── tests/                   # schema tests, golden-number regression tests
```

Language policy: Python default; R permitted for `tempdisagg` and `fixest` modules, invoked via reproducible scripts (no interactive-only steps). Any cross-language handoff goes through parquet with schema files.

---

## 6. Module interface contracts

All curated artifacts are parquet with an accompanying `schema.yaml`. Core contracts:

**C-INDEX (L2 output)**
`week (date, W-MON) | index_level (float) | index_se (float) | source_version (str) | anchored (bool)`
Invariant: weekly movement comes from the configured parent-brand Trends proxy;
survey data calibrate orientation and scale but do not anchor individual weeks;
survey convergence and leave-one-quarter sensitivity are documented.

**C-EXPOSURE (L3 output)**
`property_id | week | impressions | engagements | engagement_rate | posts | adstock_impressions | delta_used`
Invariant: adstock recomputable from impressions + delta_used.

**C-PANEL (L4b input)**
`property_id | week | y_trends_cobrand | y_engagement_rate | adstock_impressions | covariates...`
Balancedness report required; unbalanced panels allowed but documented.

**C-EVENTSTUDY (L5 output)**
`event_id | window | CAR | CAR_se | test_stat | test {BMP, rank} | pre_window | factors_used`

**C-ROI (L7 output)**
`scenario_id | valuation_method | delta_index_attrib | incremental_fcf_or_royalty | incremental_value | fee | roi_multiple | assumptions_hash`

**C-VIZ** — each dashboard layer (§8) consumes ONLY curated contracts; no viz module may recompute statistics.

---

## 7. Config schema (base.yaml, excerpt)

```yaml
brand:
  name: Lenovo
  ticker: "0992.HK"
  adr: "LNVGY"
  survey_funnel: [awareness, engagement, appeal, consideration, purchase_intent]
horizon: {start: 2022-01-01, end: null}
index:
  version: v4_proxy_led_brand_calibrated
  frequency: W-MON
  stability_review: leave_one_quarter_out
  headline_query: brand_lenovo
validation_gate:
  corr_diff_threshold: 0.4
  corr_level_threshold: 0.5
  bootstrap_reps: 2000
adstock:
  functional_form: geometric
  delta_grid: {min: 0.5, max: 0.98, step: 0.02}
event_study:
  estimation_window_days: 120
  gap_days: 10
  windows: [[-1, 1], [-2, 5], [0, 10]]
  factors: [HSI, GLOBAL_TECH]
trends:
  draws_per_query: 10
  stitch_overlap_weeks: 26
roi:
  royalty_schedule: config/royalty_schedule.yaml
  persistence_multiplier: 2.0
banned_features: [blinkfire.media_value]
```

---

## 8. What the platform shows (dashboard layer map)

| View | Content | Feeds from | Mandatory caveat |
|------|---------|-----------|------------------|
| V1 Exposure timeline | impressions/engagement per property, cumulative + adstocked, event markers | C-EXPOSURE, D7 | CV-01 (broadcast gap) |
| V2 Brand Index | weekly index with uncertainty bands, survey anchor dots, funnel-stage decomposition at waves (LMG shares) | C-INDEX, Tier A | — |
| V3 Dose–response | elasticity curve + decay/half-life chart | L4a | CV-02 (owned-channel bias) |
| V4 Portfolio benchmark | per-property β, FIFA vs. rest, co-branded search lift panels | L4b | — |
| V5 Financial events | CAR charts around milestones, factor-model diagnostics | C-EVENTSTUDY | CV-03 (associational stage 2) |
| V6 Counterfactual | actual vs. synthetic gap chart; placebo distribution | L6 | CV-04 (proxy-based SCM) |
| V7 ROI | incremental-cash-flow waterfall, royalty cross-check, ROI multiple, tornado sensitivity | C-ROI | CV-05 (assumption-driven) |
| V0 Industry comparison | Blinkfire media_value line vs. model-implied value | D2 | labelled "industry-claimed (AVE), not endorsed" |

---

## 9. Known risks, failure modes, and approved workarounds

| ID | Problem | Approved workaround |
|----|---------|---------------------|
| W-01 | **Google Trends non-determinism** (window-normalized 0–100, resampled per request; two pulls differ) | Pull `draws_per_query` independent draws (rotate sessions/days), average. For long histories: chain overlapping windows — pull coarse (5y) and fine (90d) granularities, splice via overlap-ratio rescaling. Persist every raw draw; the averaged/stitched series is a curated artifact with `draws_used` metadata. |
| W-02 | **Frequency mismatch** (quarterly survey vs. daily/weekly everything else) | Two-tier design (§4-L2). Analyses run at the natural frequency of each layer: index weekly, event study daily, funnel-stage attribution quarterly. Never interpolate the survey linearly; only via L2 models. |
| W-03 | **Tiny n at survey frequency (~8–12 waves)** | No asymptotic inference at wave frequency: bootstrap intervals, screening-not-testing language for the gate. Stage-2 index→returns regression is reported as associational + literature-calibrated (Cornwell/Pruitt/Clark stream) — never as an in-house causal estimate. |
| W-04 | **Single-brand design / no counterfactual by default** | Identification stack, in order of credibility: (1) L4b property FE panel (within-brand, across-property variation) — primary; (2) event-study abnormal returns — dated causal moments; (3) proxy-based synthetic control — flagship visual, gated on donor pool ≥ 5; (4) placebo bank — credibility audit. |
| W-05 | **Spurious regression risk on trending series** | Index and adstock enter regressions in differences or with deterministic trend controls; unit-root screening (ADF/KPSS) logged per series; never regress two levels series without cointegration justification (which is out of scope → so never). |
| W-06 | **Broadcast/earned exposure not in Blinkfire** (biggest World Cup exposure component missing) | Declared blind spot: caveat CV-01/CV-02 on affected views. Elasticities are labelled "per owned/social impression, upward-biased if broadcast co-moves". `[OPEN]` optional extension: ingest GRP/broadcast audience data if client provides; schema slot reserved in C-EXPOSURE (`channel` column). |
| W-07 | **HKEX timezone/calendar vs. event timestamps** | All D7 timestamps stored in UTC + local tz; mapping rule: event → first HKEX trading session with a close AFTER the event moment. Half-day sessions and HK holidays from exchange calendar package. Unit-tested. |
| W-08 | **Blinkfire media_value contamination** | Column ingested but registered in `banned_features`. CI test fails the build if any model artifact lists it among regressors/features. Appears only in V0 comparison view. |
| W-09 | **Trends geo/language composition drift** | Query families defined per geo in `queries_trends.yaml` (incl. "联想" for CN where Google coverage is unreliable → flag CN as low-quality geo; prefer Wikipedia zh pageviews for CN salience). Composition fixed by config version; changes require a DECISIONS.md entry. |
| W-10 | **Proxy structural breaks** (Wikipedia redesigns, GDELT ingest changes, Trends rebasing) | Break detection (Bai–Perron or simple CUSUM) on every proxy at refresh; detected break → proxy auto-moved to `watchlist`, index re-estimated without it, alert emitted. |
| W-11 | **Endogenous exposure timing** (posts spike when brand news is good) | GDELT tone as control in L4a; week FE in L4b absorb brand-wide shocks; robustness: re-estimate excluding product-launch weeks. Documented residual risk. |
| W-12 | **Proxy calibration drift** | Re-run convergence and leave-one-quarter sensitivity diagnostics at every refresh. A non-positive calibration slope, unstable sign, or material dependence on a single survey quarter triggers review before publication. |
| W-13 | **Survey methodology changes between waves** (sample, questionnaire) | Preserve the wave metadata and recompute the calibration only across comparable GWI quarters. A composition change requires a new index version and back-series review. |

---

## 10. Validation and acceptance criteria

### 10.1 Per-module gates (CI-enforced where possible)

- **L1:** proxy_registry reproducible from raw draws; admitted set stable under 2-wave exclusion.
- **L2:** positive survey calibration; leave-one-quarter stability reported;
  overlap-window uncertainty retained; no family pooling. Forecast accuracy is
  optional nowcasting research, not an index gate.
- **L3:** adstock recomputable; δ within grid interior (boundary solution → flag).
- **L4a:** HAC SEs; residual autocorrelation diagnostics reported.
- **L4b:** two-way clustered SEs; FE panel passes negative-placebo test (quiet weeks β ≈ 0 within CI).
- **L5:** estimation-window R² and factor loadings reported; BMP and rank tests agree in sign or the disagreement is reported.
- **L6:** placebo distribution archived; main estimate outside placebo 90% envelope or effect is reported as "not distinguishable from placebo".
- **L7:** ROI reproducible from `assumptions_hash`; tornado covers all locked assumption parameters.

### 10.2 Golden-number tests

Once a layer's output is validated by a human, freeze key numbers (e.g., δ̂, β̂ per property, CAR for the announcement event) as golden values with tolerances in `tests/golden/`. Refactors must reproduce them; data refreshes update them via an explicit, logged regeneration step.

### 10.3 Language discipline in outputs

- "caused / effect of" → only L4b (within CI), L5 CARs, L6 SCM.
- "associated with" → L4a brand-level, stage-2 index→returns.
- "industry-claimed" → anything derived from media_value/AVE.

### 10.4 Standard caveat strings (render verbatim)

- **CV-01:** "Exposure covers digital/social/owned channels (Blinkfire). Broadcast audience is not measured and typically dominates World Cup exposure."
- **CV-02:** "Elasticities are per owned/social impression; if broadcast exposure co-moves with digital exposure, these estimates are upper bounds."
- **CV-03:** "The perception-to-returns link is estimated on few quarterly observations and is associational; magnitudes are calibrated against the published sponsorship event-study literature."
- **CV-04:** "The synthetic counterfactual is built from public high-frequency proxies of competitor salience, not from competitor survey data."
- **CV-05:** "ROI depends on the selected income method, attribution, operating or royalty assumptions, discount rate and persistence; see sensitivity panel."

---

## 11. Agent guardrails — hard constraints

**MUST NOT**
1. Use `blinkfire.media_value` (or any AVE-style monetary exposure valuation) as a model input. (P1, W-08)
2. Regress stock prices in levels, or include stock returns/prices as an input to the Brand Index. (P2; circularity)
3. Interpolate the survey linearly or describe GWI calibration points as weekly anchors. (P3)
4. Admit a proxy into L2 that has not passed the L1 gate, or keep one that a structural-break check has quarantined. (P4, W-10)
5. Use causal language for L4a brand-level or stage-2 estimates. (§10.3)
6. Pool Trends query families, or mix geos outside the config composition. (§3.3, W-09)
7. Report wave-frequency p-values as valid asymptotic inference. (W-03)
8. Silently coerce schema violations, edit files under `data/raw/`, or
   publish C-INDEX after a non-positive or unstable calibration review. (P8, W-12)
9. Drop uncertainty bands from any estimate surface or dashboard view. (P6)
10. Hard-code event dates, tickers, thresholds, or query strings outside `config/` and `data/reference/`.

**MUST**
1. Fail loudly on contract violations with the contract ID in the error message.
2. Append a DECISIONS.md entry (ADR format: context, decision, alternatives, consequences) for any choice not fixed here, and for any `[OPEN]` item you resolve.
3. Attach the relevant CV-xx caveat string to every new output view.
4. Emit pull manifests, seeds, and `assumptions_hash` so any number in the platform is reproducible end-to-end.
5. Run the placebo bank after any change to L2–L4 estimation code.

---

## 12. Open items `[OPEN]`

| ID | Question | Blocking? | Notes |
|----|----------|-----------|-------|
| O-01 | Exact survey wave dates + stage-level scores availability | YES — blocks L1/L2 | First data request to client. Composite-only delivery degrades the design (validation gate weakens; funnel-stage states impossible). |
| O-02 | Global tech factor choice (MSCI ACWI IT vs. NDX in HKD) | No | Decide at L5 build; log ADR. |
| O-03 | Income-approach inputs | Blocks L7 only | Obtain product/geography operating drivers for with-and-without valuation and an approved royalty schedule for the independent cross-check. |
| O-04 | Broadcast/GRP data availability from client or FIFA | No (v2 feature) | Schema slot reserved (`channel`). |
| O-05 | SCM donor pool: which competitor set has usable Trends/Wikipedia series | No | Screen HP, Dell, Asus, Acer, Samsung (PC line), Huawei — check query ambiguity ("Dell" is clean, "Apple" is not a donor). |
| O-06 | Single-language pipeline vs. Python+R | No | Default Python+R (fixest, tempdisagg are best-in-class); revisit if deployment constraints emerge. |

---

## 13. References (methodological anchors)

- Cornwell, T.B., Pruitt, S.W., Clark, J.M. — sponsorship announcements and shareholder value (event-study stream). Basis for L5 design and W-03 calibration.
- Chow, G., Lin, A. (1971) — best linear unbiased interpolation; `tempdisagg`. Basis for L2 v1.
- Boehmer, Musumeci, Poulsen (1991) — event-study test robust to event-induced variance. L5 tests.
- Abadie, Diamond, Hainmueller — synthetic control methods. L6.
- Broadbent, S. — adstock/geometric decay in advertising response. L3.
- ISO 10668 — monetary brand-valuation framework; IVS 210 — intangible-asset income methods including excess earnings, relief from royalty, premium profit and with-and-without. L7.
- Grömping, U. — LMG / dominance analysis (relaimpo). Tier A attribution.
