# SRMP Front End — Sponsorship Intelligence (demo product)

Static, no-build demo dashboard for the Lenovo × FIFA case study, per
[`VISUALIZATION.md`](../VISUALIZATION.md) (demo track). OpenEconomics brand via
the pinned `ds-kit/`; charts via vendored Chart.js 4. **Zero backend, zero
network calls at runtime** — everything needed is in this folder.

## Run it

Any of these works:

- **Double-click `Launch Demo.lnk`** (Windows shortcut, opens in your default browser).
- **Double-click `index.html`** (runs from `file://`).
- `npx serve frontend` (or any static server) for in-room demos.
- **GitHub Pages:** the folder is Pages-ready (relative paths only, `.nojekyll`
  included). Either:
  1. Push the repo, then Settings → Pages → *Deploy from a branch*, folder
     `/frontend` is not offered by Pages directly — so either move/copy this
     folder to `/docs` and select `/docs`, **or**
  2. use an Actions workflow that uploads `frontend/` as the Pages artifact:

  ```yaml
  # .github/workflows/pages.yml
  on: { push: { branches: [main] } }
  permissions: { pages: write, id-token: write }
  jobs:
    deploy:
      runs-on: ubuntu-latest
      environment: { name: github-pages }
      steps:
        - uses: actions/checkout@v4
        - uses: actions/upload-pages-artifact@v3
          with: { path: frontend }
        - uses: actions/deploy-pages@v4
  ```

No build step exists, so there is nothing else to configure.

## Data flow (demo track, isolation rule §0.4)

```
pipeline artifacts (data/curated, data/staged, data/reference)
        │  python frontend/scripts/extract_real_data.py
        ▼
frontend/data/real-data.js        (window.SRMP_REAL — real series, checked in)
        │  node frontend/scripts/generate-demo-data.mjs   (seed 20260715)
        ▼
frontend/data/demo-data.js        (window.SRMP_DEMO — simulated fills + every
        │                          derived KPI, checked in)
        ▼
the app (js/screens/*) reads SRMP_DEMO only
```

- Regenerating data is an explicit, logged step: run the two scripts above from
  the repo root, then `node frontend/tests/check-consistency.mjs` must pass.
- The demo never reads `data/raw|staged|curated` at runtime and nothing here is
  imported by `srmp/`.
- Real vs simulated: real series are embedded unchanged; simulated fills
  (broadcast, tournament arc after 2026-07-06, engagement, post-tournament
  survey wave, ROI inputs, portfolio value rates) are produced only by the
  seeded generator. Chart lines render simulated ranges dashed.

## Layout

```
frontend/
├── index.html                 # app shell (hash-routed SPA: #/overview … #/about)
├── ds-kit/                    # pinned OpenEconomics design-system kit (copy)
├── vendor/chart.umd.js        # Chart.js 4 (vendored — offline/file:// safe)
├── styles/app.css             # layout glue on top of ds-kit components
├── js/
│   ├── theme.js               # semantic chart slots → OE tokens (only brand values in JS)
│   ├── copy.js                # every UI string (demo register, §4)
│   ├── format.js  charts.js  components.js  app.js
│   └── screens/v0-overview.js … v7-about.js
├── data/                      # generated, checked in (see above)
├── scripts/                   # extract + seeded generator
└── tests/check-consistency.mjs
```

## Checks

```
node frontend/tests/check-consistency.mjs
```

Verifies the §7.3 invariants: shared timeline alignment, simulated series
continuous with the real series they extend, V6 waterfall arithmetic closes,
funnel deltas match the lift dataset, and the three memorable numbers
(impressions, Index lift, ROI multiple) are the same everywhere.

Front-end-specific decisions (no-build stack, Chart.js, timeline extension,
z-score market benchmark) are logged in [`DECISIONS.md`](DECISIONS.md).
