# Lenovo Brand Index construction and governance

> **SUPERSEDED (2026-10-07, ADR-0040).** This document describes the proxy-led index, which is no longer the Brand Index. It is kept as the *search-salience* cross-check (`data/curated/index/search_salience_index_weekly.parquet`). The current Brand Index is documented in [`05_brand_index.ipynb`](05_brand_index.ipynb).

> **STALE: not synchronized with the October 2026 production state (labelled 2026-10-06).**
> - *Affected:* calibration slope and correlation, coverage end (now the week of 28 September 2026), method-comparison figures
> - *Why not updated yet:* the October 2026 refresh (ADR-0027) re-ran this experiment; the narrative was not rewritten in the same session
> - *Consequence for interpretation:* construction rules are unchanged; quoted statistics and dates are July values
> - *Required action:* rewrite as a review notebook reading `data/curated/index/` (tracked under "Open documentation actions" in `README.md`).

## Purpose

This note documents the simple, PCA, and evidence-weighted Lenovo Brand Index
constructions. They are weekly, descriptive measures of Lenovo brand
performance. They are not forecasts, causal sponsorship effects, or weekly
survey reconstructions.

Peer position is excluded on purpose. Peer series answer a benchmarking
question; this index is intended to measure Lenovo's own brand performance.

## Shared inputs and exclusions

The weekly horizon is 2022-01-03 to 2026-07-06 (W-MON). Google Trends is
assembled from overlap-rescaled windows, and each query is standardized before
entering a composite.

The multi-signal constructions use four Lenovo-only dimensions:

1. Brand salience (B): worldwide Google Trends for the Lenovo parent brand.
2. Product portfolio interest (P): equally weighted Lenovo laptop, ThinkPad,
   and Lenovo Legion searches.
3. Commercial intent (I): equally weighted Lenovo laptop price and ThinkPad
   price searches.
4. Earned-news tone (T): weekly mean GDELT tone. A week missing provider tone
   is filled with the observed-period mean, neutral after standardization.

Wikipedia pageviews and GDELT volume are attention diagnostics, not inputs:
their direction as brand-health measures is not established here. Co-branded
Trends are property outcomes; Blinkfire is sponsorship exposure. Neither is a
broad Lenovo brand-performance constituent.

## Survey role and calibration

The usable population survey is the 37-quarter GWI engagement/consideration
PC1. Seventeen quarters overlap the weekly index. Each method's quarterly
average score Q is mapped to GWI using the full overlap:

    GWI_z = intercept + slope * Q + residual
    Index = 100 + 15 * (intercept + slope * Q_week)

This calibration orients the score so higher means stronger performance and
puts each method on the same 100/15 display scale. It does not anchor individual
weeks, interpolate GWI, or claim that GWI is complete brand equity.

Consumer-research awareness, appeal, and purchase-intent crosstabs are not
population weights or calibration targets: they are sponsorship-awareness
segments, lack a usable population total, and have a 2024-to-2025 scale break.
They remain separate within-wave, within-property sponsorship-lift evidence
(aware minus unaware).

## 1. Simple proxy-led index - current canonical series

    Q_simple = B

The simple index uses only the Lenovo parent-brand Trends series. It therefore
has the narrowest, clearest construct: weekly Lenovo brand salience. Product
and price searches remain companion pulses rather than silently broadening the
meaning of the headline. Its 17-quarter GWI level correlation is 0.666 and its
first-difference correlation is 0.291. The output version is
v4_proxy_led_brand_calibrated.

## 2. PCA multi-signal index - experimental

PCA finds the direction of greatest shared variation in B, P, I, and T. GWI
does not choose the loadings; its relationship only orients the sign and maps
the output to the display scale.

    Q_PCA = 0.572 B + 0.575 P + 0.543 I + 0.216 T

The loadings have unit Euclidean length, not a 100% budget, and are not
component contributions. Their squared-loading shares are 32.7% B, 33.1% P,
29.5% I, and 4.7% T. PCA has GWI level correlation 0.676,
first-difference correlation 0.284, and calibration residual SD 0.105 GWI
z-units.

Leave-one-quarter-out refits are very stable: the largest absolute loading move
is 0.046 (tone), while the three search loadings each move by at most 0.010.
Choose PCA when the intended construct is the common movement across the four
chosen dimensions without asking GWI to allocate their relative weights.

## 3. Evidence-weighted multi-signal index - experimental

Evidence weighting uses the same four dimensions but lets the available GWI
history inform a constrained, interpretable weight budget. It minimizes the
fit to the overlap-standardized GWI score (not to a future survey value):

    sum_quarters (GWI_overlap_z - w_B*B - w_P*P - w_I*I - w_T*T)^2
    + 5.0 * sum_components(w_component^2)

subject to non-negative weights that sum to one. The fixed ridge penalty 5.0
is a governance choice: it strongly shrinks a 17-quarter fit away from a
fragile winner-takes-all solution. It was not selected by forecasting.

    Q_evidence = 0.261 B + 0.331 P + 0.176 I + 0.232 T

Evidence weighting has GWI level correlation 0.681, first-difference
correlation 0.250, and calibration residual SD 0.104 GWI z-units. Across 17
leave-one-quarter-out refits, maximum weight shifts are 0.059 B, 0.062 P,
0.047 I, and 0.078 T. Choose it when the intended governance is explicitly
GWI-informed weighting with non-negative, sum-to-one, strongly regularized
weights.

## Comparison and choice

PCA and evidence weighting are nearly the same historical signal: their weekly
series correlate 0.988 and their maximum display-index gap is 0.865 points.
The decision is therefore principally about interpretation and governance, not
a major difference in the historical curve.

- Choose simple for strict Lenovo brand salience and maximum clarity.
- Choose PCA for a survey-neutral summary of common movement across the four
  selected dimensions.
- Choose evidence weighting for GWI-informed, transparent component weights.

Entropy weighting is retained only as a mechanical sensitivity reference. It
places 52.5% on commercial intent, versus 15.5% B, 19.9% P, and 12.2% T, so it
is less suitable as the preferred brand-performance index.

No method is selected through a future-survey forecast test. Review instead
covers component scope, positive GWI orientation, survey convergence,
leave-one-quarter weight stability, Trends-window uncertainty, and substantive
event interpretation. A non-positive slope, unstable signs, or material
dependence on one GWI quarter requires review before publication.

## Reproducibility

Build the canonical simple series with:

    python -m srmp.index.proxy_led

Build the three-method comparison with:

    python -m srmp.index.multisignal_compare

Outputs and diagnostics are in data/curated/index, including
brand_index_method_comparison_manifest.json.

The separate experimental bridge from sponsorship exposure and funnel lift to
conditional monetization is documented in
[experimental_sponsorship_monetization_v1.md](experimental_sponsorship_monetization_v1.md).
