# Front end — FIFA Partnership Intelligence

Static, no-build front end on the OpenEconomics brand (pinned `ds-kit/`, vendored
Chart.js 4). **Zero backend, zero network calls at runtime.**

- `index.html` — the landing page with the FIFA partner programmes. Only Lenovo is live.
- `lenovo.html` — the **Lenovo × FIFA case dashboard** in the EROI · Event Return on
  Investment design (FE-009): a Summary plus three chapters (Exposure → Evaluation →
  Monetization) and a Method page, navigated through a process-arrow bar.

## Run it

- Double-click `Launch Demo.lnk` or `index.html` (works from `file://`), or
- `npx serve frontend`, or
- GitHub Pages: pushes to `main` that change `frontend/` deploy via
  [`.github/workflows/pages.yml`](../.github/workflows/pages.yml), which publishes only the
  runtime files (HTML, `js/`, `styles/`, `data/`, `ds-kit/`, `vendor/`, `assets/`, `404.html`,
  `.nojekyll`). One-time setup: repository Settings → Pages → Source = **GitHub Actions**.
  All paths are relative, so the site works under the project URL
  (`https://<user>.github.io/<repo>/`) as well as from `file://`.

## Data flow

```
production outputs (data/curated, data/staged, data/reference)
        │  python frontend/scripts/build_eroi_data.py      (after python -m srmp.pipeline)
        ▼
frontend/data/eroi-data.js   (window.EROI — generated, checked in)
        ▼
lenovo.html + js/eroi.js     (formats and draws; estimates nothing)
```

- No simulated or illustrative numbers: every figure is copied from a production manifest
  or derived in `build_eroi_data.py` with the arithmetic stated there (rebased series,
  scenario values, sensitivity ranges). The only arithmetic in the page is the optional
  programme-cost multiple the viewer types in.
- `tests/test_frontend_data.py` (repo root test suite) fails when `eroi-data.js` is stale
  against the manifests. After any pipeline rebuild, re-run the build script.
- The figures are explained, with every calculation, in the review notebooks
  (`reports/methods_annex/10`, `20`, `35`, `40`).

## What the Lenovo dashboard shows

| Chapter | Question | Output it hands on |
|---|---|---|
| 01 Exposure | How much more did Lenovo stand out than rivals, and how much of that is FIFA? | FIFA-specific effect (ADR-0043), with its 95% band and the whole gap as ceiling |
| 02 Evaluation | What is the Lenovo brand worth, from what moves its share price? | Brand value from the brand's share of Lenovo-specific price drivers, corroborated by independent valuations (ADR-0044) |
| 03 Monetization | What did FIFA add to that value, and what cost would it cover? | FIFA-added brand value per scenario; break-even programme cost |

## Layout

```
frontend/
├── index.html, js/landing.js      # landing page
├── lenovo.html, js/eroi.js        # Lenovo case dashboard
├── styles/app.css                 # landing styles (on top of ds-kit)
├── styles/eroi.css                # dashboard styles (EROI design)
├── data/eroi-data.js              # generated
├── scripts/build_eroi_data.py     # generator (reads production outputs)
├── ds-kit/  vendor/  assets/      # brand kit, Chart.js, partner logos
└── DECISIONS.md                   # front-end decision log
```
