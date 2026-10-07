# Curated data

Analysis-ready contract artifacts belong here. Curated outputs must satisfy the relevant contract schema and must not recompute statistics in the visualization layer.

## Brand Index (C-INDEX, ADR-0040)

`index/brand_index_weekly.parquet` is the Lenovo Brand Index: a weekly mixed-frequency
dynamic factor of Lenovo's Google share of search against rival brands, with GWI
engagement and consideration entering as quarterly-average measurements
(`srmp/index/brand_factor.py`, `config/brand_index.yaml`). 100 = pre-announcement
average; 1 point is about 1% of Lenovo's brand share of attention (ratio scale).
Companion files: `brand_index_loadings`, `brand_index_validity_screen`,
`brand_index_sensitivities` and `brand_index_manifest.json` (version, loadings,
validity screen, display scale, survey fit). The weekly file also carries each
signal's log share and `product_search_demand`, a descriptive Lenovo product/price
search indicator that is not part of the index. Review: `reports/methods_annex/05_brand_index.ipynb`.

## Search-salience cross-check

`index/search_salience_index_weekly.parquet` is the former, proxy-led index (worldwide
"Lenovo" Trends on the GWI composite's 100/15 scale; `srmp/index/proxy_led.py`). It is
kept only for cross-checks and for the original 2024 counterfactual design. Its
components are in `index/brand_index_components_weekly.parquet`.

## Experiments

`experimental/<experiment_id>/` holds each experiment's outputs; every experiment has a
review notebook in `reports/methods_annex/`.
