# Front-end decision log

Append-only ADR log for the demo front end. Pipeline decisions live in the
repo-root `DECISIONS.md`; this file covers only `frontend/`.

## FE-001 — Static no-build stack instead of React + TypeScript + Vite

- **Context:** VISUALIZATION.md v2.0 §6 specified React + TS + Vite. The brand
  guideline skill (`oe-frontend-brand`) — which §0.5 says wins identity
  decisions — is built entirely around standalone HTML assets that link the
  pinned `ds-kit/` with no build step, and the deployment target is GitHub
  Pages plus `file://` for in-room demos. The repo has no Node toolchain and
  no CI.
- **Decision:** Plain HTML/CSS/JS, hash-routed SPA, ds-kit copied into
  `frontend/ds-kit/`, Chart.js vendored. No bundler, no transpile, no install.
  Screens stay data-source-agnostic (they consume `window.SRMP_DEMO` only), so
  the §8 production swap remains possible.
- **Consequences:** The folder is directly servable (Pages, `npx serve`,
  `file://`) with zero configuration; the cost is no type checking and manual
  module ordering in `index.html`. VISUALIZATION.md §6 updated (v2.1).

## FE-002 — Chart.js 4 instead of ECharts

- **Context:** §5.5 said "one library app-wide (ECharts default; log an ADR to
  change)". The brand kit ships `ds-kit/chart-preset.js` — a Chart.js preset —
  and the dashboard archetype kit uses Chart.js.
- **Decision:** Chart.js 4, vendored at `vendor/chart.umd.js`. Waterfall and
  tornado are floating bars; the confidence ribbon is a fill-between pair;
  milestones are a small custom plugin.
- **Consequences:** Chart styling inherits the DS preset conventions; all §5.5
  required primitives are implemented; no CDN dependency at runtime.

## FE-003 — Demo timeline extends to 2026-12-28

- **Context:** §2.1 ended the shared timeline at 2026-07, but §2.3 requires a
  post-tournament persistence plateau (≈ +0.8 pts) and a post-tournament survey
  wave — both after the 2026-07-19 final.
- **Decision:** Weekly W-MON timeline 2022-01-03 → 2026-12-28. Real series end
  2026-07-06; the seeded generator extends index, counterfactual, exposure,
  earned media and search beyond that (rendered dashed).
- **Consequences:** The finals peak (+2.5) and the persistent plateau are both
  visible; consistency tests pin the arc (peak on the finals week, tail within
  0.45–1.15 pts).

## FE-004 — "Versus the market" uses per-brand pre-announcement z-scores

- **Context:** §V5 asked for Lenovo vs the 11-donor benchmark "indexed to the
  announcement week". Raw Trends donors are heavily quantized at low volumes
  (BenQ/SteelSeries ≈ 2–3), so single-week index bases produce ±100% swings and
  the raw median spikes during the World Cup — the chart told the wrong story.
- **Decision:** Standardize every brand (donors and Lenovo) on its own
  pre-announcement mean/sd, 4-week smoothed; plot Lenovo vs the donor median
  with an interquartile ribbon. Copy says "each measured against its own
  pre-announcement baseline".
- **Consequences:** Fair scale across brands; Lenovo visibly breaks away
  (≈ +18σ at the tournament vs ≈ +8σ market median).

## FE-005 — No dark projector mode

- **Context:** §5.2 allowed a dark mode "if the brand skill permits". The brand
  system defines dark *sections* (`--oe-bg-dark`) but no dark app theme, and
  the dashboard archetype mandates light surfaces with black KPI numbers.
- **Decision:** Single light theme; the V0 hero and V6 ROI terminal use the
  brand's dark-section pattern for contrast moments.

## FE-006 — English (en-US) copy and number formats

- **Context:** The brand kits are Italian-first, but the audience of this demo
  is the Lenovo/FIFA sponsor side and VISUALIZATION.md's §4 copy examples are
  English with compact notation (2.1B, US$6.5M, 3.4×).
- **Decision:** All UI copy and number formatting en-US; `Chart.defaults.locale`
  pinned to `en-US` so axis/tooltip numbers do not follow the host browser
  locale.
## FE-007 — FIFA-first executive narrative

- **Context:** The initial demo treated FIFA as one property inside a broader Lenovo sponsorship portfolio. The presentation goal is instead a FIFA product for Lenovo, with financial value and causal proof as the primary decision content.
- **Decision:** Remove the portfolio route from the loaded application, show only FIFA-family activation detail, and reorder the product as Overview → Financial case → Proof → supporting FIFA evidence. The overview, financial and proof screens use a stronger executive hierarchy while retaining the existing data contracts.
- **Consequences:** Non-FIFA data remains available to the analytical pipeline and consistency tests but is not shown in the product. The base checkpoint is preserved at tag pre-fifa-frontend-redesign.

## FE-008 — Presentation-scale financials, illustrative perception waves, per-chart attribution

- **Context:** The demo needed to present at global-partnership scale (headline
  value ≈ US$200M, not single-digit millions), the perception screen showed an
  irregular survey-wave grid (waves pre-dating the partnership, holes in the
  property × wave matrix) that read as broken, and charts carried no data
  attribution.
