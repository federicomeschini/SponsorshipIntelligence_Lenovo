# VISUALIZATION.md — SRMP Front End (PoC / Demo Product)

**Status:** v2.1 — canonical reference for the demo front end. **Implemented in
`frontend/`** (see `frontend/README.md`); deviations from v2.0 are logged in
`frontend/DECISIONS.md` (FE-001…FE-006) and folded into §2.1, §5 and §6 below.
**Owner:** Federico Meschini (OpenEconomics)
**Audience:** autonomous coding agents and human developers building the SRMP demo dashboard
**Track:** `demo` — this front end is a **proof of concept with embedded illustrative data**. It is decoupled from the canonical C-VIZ pipeline in `ARCHITECTURE.md` §6/§8, which remains the target for the production build.

---

## 0. How agents must use this document

1. **This is a product demo, not a reporting surface.** The goal is to make a sponsor say "I want this." Build it to feel like a shipped commercial product: polished, confident, fast, opinionated. Do not build it like a methods annex.
2. **All data is embedded in the app.** There is no live pipeline, no export step, no backend, no refresh. A single demo-data module (§2) contains the full dataset: real pipeline outputs where they exist today, simulated fills everywhere else. Numbers on screen are illustrative by design.
3. **Demo copy is executive copy.** The hedged, badge-heavy language required of canonical outputs (`ARCHITECTURE.md` §10.3–10.4) applies to production artifacts, **not** to this demo. Here, results read as results: "Sponsorship lifted the Brand Index by +1.0 points." Rules in §4.
4. **Isolation rule (the one hard constraint kept from the parent doc):** demo data lives only under `frontend/src/demo-data/` and is never written into `data/raw|staged|curated`, never imported by any `srmp/` module, and never described in client deliverables as measured results. One discreet demo notice exists (§4.4) — a single footer line, nothing more. This is what lets everything else in the demo be fully confident.
5. **Brand identity comes from the brand guideline skill in this repo.** Read it before writing any CSS or choosing any color/typeface; it wins every identity decision. The general `frontend-design` skill guides craft (hero, typography, motion) where the brand skill is silent.
6. **When in doubt, choose the choice a product designer would make, not the one an econometrician would make.** If a chart, number, or sentence makes the demo feel tentative, cut or rewrite it.

---

## 1. Product intent and positioning

**What this is:** a sponsorship ROI intelligence platform — a BI product a rights holder / sponsored entity uses to show its sponsors, in one guided experience, the value their sponsorship created. The demo tells that story end-to-end with the Lenovo × FIFA case study.

**The narrative spine** (also the navigation order):

```
REACH        →   ATTENTION        →   PERCEPTION       →   VALUE          →   RETURN
Exposure         Search & media       Brand Index +        Counterfactual     Financial impact
delivered        salience             audience funnel      proof              & ROI
(V1)             (V2)                 (V3, V4)             (V5)               (V6)
```

Every screen answers a sponsor question:

| Screen | Sponsor question | Money shot |
|--------|-----------------|------------|
| Overview | "What did I get, in one glance?" | KPI hero strip + headline value figure |
| V1 Reach | "How many people saw us?" | Cumulative exposure counter climbing across the partnership |
| V2 Attention | "Did people care?" | Brand Index line with sponsorship milestones lighting it up |
| V3 Perception | "Did it change minds?" | Aware-vs-unaware funnel with big green lift deltas |
| V4 Portfolio | "How does this property compare?" | FIFA vs. the rest of the portfolio, per-property return |
| V5 Proof | "Would this have happened anyway?" | Actual vs. no-sponsorship counterfactual, shaded gap = created value |
| V6 Return | "What's it worth?" | Value waterfall ending in the ROI multiple |

**Tone target:** the confidence of a top-tier consumer analytics product. Numbers are large, resolved, and singular. Insights are stated, not hedged. Sponsors leave the demo remembering three numbers: total impressions, Brand Index lift, and the ROI multiple.

---

## 2. Embedded demo dataset

### 2.1 Structure

One module owns all data: `frontend/data/`, exporting one object per view plus a shared `timeline` (weekly, 2022-01 → **2026-12**, W-MON — extended past the 2026-07-19 final so the §2.3 persistence plateau and post-tournament wave are visible, FE-003) and `events` array. Everything is deterministic — real series are extracted once (`frontend/scripts/extract_real_data.py`) and simulated series are generated once by a seeded script (`frontend/scripts/generate-demo-data.mjs`, seed committed) and checked in as static JS, so the demo renders identically everywhere with zero runtime generation.

### 2.2 Real pipeline outputs to embed (current stage)

Embed these as-is; they are the backbone the simulated fills are shaped around. Source values from the current curated artifacts / DECISIONS.md:

