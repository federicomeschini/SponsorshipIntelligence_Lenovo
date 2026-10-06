# Market-implied earnings bridge v1

> **STALE: not synchronized with the October 2026 production state (labelled 2026-10-06).**
> - *Affected:* per-BI-point mapping (now US$3.02m, July US$6.25m); the superseded-by reference (now `sponsorship_total_return_v3`); World Cup cases (now interim engine)
> - *Why not updated yet:* the October 2026 refresh (ADR-0027) re-ran this experiment; the narrative was not rewritten in the same session
> - *Consequence for interpretation:* do not quote US$6.25m per point; see `40_brand_value.ipynb` for the current valuation routes
> - *Required action:* fold into `40_brand_value.ipynb` or rewrite as its own notebook (tracked under "Open documentation actions" in `README.md`).

> **Status:** the per-BI unit calibration remains a planning diagnostic, but
> its US$45.7m single-multiplication result is superseded for total-return use
> by sponsorship_total_return_v2.

## Operational answer

The immediate stock-response estimate is positive:

    one BI point -> +0.305171% abnormal equity return

Under a constant Lenovo earnings multiple, the same percentage change applies
to market-implied annual adjusted earnings:

    one BI point -> +0.305171% annual adjusted earnings-equivalent

Lenovo FY2025/26 adjusted net income is US$2.049bn. Therefore:

    US$2.049bn * 0.305171% = US$6.253m per year per BI point

This is the operational coefficient.

## Market-value cross-check

Lenovo's FY2025/26 Annual Report records 12,404,659,302 ordinary shares and a
31 March 2026 market capitalisation of HK$113.5bn, approximately US$14.5bn.
Against US$2.049bn adjusted net income, the observed adjusted-earnings multiple
is approximately 7.08 times.

    equity value per BI point =
        US$14.5bn * 0.305171%
        = US$44.250m

    earnings-equivalent per BI point =
        US$44.250m / 7.08
        = US$6.253m per year

The direct earnings calculation and market-cap calculation therefore reconcile.

## Positive planning rule

The empirical immediate-response interval is -0.817% to +1.427%. For commercial
planning, the coefficient is subject to a transparent monotonicity constraint:

    planning beta = max(0, empirical beta)

The planning range is consequently zero to US$29.244m annual adjusted
earnings-equivalent per BI point, with US$6.253m as the central value. This is a
decision range, not a statistical confidence interval. The empirical interval
and p-values remain in the underlying stock-response artifact.

The rule says that an increase in the Brand Index cannot be assigned a negative
commercial value in the planning model. It does not claim that the data proved
the restriction.

## Current scenario application

| Case | BI change | Annual earnings-equivalent central |
|---|---:|---:|
| One BI point | +1.000 | +US$6.253m |
| Announcement-period candidate | +1.033 | +US$6.461m |
| World Cup total-path simulation | +0.367 | +US$2.292m |
| World Cup incremental simulation | -0.160 | -US$1.003m |

The coefficient is accepted for planning. The announcement and World Cup
attributions remain unaccepted until their separate counterfactual gates pass.
A positive monetisation coefficient cannot make an uncertain treatment effect
causal.

## Why this is practical

The bridge needs only data already present or easily auditable:

- the immediate stock-response coefficient;
- Lenovo annual adjusted net income;
- official shares and market capitalisation; and
- the estimated BI change for the scenario.

It does not require product-level margin, retention, WACC, royalty or client
survey microdata. Those inputs would improve a future decision-grade income
valuation but no longer block an operational planning number.

## Reproduction

Run:

    python -m srmp.experiments.market_implied_earnings_bridge_v1

Configuration is in
config/experiments/market_implied_earnings_bridge_v1.yaml and artifacts are in
data/curated/experimental/market_implied_earnings_bridge_v1.

Official source:

- Lenovo FY2025/26 Annual Report:
  https://www.hkexnews.hk/listedco/listconews/sehk/2026/0626/2026062600475.pdf