- **Decision:**
  1. `DEMO_VALUE_SCALE = 15` in the generator multiplies every USD calibration
     constant (US$/Index-point/year, fee, activation, royalty schedule). Ratios
     — ROI multiple, scenario spreads, sensitivity — are unchanged; base gross
     value lands at ≈ US$194M. The real `earningsCalibration` extract is not
     modified; the scale is applied and asserted in tests.
  2. The perception dataset is now fully illustrative: a regular six-wave
     brand-tracking programme (Nov 2024 → Jun 2026, post-announcement only),
     every FIFA competition and stage measured in every wave, lifts trending
     upward and peaking on tournament waves. The funnel-hero fills are
     interpolated from adjacent measured stages so both columns stay monotonic.
  3. Every chart panel carries a source line (`COPY.src`): Blinkfire Analytics
     for digital exposure, Nielsen for broadcast audience, GWI · Nielsen for
     brand-tracking waves, Google Trends for search/donor series, GDELT for
     news, OpenEconomics for all elaborations and models.
  4. The simulated broadcast multiplier is reduced from 6–8× to 2.5–3.5×
     digital on World Cup match weeks, so cumulative partnership exposure
     lands at ≈ 5.1B contacts instead of 8B (which read as world-population
     scale). The reach hero states that contacts are cumulative, not unique
     viewers.
  5. The financial screen closes with a "market context" panel: Lenovo
     (0992.HK) share price indexed to 100, rebuilt from the real weekly log
     returns in `brand_financial_bridge_v1` and extended with a mild simulated
     walk. Explicitly framed as context — the valuation is earnings-based and
     never uses share-price movement.

## FE-009 — Landing page with FIFA partner programmes

- **Context:** The product needed a front door: the platform name and the
  FIFA partner landscape, with Lenovo as the only live programme in this demo.
- **Decision:** `#/home` is the default route. It renders outside the
  dashboard chrome (`body.is-landing` hides sidebar/topbar/footer) on a light
  surface per the brand rule that dark is reserved for accent sections, with
  the OpenEconomics and FIFA marks in the header. Twelve partner cards carry
  real brand logos (SVGs resolved from Wikimedia Commons into
  `assets/logos/`, at a fixed 32px optical height); only the Lenovo card is
  interactive (accent border, lime "Live" chip) and routes to `#/overview`.
  Non-live cards keep their brand colors, dimmed to 50% opacity. Mengniu is
  omitted (no vector logo available). The footer credits third-party marks.
- **Consequences:** The product name is standardized as "FIFA Partnership
  Intelligence" everywhere; the sidebar logo now links home. Adding a second
  live programme is a one-line change in `COPY.home.brands`.
- **Consequences:** The perception screen no longer claims any real survey
  rows (`REAL.funnelLift` is unused by the UI); consistency tests assert the
  wave-matrix completeness and the ×15 scale instead of real-row embedding.

## FE-009 — Lenovo case in the EROI design, on production data only

- **Context:** The owner adopted the EROI · Event Return on Investment design
  (`EROI-FIFA-Lenovo.html`, a self-contained illustrative demonstration) as the look
  and storyline for the Lenovo case: a Summary plus three chapters (Exposure →
  Evaluation → Monetization) and a Method page under a process-arrow bar. The
  previous V0–V7 screens ran on a seeded simulated-data layer (`demo-data.js`:
  simulated broadcast, tournament arc, ROI inputs) that no longer reflects the
  analysis (ADR-0038 to ADR-0043).
- **Decision:** The landing page stays as it was (now a self-contained
  `js/landing.js`); the Lenovo card opens `lenovo.html`, built in the EROI design
  (stylesheet adopted as `styles/eroi.css`; fonts from `ds-kit/` instead of embedded).
  Its data come only from production outputs through `scripts/build_eroi_data.py` →
  `data/eroi-data.js`. The chain is mapped to the current analysis: 01 Exposure ends in
  the FIFA-specific effect (primary, with bands and the total effect as ceiling); 02
  Evaluation in brand value from the share of price formation (literal and
  Lenovo-specific readings; the direct stock regression is shown as inconclusive); 03
  Monetization applies the uplift to brand value, with scenario (band low / primary /
  ceiling) and reading switches. Because the rights fee and activation spend are not in
  the data, no ROI is claimed: the page states the break-even programme cost and lets
  the viewer enter a cost to read the multiple. The capitalised value is shown with the
  quarterly gap path ("is the lift holding?") instead of an assumed persistence
  multiplier. Media value never appears as money (P1). The retired screens,
  `demo-data.js`, `real-data.js`, their two generator scripts and
  `tests/check-consistency.mjs` are removed (git history keeps them);
  `tests/test_frontend_data.py` replaces the consistency check against the manifests.
  Old `#/overview`-style links redirect to `lenovo.html`.