| Dataset | Content | Use in demo |
|---------|---------|-------------|
| Weekly Brand Index (v4 proxy-led) | 235 weeks, 2022–2026, level + band | V2 headline line |
| Quarterly survey composite (GWI PC1) | 2017–2026 quarterly points | V2 "validated against independent survey research" dot overlay |
| Blinkfire exposure | daily→weekly impressions & views, 13 properties, FIFA + portfolio | V1, V4; FIFA vs. rest split |
| Sponsorship funnel lift | appeal +33 to +48 pp, purchase intent +28 to +41 pp, per property × wave | V3 lift deltas |
| Counterfactual gap | synthetic vs. actual around 2024-10-15; +1.033 Index pts (exposure-weighted), pre-fit RMSPE 0.244 | V5 gap chart + "created Index points" callout |
| Donor panel | 11 jointly scaled competitor salience series | V5 background context ("versus the market") |
| Earnings calibration | +US$6.253m annual earnings-equivalent per Index point; +1.033 pts ⇒ +US$6.46m/yr | V6 monetization step |
| Event calendar | announcement, FCWC, World Cup official 104-match calendar, campaigns | milestone markers everywhere |
| GDELT news volume/tone | 1,634 daily obs | V2 secondary "earned media" strip |

### 2.3 Simulated fills (generate; keep internally consistent)

Where the pipeline has gaps, the demo fills them with plausible, internally consistent simulated data so **no screen is ever empty, blocked, or apologetic**:

| Gap | Simulated fill | Consistency rules |
|-----|---------------|-------------------|
| Broadcast/TV exposure | Weekly broadcast audience series peaking at World Cup match weeks; ~6–8× digital exposure during tournament | Peaks align to the embedded official match calendar; decays with the same adstock shape as digital |
| World Cup tournament outcome | Brand Index tournament arc: build-up ramp, peak lift ≈ +2.5 pts around finals, decay to a persistent ≈ +0.8 pts plateau | Pre-tournament path continues the real embedded series; counterfactual continues the real synthetic donor path |
| Engagement metrics | Weekly engagements + engagement rate per property (D2 supplies only impressions/views) | Rates in realistic social ranges (0.5–4%), higher on match weeks |
| Post-tournament survey wave | One additional funnel wave showing lift growth vs. prior waves | Deltas extend the real 2024–2026 lift trajectory, same scale |
| Royalty schedule | 4-point Index→royalty-rate curve | Monotonic; consistent with the V6 waterfall |
| ROI inputs | Sponsorship fee, activation cost, persistence horizon (2 yrs), discount rate | Chosen so ROI multiple lands ≈ 3–4× — credible, not absurd |
| Portfolio returns | Per-property value-per-impression for F1, MotoGP/Ducati, esports, others | FIFA best-in-portfolio but not implausibly dominant (e.g., 1.4–1.8× median) |

Generation rules: seeded; weekly grain on the shared timeline; realistic noise (no perfectly smooth synthetic look); every simulated series visually coherent with the real series it touches (levels, volatility, seasonality). If a simulated number and a real number appear on the same screen, they must not contradict each other.

### 2.4 Non-goals

No parquet reading, no `srmp/viz/export.py`, no bundle provenance blocks, no status enum, no blocked-state components, no Methods mode. Those belong to the production track and return when the platform moves off embedded data.

---

## 3. Screen catalog

General rules for every screen: one hero element (the money shot), a short stated insight sentence under the title, supporting charts below the fold, milestone markers from the shared `events` array, smooth entrance animation on first load, and export-to-image on every chart. Uncertainty bands stay on the Brand Index and counterfactual charts — rendered as a sleek confidence ribbon (it reads as rigor, which sells) — but nowhere does copy dwell on them.

### V0 — Overview (landing)
- **Hero:** full-bleed partnership header (per brand skill) + KPI strip of five big numbers: total impressions delivered, broadcast audience reached, Brand Index lift (+1.0 pts), brand value created (US$ figure from V6), ROI multiple (≈ 3–4×).
- **Below:** miniature sparkline row previewing each section (reach, attention, perception, value, return), each clicking through to its screen. A "partnership timeline" ribbon with the announcement, FCWC, and World Cup as glowing milestones.
- **Insight line:** e.g. "The FIFA partnership reached 2.1B cumulative impressions and lifted Lenovo's Brand Index by +1.0 points — US$6.5M in annual brand-driven earnings."

### V1 — Reach (exposure delivered)
- **Hero:** cumulative exposure area chart (digital + broadcast stacked), counter animating to the total on load. World Cup weeks visibly dominate.
- **Supporting:** per-property weekly exposure small multiples (13 properties); FIFA vs. rest-of-portfolio share donut; adstock overlay toggle framed as "attention carryover" with the half-life stated as a feature ("your exposure keeps working for N weeks after each activation").
- **Insight line:** stated totals — impressions, broadcast audience, share of voice during tournament weeks.

