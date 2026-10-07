# Brand Index-to-financial bridge v1

> **SUPERSEDED (2026-10-07).** The current review artifact for this experiment is [`35_financial_links.ipynb`](35_financial_links.ipynb), which reads the current outputs. This document is the July 2026 record; its figures are in the superseded search-salience index's units (ADR-0040) and must not be quoted.

> **Units changed by ADR-0040 (2026-10-07).** Brand Index figures below are in the superseded search-salience index's points; the experiment now runs on the brand-level Brand Index (1 point ≈ 1% of brand share of attention).

> **STALE: not synchronized with the October 2026 production state (labelled 2026-10-06).**
> - *Affected:* sample size and coefficients (now 17 quarters including FY26/27 Q1); the World Cup cases, which now use the interim engine (ADR-0036)
> - *Why not updated yet:* the October 2026 refresh (ADR-0027) re-ran this experiment; the narrative was not rewritten in the same session
> - *Consequence for interpretation:* quoted coefficients and dollar figures are July values; the overall conclusion (no profit coefficient approved) still holds in the current output
> - *Required action:* rewrite as a review notebook reading `data/curated/experimental/brand_financial_bridge_v1/` (tracked under "Open documentation actions" in `README.md`).

> **Status:** exploratory single-company association. No coefficient in this
> branch is approved for sponsorship valuation.

## Why stock price is not profit

A stock-price level is the market's discounted expectation of all future cash
flows and news. It is neither quarterly profit nor brand-attributable profit.
The primary bridge therefore uses Lenovo's directly reported quarterly revenue
and adjusted net income. Stock prices are converted to returns and then to
factor-adjusted abnormal returns only as a secondary market corroboration.

The analysis also respects the distinction between units: one Brand Index point
is one point on the documented mean-100/SD-15 scale, not a percentage point.
The financial outcome is the change in adjusted net-income margin, measured in
percentage points.

## Source panel

The financial panel contains 16 Lenovo fiscal quarters from FY22/23 Q1 through
FY25/26 Q4. Revenue, reported net income and non-HKFRS/adjusted net income come
from Lenovo's official financial-highlights tables. Where Lenovo subsequently
restated an adjusted-profit comparator under its newer definition, the later
official comparative is used and marked as restated.

For quarter q:

    adjusted_margin[q] =
        100 * adjusted_net_income_usd_m[q] / revenue_usd_m[q]

The Brand Index is averaged over the corresponding calendar quarter.

## Controls

The quarterly control set contains:

- category-demand movement: the equal-weighted, standardised quarterly movement
  of Dell, Asus, Acer, HP laptop, Microsoft Surface and MacBook Trends;
- Hang Seng quarterly log return;
- Nasdaq-100 return converted to HKD;
- fiscal-quarter seasonality indicators;
- quarterly Lenovo product/corporate event counts; and
- revenue growth in the adjusted-profit growth specification.

All financial models use first differences or log changes. No trending levels
are regressed on one another.

The principal direct-margin specification is:

    delta_margin[q] =
        alpha + beta * delta_BI[q]
        + gamma * delta_category_demand[q]
        + theta_1 * HSI_return[q]
        + theta_2 * NDX_HKD_return[q]
        + error[q]

HC3 robust uncertainty is used because only 15 quarterly first differences are
available.

The adjusted-profit sensitivity additionally controls revenue:

    delta_log_profit[q] =
        alpha + beta_p * delta_BI[q]
        + rho * delta_log_revenue[q]
        + category_and_market_controls[q]
        + error[q]

## Results per one Brand Index point

### Direct adjusted-margin mapping

| Quantity | Estimate |
|---|---:|
| Adjusted net-margin change | +0.0035 percentage points |
| Robust SE | 0.5016 pp |
| Approximate 95% interval | -0.9796 to +0.9866 pp |
| p-value, normal approximation | 0.994 |

At the latest quarterly revenue of US$21.588bn, the mechanical translation is:

| Quantity | US$ million per quarter |
|---|---:|
| Central | +0.75 |
| Approximate 95% lower | -211.48 |
| Approximate 95% upper | +212.98 |

The raw uncontrolled margin model gives +0.1962 pp per Index point, or about
US$42.3m per quarter. Once category and macro controls enter, it falls to
+0.0035 pp. Adding fiscal seasonality changes the sign. Across the five margin
specifications, coefficients range from -0.788 to +0.196 pp. The mapping is
therefore not stable.

The revenue-controlled profit-growth sensitivity gives +11.8% adjusted net
income per Index point, but its interval is -28.6% to +75.0% and p=0.625. It is
also not a usable calibration.

## Stock-market corroboration

Daily Lenovo log returns are factor-adjusted against contemporaneous HSI
returns and the latest Nasdaq-100-in-HKD return available before the Hong Kong
trading session. Weekly abnormal returns are then related to weekly Index
changes, controlling lagged abnormal return and Lenovo product, promotion and
mixed-event weeks with four-lag Newey-West uncertainty.

The result is -0.873 percentage points of weekly abnormal return per Brand
Index point, SE 0.821, interval -2.482 to +0.735, p=0.287. It is negative,
imprecise and explains very little weekly return variation. It does not support
using stock performance as a profit proxy or as a monetary conversion.

This v1 sensitivity is superseded for market-response work by
stock_brand_response_v2. The newer experiment uses prior-only rolling factor
coefficients, Brand Index innovations, official results-release controls,
frozen response horizons, family-wise testing and endpoint stability. The
direct quarterly profit models in this document are unchanged.

## Mechanical application to current Index cases

Using the controlled direct-margin coefficient only:

| Case | Index change | Quarterly adjusted-profit central | Approx. 95% range |
|---|---:|---:|---:|
| One Index point | +1.000 | +US$0.75m | -US$211.48m to +US$212.98m |
| Announcement-period candidate | +1.033 | +US$0.77m | -US$218.54m to +US$220.09m |
| World Cup total-path simulation | +0.367 | +US$0.27m | -US$77.51m to +US$78.06m |
| Incremental World Cup simulation | -0.160 | -US$0.12m | -US$34.16m to +US$33.92m |

These are arithmetic sensitivities, not accepted value estimates. Annualising
them assumes four identical quarters and is not a present value or ROI.

## Decision and preferred valuation route

There is currently no defensible empirical answer of the form “one BI point
causes X profit.” The panel is short, the controlled estimate is effectively
zero, uncertainty is economically enormous, and specifications change sign.

For decision-grade monetisation:

1. Use an accepted sponsorship-attributable Index change.
2. Estimate a brand contribution factor from product/geography-level revenue,
   margin, price-premium and consideration data, preferably with untreated
   comparison variation.
3. Apply the BCF to the relevant profit or revenue base.
4. Value the identified operating consequences with a with-and-without
   incremental-cash-flow model; cross-check with an approved royalty-relief
   schedule and comparable royalty rates.
5. Retain abnormal stock returns only as event corroboration.

The direct quarterly regression remains a reasonableness check, not the
valuation engine.

## Reproduction

Run:

    python -m srmp.experiments.brand_financial_bridge_v1

Configuration is in
`config/experiments/brand_financial_bridge_v1.yaml`. Results are in
`data/curated/experimental/brand_financial_bridge_v1`. Every monetary
scenario is stamped `accepted_for_valuation=false`.

## Data still needed

- longer or more granular BI history matched to financial outcomes;
- geography/product-level Lenovo revenue, units, price, margin and marketing;
- an external PC-category shipment/demand series rather than search alone;
- campaign and sponsorship spend intensity;
- an identified BCF model with untreated comparison variation; and
- an approved royalty-rate schedule and sponsorship fee.
