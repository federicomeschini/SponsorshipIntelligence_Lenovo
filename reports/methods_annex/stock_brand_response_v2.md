# Brand Index-to-stock response v2

> **Status:** exploratory market association. It is not a profit coefficient,
> a causal sponsorship estimate, or an accepted valuation input.

## Why this replaces the v1 stock sensitivity

The v1 stock sensitivity estimated the market-factor model over the full
sample and related the resulting weekly residual to the raw weekly Index
change. That was useful as a first diagnostic but allowed future observations
to influence the factor coefficients, did not isolate unexpected Index
movement and omitted Lenovo financial-results weeks.

Version 2 fixes those design problems:

1. Daily Lenovo log returns are predicted from a rolling 120-trading-day model
   estimated strictly before the prediction day.
2. Factors are the contemporaneous Hang Seng return and the most recent
   Nasdaq-100-in-HKD return available before the Hong Kong session.
3. Weekly Brand Index innovations are actual changes minus rolling predictions
   based on up to 104 prior weeks, with a 52-week minimum.
4. The prediction controls lagged Index movement, PC-category demand, product
   and promotion events, mixed sponsorship/product events and annual
   seasonality.
5. The stock-response regression controls lagged abnormal return, lagged
   residual volatility, category demand, product and promotion events, and the
   announcement week plus two following weeks for all 16 official Lenovo
   results releases.
6. Cumulative abnormal returns are evaluated at the frozen 0, 1, 4 and 13-week
   horizons as one Holm-corrected family.

The response equation at horizon h is:

    CAR[t,h] = alpha[h] + beta[h] * BI_innovation[t]
               + controls[t] + error[t,h]

Overlapping-horizon uncertainty uses Newey-West covariance with at least four
lags and at least h+1 lags.

## Results

The coefficient unit is percentage points of cumulative factor-adjusted equity
return per one unexpected Brand Index point.

| Horizon | Estimate | Robust SE | Approx. 95% interval | Raw p | Holm p |
|---:|---:|---:|---:|---:|---:|
| 0 weeks | +0.305 pp | 0.572 | -0.817 to +1.427 | 0.594 | 1.000 |
| 1 week | -1.380 pp | 1.259 | -3.848 to +1.088 | 0.273 | 0.819 |
| 4 weeks | +0.530 pp | 2.872 | -5.100 to +6.161 | 0.853 | 1.000 |
| 13 weeks | +9.403 pp | 4.642 | +0.304 to +18.501 | 0.043 | 0.171 |

No horizon survives the frozen family-wise test at 10%. The four-week
future-Innovation timing placebo is -0.314 pp with p=0.673.

The 13-week estimate is especially endpoint-sensitive:

| Data endpoint | 13-week estimate | Robust SE | p |
|---|---:|---:|---:|
| 31 Dec 2024 | -2.822 pp | 4.501 | 0.531 |
| 31 Dec 2025 | +2.773 pp | 2.640 | 0.294 |
| 6 Jul 2026 | +9.403 pp | 4.642 | 0.043 |

The long-horizon sign reversal and magnitude jump coincide with the exceptional
May-June 2026 Lenovo stock rally. The result therefore remains a monitored
hypothesis and is not a monetary calibration.

The immediate coefficient is the cleanest efficient-market interpretation:
news should enter the price when it becomes known. Its current estimate is
positive but small, imprecise and statistically indistinguishable from zero.

## What stock evidence can and cannot monetize

If a response coefficient were later accepted, it would first imply an equity
value response, not profit:

    delta_equity_value[t,h] =
        beta[h] * delta_BI[t] * market_cap_before_shock[t]

An equivalent annual cash-flow calculation would require a separately approved
WACC, long-run growth and persistence assumption. Under a perpetual-growth
illustration only:

    equivalent_annual_after_tax_FCF =
        delta_equity_value * (WACC - g)

That second equation is an assumption-driven translation of market value. It
is not evidence that the observed return was caused by brand, nor a direct
profit regression.

For operational planning, this is now implemented in
market_implied_earnings_bridge_v1. It uses the positive immediate response,
Lenovo's official FY2025/26 adjusted earnings and its observed market multiple.
The resulting calibration is +0.305% or +US$6.253m annual adjusted
earnings-equivalent per BI point, with an explicit zero-floor planning rule.

## Alternative income approach: incremental cash flow

ISO 10668 frames monetary brand valuation around valuation approaches, methods,
quality data and assumptions. IVS 210 describes several income methods,
including excess earnings, relief from royalty, premium profit and
with-and-without. Relief from royalty is therefore not the only permitted
income route.

For Lenovo sponsorship, the preferred direct alternative is with-and-without
incremental cash flow:

    sponsorship_value =
        sum over t of
        (FCF_with_sponsorship[t] - FCF_without_sponsorship[t])
        / (1 + WACC)^t

The Brand Index is an intermediate demand signal. It enters the operating
forecast through separately identified elasticities:

    incremental_FCF[t] =
        price_premium_effect[t]
        + volume_effect[t]
        + retention_and_service_effect[t]
        + attributable_cost_savings[t]
        - activation_and_brand_support_costs[t]
        - incremental_tax[t]

The with-sponsorship and without-sponsorship forecasts must be defined on the
same product, geography, volume, margin, tax and working-capital basis. Price
and volume effects must not double count the same revenue. If a multi-period
excess-earnings method is used instead, contributory charges for working
capital, fixed assets, technology and customer relationships must be deducted
before assigning residual cash flow to the brand.

This approach links the sponsorship counterfactual to monetisation directly:

    sponsorship exposure
        -> sponsorship-attributable BI change
        -> price, volume, retention and service changes
        -> incremental after-tax free cash flow
        -> present value

It avoids forcing a royalty rate where Lenovo operating data can support a
cash-flow counterfactual. Royalty relief remains a useful independent
cross-check.

## Reproduction

Run:

    python -m srmp.experiments.stock_brand_response_v2

Configuration is in config/experiments/stock_brand_response_v2.yaml. Outputs
are isolated under data/curated/experimental/stock_brand_response_v2.

## Inputs still missing for monetary use

- dated Lenovo market capitalisation or shares outstanding for an equity-value
  translation;
- an approved WACC, terminal growth and BI-effect persistence policy;
- product-by-geography units, realised prices, contribution margins and
  working-capital effects;
- retention, service-attachment and price-premium measures;
- sponsorship activation and ongoing brand-support costs;
- an identified BI-to-price, BI-to-volume or BI-to-retention elasticity with
  untreated comparison variation; and
- the completed World Cup BI effect and observed World Cup exposure.

Sources:

- ISO 10668 overview: https://www.iso.org/standard/46032.html
- IVS 210 Intangible Assets: https://ivsc.org/wp-content/uploads/2021/10/IVS210IntangibleAssets.pdf
- Lenovo official results archive: https://investor.lenovo.com/en/financial/results.php