### V2 — Attention (brand salience)
- **Hero:** the weekly Brand Index line (embedded real series + simulated tournament arc), confidence ribbon, sponsorship milestones lighting the line where lifts occur. Quarterly survey dots overlaid, labelled simply "independent survey research" — framed as validation, one line: "tracks independent survey measurement across 17 quarters."
- **Supporting:** earned-media strip (GDELT news volume with tone coloring); search-interest panel for product/purchase queries ("commercial intent") as a companion chart.
- **Insight line:** e.g. "Brand attention peaked at an all-partnership high during the World Cup and holds +X pts above the pre-partnership baseline."

### V3 — Perception (audience impact)
- **Hero:** funnel diagram (awareness → engagement → appeal → consideration → purchase intent) with sponsorship-aware vs. unaware audiences side by side and large green delta chips on appeal (+33–48 pp) and purchase intent (+28–41 pp).
- **Supporting:** lift by property × wave heat strip; the simulated post-tournament wave extending the trajectory upward; audience quote-style stat cards ("fans exposed to the sponsorship are ~2× as likely to consider Lenovo").
- **Framing:** "audiences who experienced the sponsorship vs. those who didn't" — plain comparative language, no methodology talk.

### V4 — Portfolio (property benchmark)
- **Hero:** per-property return chart — value created per million impressions, FIFA highlighted, sorted descending.
- **Supporting:** exposure-vs-lift scatter (bubble = fee tier, simulated); property cards with each property's signature stat; a "portfolio mix" view showing FIFA's share of total portfolio value vs. share of spend.
- **Insight line:** e.g. "FIFA delivers the portfolio's highest value per impression — 1.6× the portfolio median."

### V5 — Proof (counterfactual)
- **Hero:** actual vs. "without sponsorship" line pair; the gap between them shaded and labelled "value created by the partnership"; the +1.0 Index-point callout anchored to the announcement, extending through the simulated tournament arc (+2.5 peak, +0.8 persistent).
- **Supporting:** "versus the market" panel — Lenovo against the 11-competitor salience benchmark, indexed to the announcement week (Lenovo pulls away); a one-line method credential: "counterfactual built from 11 competitor brands using synthetic-control methodology" (name-drop the method as a credibility asset, then move on).
- **Insight line:** "Without the partnership, Lenovo's brand trajectory tracks the competitor market. With it, Lenovo breaks away."

### V6 — Return (financial impact & ROI)
- **Hero:** value waterfall: Index points created → annual earnings-equivalent (US$6.25M per point) → persistence horizon → gross brand value → minus fee & activation → **net value and ROI multiple** as the terminal, largest number on the screen.
- **Supporting:** royalty cross-check card ("an equivalent licensing view values the uplift at US$X–Y") using the simulated schedule; scenario slider (conservative / base / ambitious) that re-runs the waterfall live — interactivity here is the wow moment; sensitivity tornado styled as a compact "what moves the number" panel.
- **Insight line:** e.g. "Every US$1 of sponsorship investment returned US$3.40 in brand value."

### V7 — About the platform (secondary nav)
- One elegant page: the causal chain diagram (exposure → perception → financial performance), the data sources as logo/credential row (survey research, social analytics, search, news, market data), and a short "how we measure" section in product language (three paragraphs, no formulas). This is the sales page for the methodology, not the methods annex.

---

## 4. Language rules (demo register)

### 4.1 Voice
Confident, declarative, sponsor-facing. Insights are conclusions, not hypotheses. Active voice, present tense for the product, past tense for results. Every screen's insight line is a complete sentence a CMO could repeat in a board meeting.

### 4.2 Say / avoid

| Say | Avoid |
|-----|-------|
| "The partnership lifted the Brand Index by +1.0 points." | "candidate estimate", "not distinguishable from placebo", "associational" |
| "Value created: US$6.5M per year." | "market-implied earnings-equivalent under a zero-floored planning constraint" |
| "Without the sponsorship, Lenovo tracks the market." | "the donor-placebo screen passes at its finite-sample boundary" |
| "Validated against independent survey research." | "non-canonical constructed anchor" |
| "Attention carryover: exposure keeps working for N weeks." | "geometric adstock decay parameter δ" |
| "Audiences exposed to the sponsorship" | "sponsorship-aware self-selected segment" |

Econometric vocabulary appears at most once per screen, as a credential ("synthetic-control methodology"), never as a hedge. No badges, no status chips, no caveat blocks, no blocked states, no p-values on screen.

### 4.3 Numbers
Big numbers get big treatment: animated count-up, compact notation (2.1B, US$6.5M, 3.4×), one decimal max on Index points, zero decimals on percentages. One hero number per screen; supporting numbers visibly subordinate.