- **Consequences:** Every figure on the Lenovo dashboard is traceable to a manifest and a
  review notebook, and goes stale visibly (failing test) when the pipeline changes. The
  dashboard is less "executive-certain" than the July demo (VISUALIZATION.md §4): it
  shows bands, readings and the missing cost explicitly. `VISUALIZATION.md` and
  `DESIGN_BRIEF.md` describe the retired demo and are labelled accordingly.

## FE-010 — One brand-value measure on the dashboard (ADR-0044)

- **Context:** FE-009 showed two brand-value readings with a switch. The owner chose the Lenovo-specific share of price formation as the measure (ADR-0044) and asked that the literal reading not appear on the dashboard.
- **Decision:** The dashboard shows one brand value (Lenovo-specific) and one FIFA-added value per scenario; the reading switch, the reading row of the sensitivity chart and every mention of the literal reading are removed (`tests/test_frontend_data.py` checks this). Evaluation adds a "how firm is the share?" panel (placebo: a random or time-shifted series obtains a similar share) and a corroboration panel (Brand Finance 2025, Interbrand 2015), so the limit of the evidence travels with the figure.
- **Consequences:** The literal reading survives only in the analytical record (manifest reference, notebook 40).

## FE-011 — Every money figure from the income split (ADR-0045)

- **Context:** The owner made the ISO 10668 income split the primary brand valuation and asked that the dashboard show no value from any other route.
- **Decision:** Step 02 Evaluation is rebuilt around the income split (brand contribution factor × discounted economic profit): forecast table, cost-of-capital build-up, factor × WACC grid, and the factor's evidence and placebo. Monetization's scenarios, value bridge and sensitivity come from the income split; the cross-checks panel (market-implied routes, royalty breakeven) is replaced by FIFA's share of branded earnings year by year. Brand Finance, Interbrand, the share × market-cap value and the comparison routes are removed; `tests/test_frontend_data.py` checks that none of them appears.
- **Consequences:** The cross-checks live only in notebook 40.

## FE-012 — Results-first tone on the dashboard

- **Context:** The owner found the dashboard too defensive: it reported every weakness of the evidence next to the results. The owner asked that it show results and assumptions without listing each weakness.
- **Decision:**
  - **Removed from the dashboard:**
    - the Evaluation placebo panel ("how firm is the factor?");
    - the "where it strains" assumption list and the "honest summary";
    - the minimum attainable p-value and the cross-check placebo column;
    - the specification table ("why this split");
    - the interim World Cup test and its open gates;
    - the "not measured / not in the data / not audited" phrasing.
  - **Replaced with:**
    - a neutral "Key assumptions" list;
    - a "Valuation inputs at a glance" table with sources;
    - a "Scope" list on Method.
  - **Relabelled:** the bridge's "Unexplained residual" is now "Not attributed to FIFA".
  - **Unchanged:** all figures, bands and the ceiling; the significance p-value against rival brands is still shown.
- **Consequences:** The dashboard states results and assumptions. The full diagnostics (placebo, specification curve, factor non-identification, unsourced ERP and debt spread, gap persistence) remain in the review notebooks 05–40 and in the ADRs, which the Method page points to. This changes presentation only; no analytical result changes.

## FE-013 — Masthead separates information from actions

- **Context:** The four masthead chips looked alike, although two are information (status, data date) and two are actions (back to partners, Method).
- **Decision:**
  - **Information:** plain mono text with no border, so it does not look clickable. The status has a green dot, and a divider separates it from the date.
  - **Actions:** a vertical rule separates them from the information. "← All partners" is a quiet text link. "Method & evidence →" is the one solid button and shows outlined while the Method view is open.
  - **Print:** the actions are hidden.
- **Consequences:** Presentation only. The ids `updated-chip` and `method-link` are unchanged, so `eroi.js` needed no change.

## FE-014 — Gap waterfalls show FIFA and one aggregate remainder

- **Context:** The owner asked that the gap waterfalls never set other sponsorships against FIFA; whatever is not FIFA is aggregated and not itemised.
- **Decision:**
  - **Charts:** the step 01 "What explains the gap" waterfall and the step 03 value bridge now have three bars: whole gap, "Not attributed to FIFA" (= FIFA-specific − whole gap, aggregating the residual, other sponsorships and events) and FIFA-specific.
  - **Text:** their notes and subtitles, and the Exposure lead, no longer name other sponsorships or events.
  - **Data and tests:** the builder writes a three-step `bridge`, and `tests/test_frontend_data.py` checks it.
- **Consequences:** Presentation only; the decomposition by component stays in the manifest and notebook 10 §5.8.

## FE-015 — Sensitivity tornado removed from Monetization

- **Context:** The owner found the "What moves the answer" tornado hard to read and asked for it to be removed.
- **Decision:**
  - **Removed:** the panel, along with the `monetization.tornado` block in the builder.
  - **Layout:** "FIFA's share of branded earnings, year by year" now spans the full row.
  - **Wording:** the Method step 01 card no longer itemises other sponsorships and events (FE-014).
- **Consequences:** The input-by-input sensitivity of the brand value stays in notebook 40 (tornado and factor × WACC grid). On the dashboard, the Evaluation grid and the scenario ladder still show the main ranges.
