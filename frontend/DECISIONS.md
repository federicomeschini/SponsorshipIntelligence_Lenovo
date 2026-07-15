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
