# Dynamic sponsorship total return v2

> **Status:** operational planning valuation. It supersedes the US$45.7m
> single-multiplication result for total-return use.

## Primary result

The base estimate of total market-implied Lenovo-FIFA sponsorship value is:

    US$1.250bn

The part supported by the observed sponsorship BI path, allowing every current
shock to complete its 13-week response, is:

    US$734.7m

The additional amount is a transparent contract-completion scenario for the
remaining 12.5% of the Men's World Cup match calendar and the 2027 Women's
World Cup.

| Scenario | Observed path, fully matured | Full-contract planning value |
|---|---:|---:|
| Low | US$81.6m | US$116.5m |
| Base | US$734.7m | US$1.250bn |
| High | US$2.432bn | US$4.702bn |

## Defect corrected

The old calculation multiplied an exposure-weighted average BI level gap by an
immediate stock coefficient. The stock model coefficient was estimated on
weekly BI innovations, so those quantities were not aligned.

Let g[t] be the weekly actual-minus-synthetic BI level gap and phi[t] the
rolling coefficient on lagged BI change in the innovation model. The
sponsorship-attributable innovation is:

    u_sponsorship[t] =
        delta_g[t] - phi[t] * delta_g[t-1]

Across the 90 post-announcement weeks, these aligned innovations sum to 0.730
BI points.

For each planning scenario, cumulative stock responses at 0, 1, 4 and 13 weeks
are projected onto a nonnegative, nondecreasing curve using
inverse-variance-weighted isotonic regression. Linear interpolation supplies
weekly cumulative responses B[l], and incremental distributed-lag responses
are:

    lambda[l] = B[l] - B[l-1]

Weekly sponsorship-attributable abnormal return is:

    r_sponsorship[t] =
        sum over l of lambda[l] * u_sponsorship[t-l]

Once all observed shocks mature:

    R_sponsorship = B[13] * sum_t u_sponsorship[t]

Market-implied value is computed against the dated current market
capitalisation:

    Value = MarketCap * (1 - exp(-R_sponsorship))

This avoids treating an average level as one shock and avoids adding
overlapping cumulative-return windows.

## Response scenarios

The low case holds the positive immediate full-sample response constant through
13 weeks.

The base case uses only stock-response estimates through 31 December 2025,
before the World Cup outcome and the exceptional 2026 rally. Its raw cumulative
responses are +0.860%, -0.489%, +1.842% and +2.773% at 0, 1, 4 and 13 weeks.
The monotone projection pools the first two at +0.284% and leaves the 4 and
13-week values unchanged.

The high case uses the full-sample 13-week response of +9.403%. This captures
the current upside but is endpoint-sensitive, so it is not the central case.

## Contract completion

The current outcome covers 91 of 104 Men's World Cup matches, or 87.5%. The
contract also includes the 2027 Women's World Cup. With no future BI outcome,
the Women's competition is represented as an explicit share of the completed
Men's impact:

- low: 25%;
- base: 50%;
- high: 75%.

The completion multiplier is:

    (1 / observed_mens_match_share) * (1 + womens_share)

This is scenario modelling, not fabricated observed data.

## External triangulation

| Cross-check | Gross market-implied value | Treatment issue |
|---|---:|---|
| Announcement, first two HK sessions | US$306m | Confounded with Tech World |
| Announcement, first three HK sessions | US$756m | Confounded with Tech World |
| World Cup start through 14 July | US$4.014bn | Confounded with financing, buyback and corporate news |

The announcement range supports a value materially above US$45.7m. The
tournament CAR supports the high case but cannot be assigned wholly to FIFA.
These values are triangulation only and are not added to the dynamic estimate.

## ROI interpretation

If F is the all-in rights, activation and delivery cost in US$ millions:

    gross value multiple = 1,250.4 / F

    net ROI = (1,250.4 - F) / F

The base break-even all-in cost is therefore approximately US$1.25bn. No public
fee has been inserted.

## Reproduction

Run:

    python -m srmp.experiments.stock_brand_response_v2
    python -m srmp.experiments.sponsorship_total_return_v2

Configuration is in config/experiments/sponsorship_total_return_v2.yaml.
Artifacts are isolated under
data/curated/experimental/sponsorship_total_return_v2.
