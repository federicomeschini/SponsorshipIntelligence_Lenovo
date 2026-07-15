# Experimental sponsorship counterfactual v1

> **Interim scope:** this experiment evaluates the 15 October 2024 FIFA
> partnership announcement and the subsequent FCWC period. The World Cup is
> expected to be the largest activation and is covered by a separate prospective
> protocol. This result cannot close sponsorship attribution or valuation.

## Estimand and separation of roles

The counterfactual estimates Lenovo's weekly Brand Index path absent a
Lenovo-specific post-announcement salience break:

    gap[t] = actual_index[t] - synthetic_no_FIFA_index[t]

Donors are competitor-brand search series. Blinkfire is not a donor: after the
counterfactual is fitted, it supplies FIFA exposure weights and a non-FIFA
sponsorship timing control. Lenovo product, corporate and promotion events are
downstream confounder controls. Co-branded property searches remain mechanism
diagnostics only.

The announcement week beginning 14 October is kept in the pre-period because it
contains only a partial treatment day. The first full post week is 21 October
2024. All standardisation and donor-weight fitting use only the pre-period.

## Jointly scaled Google Trends panel

The prior independently normalised donor pulls have been discarded for
counterfactual fitting. The replacement collector sends the common anchor
'Lenovo' with at most four donor terms in each request. It repeats each of six
panels ten times. For panel p and draw d, the positive-overlap scaling factor is:

    scale[p,d] = sum_t median_anchor_reference[t]
                 / sum_t anchor[p,d,t]

and each donor series is multiplied by that factor. This creates a coherent
cross-panel request scale while retaining Google Trends' sampling and rounding
limitations.

The completed artifact has 6 panels, 21 candidate donor queries, 10 successful
draws per panel, and 237 weeks. Zero-heavy or constant series are removed before
SCM. The 11 clean base donors are Dell, Asus, Acer, HP laptop, Microsoft
Surface, Razer, Logitech, MacBook, Corsair, SteelSeries and BenQ. Huawei and MSI
are sensitivity-only. Samsung and LG gram are contamination exclusions.
Gigabyte, Toshiba, Fujitsu, VAIO, Framework and AOC are data-quality exclusions.

## Treatment-contamination screen

The registry covers 1 January 2022 through 15 July 2026. It combines FIFA's
current partner roster, FIFA annual-report and commercial announcements, and
targeted official brand/FIFA/World Cup/FIFAe searches. Every claim is stored in
'fifa_donor_screening_evidence.csv'.

'no_match_found' is an evidence-bounded search result, not proof that a brand
has never had a relevant relationship. The screen must be refreshed at the
outcome freeze. Samsung is excluded because FIFA+ distribution and World Cup
marketing can affect its search outcome even without an official sponsorship.
MSI is sensitivity-only because its own history reports World Cup stadium
technology visibility. Huawei remains sensitivity-only for construct
comparability.

## Synthetic-control fit

The simplex weights solve:

    minimise_w sum_pre (Lenovo_z[t] - sum_j w[j] donor_z[j,t])^2
    subject to w[j] >= 0 and sum_j w[j] = 1

The fitted weights are:

| Donor | Weight |
|---|---:|
| Asus | 46.121% |
| MacBook | 37.716% |
| Dell | 3.549% |
| Corsair | 3.467% |
| Logitech | 3.336% |
| SteelSeries | 2.976% |
| HP laptop | 2.604% |
| Acer | 0.188% |
| BenQ | 0.043% |
| Microsoft Surface | 0.000% |
| Razer | 0.000% |

The standardised gap is mapped to Index points using the pre-treatment affine
relationship between Lenovo's parent-brand proxy and the canonical Index.

## Product and campaign controls

The event table contains 21 rows spanning 2022-2026: CES, MWC, Tech World,
Innovation World, the Copilot+ PC launch and Black Friday calendar proxies.
Confirmed events are separated from promotion-calendar proxies. The week of 15
October 2024 is explicitly 'mixed_event_control', because the FIFA announcement
coincided with Tech World product and AI announcements.

Each control covers the event week and one carryover week. These indicators do
not alter the pre-treatment donor weights. They enter the downstream exposure
timing regression and an event-week-excluded effect sensitivity. They are event
dummies, not measures of Lenovo media spend or launch intensity.

## Interim result

| Diagnostic | Result |
|---|---:|
| Pre-treatment weeks | 146 |
| Post-treatment weeks | 90 |
| Pre-treatment RMSPE | 0.244 Index points |
| Post-treatment RMSPE | 1.337 Index points |
| Post/pre RMSPE ratio | 5.490 |
| All-post mean gap | +0.824 Index points |
| FIFA-exposure-weighted gap | +1.033 Index points |
| Event-week-excluded weighted gap | +1.021 Index points |
| Donor-set sensitivity range | +0.998 to +1.528 points |
| Donor-placebo p-value | 0.0833 |

With 11 donors, 0.0833 = 1/12 is the smallest attainable finite-sample
donor-placebo p-value. The candidate therefore clears the registered 0.10
screen, but only at its resolution boundary. This is stronger than the retired
five-donor result; it is not by itself proof that FIFA caused the break.

## Exposure timing diagnostic

For the 89 weeks where Blinkfire is observed, the downstream model is:

    gap[t] = alpha
             + beta_F z(log(1 + FIFA_adstock[t]))
             + beta_N z(log(1 + nonFIFA_adstock[t]))
             + gamma time[t]
             + product_event[t]
             + promotion_proxy[t]
             + mixed_event[t]
             + error[t]

with four-lag Newey-West uncertainty. The FIFA coefficient is -0.144 Index
points (HAC SE 0.160); the non-FIFA coefficient is +0.093 (SE 0.100).
Consequently, the controlled timing diagnostic does **not** support a
FIFA-specific exposure association. Exposure is endogenous and Blinkfire
starts only three observed weeks before the first full post week, so this model
is descriptive even if its sign were positive.

The experiment status 'candidate_passes_experimental_screen' means only that
pre-fit and donor-placebo gates pass. Because the timing-coherence gate is not
supported and the World Cup outcome is incomplete, explicit methodological
acceptance is withheld and 'use_counterfactual_candidate' remains false.

## Reproduction and artifacts

Run:

    python -m srmp.ingest.trends_joint
    python -m srmp.experiments.sponsorship_counterfactual_v1

Configuration is in 'config/joint_trends_donors.yaml' and
'config/experiments/sponsorship_counterfactual_v1.yaml'. The outputs include
the common-scale panel, raw draw cache and scale factors, donor registry and
evidence file, donor quality screen, weekly actual/synthetic gap, weights,
placebos, sensitivities, event controls, exposure regression and manifests.

## What remains missing

- approved World Cup activation, tournament and post-window milestone dates;
- refreshed Blinkfire World Cup exposure through at least 13 post-event weeks;
- the exact World Cup activation/match calendar;
- broadcast/GRP exposure;
- Lenovo campaign/media-spend intensity, because current event controls are
  occurrence dummies and Black Friday is only a calendar proxy;
- a final contamination-screen refresh when the World Cup outcome is frozen;
- the post-World-Cup survey and persistence outcome; and
- an approved royalty schedule, BCF-adjusted revenue base, sponsorship fee,
  discount rate and persistence assumptions for monetisation.

## Royalty schedule link

'srmp/roi/royalty_schedule.py' requires at least two approved
'(index_level, royalty_rate)' points and calculates the local slope:

    royalty_bps_per_index_point =
        10000 * (rate_high - rate_low) / (index_high - index_low)

It does not extrapolate beyond the approved Index range. The current schedule
has zero approved points, so no monetary output is produced.