### 4.4 The single demo notice
Exactly one, and only one: a discreet persistent footer line — **"Demonstration environment · illustrative data"** — set in the smallest text style the brand skill allows. It never appears in chart areas, exports may keep it in the image footer margin. Nothing else in the product references simulation, PoC status, or data provenance. This one line is deliberate: it keeps the demo safe to circulate while leaving every screen fully confident.

---

## 5. Look, feel, and craft bar

1. **Brand skill first.** All palette, typography, logo, spacing, and tone decisions come from the brand guideline skill. The tokens below are semantic slots the theme maps to brand values: `--surface`, `--surface-raised`, `--text-primary`, `--text-secondary`, `--series-headline`, `--series-counterfactual`, `--series-benchmark`, `--ribbon-confidence`, `--delta-positive`, `--marker-milestone`, `--hero-accent`.
2. **Final-product polish bar:** custom-designed empty-of-nothing screens (everything populated per §2.3); loading skeletons; 60fps chart animation; hover states on every interactive element; responsive to 1280px+ (demo runs on a laptop/projector — mobile is out of scope for the PoC). No dark app theme — the brand system defines dark *sections* only, used for the V0 hero and V6 ROI terminal (FE-005).
3. **Signature moments (spend the boldness here):** the Overview KPI count-up on first load; the V5 counterfactual "break-away" reveal (the without-sponsorship line draws first, then actual pulls away and the gap fills); the V6 scenario slider live-recomputing the waterfall. Keep everything else quiet and disciplined.
4. **Motion:** orchestrated entrance per screen (staggered, <900ms total), scroll-triggered reveals for below-the-fold charts, `prefers-reduced-motion` respected.
5. **Charts:** one library app-wide — **Chart.js 4** (the brand kit ships a Chart.js preset; ADR FE-002 supersedes the ECharts default). Required primitives: area/line with ribbon, stacked area, small multiples, donut, heat strip, scatter/bubble, waterfall, tornado, animated counters.

---

## 6. Tech stack and layout

- **Stack:** static HTML/CSS/JS with **no build step** (ADR FE-001 supersedes React+TS+Vite: the brand skill's asset model is standalone-HTML + pinned `ds-kit/`, and the target is GitHub Pages + `file://`). Zero backend, zero network calls at runtime — Chart.js and the ds-kit are vendored. Runs from `file://`, `npx serve`, or GitHub Pages unchanged.
- **State:** URL-addressable screens (hash routing `#/overview` … `#/about`); scenario state local to V6.
- **Data:** everything from `frontend/data/` (§2). The extractor + seeded generator are committed; regenerating data is an explicit, logged step.

```
frontend/
├── index.html                      # app shell; loads ds-kit, vendor, data, screens
├── ds-kit/                         # pinned OpenEconomics DS kit (copied from oe-frontend-brand)
├── vendor/chart.umd.js             # Chart.js 4, vendored
├── scripts/
│   ├── extract_real_data.py        # pipeline artifacts → data/real-data.js
│   └── generate-demo-data.mjs      # seeded; writes data/demo-data.js (checked in)
├── data/                           # ALL data in the app lives here (isolation rule §0.4)
├── styles/app.css                  # layout glue over ds-kit components
├── js/
│   ├── theme.js                    # brand-skill-mapped tokens — only place brand values exist in JS
│   ├── copy.js                     # all UI strings (insight lines, labels) in one catalog
│   ├── charts.js · components.js · format.js · app.js
│   └── screens/                    # v0…v7, one module per §3 entry
└── tests/check-consistency.mjs     # demo-data consistency checks (§7.3)
```

---

## 7. Definition of done (demo checklist)

1. Every screen in §3 renders fully populated — no empty states, no placeholders, no console errors.
2. The three memorable numbers (total impressions, Index lift, ROI multiple) are consistent everywhere they appear (Overview, deep screens, exports).
3. Demo-data consistency tests pass: shared timeline alignment; simulated series continuous with the real series they extend; V6 waterfall arithmetic closes; funnel deltas match the lift dataset.
4. Cold start to Overview hero < 2s on a mid laptop; runs offline.
5. Brand skill applied throughout; no color/typeface exists outside `src/theme/`.
6. The single §4.4 footer line is present and nothing else in the UI hedges.
7. A 5-minute guided click-through (Overview → V6, one sentence per screen) can be performed without touching anything but the nav and the V6 slider.

---

## 8. Relationship to the production track

When the platform graduates from PoC: `demo-data` is replaced by the canonical C-VIZ bundle pipeline, and the production language/status regime from `ARCHITECTURE.md` §10 applies to real client results. The screen architecture, components, theme, and chart system built for this demo are designed to survive that swap unchanged — build them data-source-agnostic (screens consume typed props, not the demo module directly).
