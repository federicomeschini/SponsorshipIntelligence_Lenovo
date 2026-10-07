# Methods annex: human-review artifacts

Every substantive output of this project has a review artifact here, written for a reader with no project history (standard: [`AGENTS.md`](../../AGENTS.md)). Notebooks import and call the production code in `srmp/`; they are read-only unless their `RUN_REBUILD` flag is set.

**Keep them synchronized.** After any rebuild, re-run the notebooks:

```
python -m srmp.pipeline --tests      # rebuild outputs
python -m srmp.review                # re-execute every review notebook in place
```

Each notebook records the hash of every production file it read; `tests/test_review_artifacts.py` fails when a file changed after the notebook was last executed.

## Review notebooks (current)

| Notebook | Question | Production experiments |
|---|---|---|
| [`00_data_inputs.ipynb`](00_data_inputs.ipynb) | What data are used, how current, how checked? | `srmp/ingest/*`, `srmp/exposure/aggregate.py` |
| [`05_brand_index.ipynb`](05_brand_index.ipynb) | **The Brand Index:** how strong is the Lenovo brand week by week, against its rivals and consistent with the GWI survey? | `srmp/index/brand_factor.py` (ADR-0039, ADR-0040); the superseded `srmp/index/proxy_led.py` as cross-check |
| [`10_total_sponsorship_effect.ipynb`](10_total_sponsorship_effect.ipynb) | **Primary estimate:** how much did the FIFA sponsorship lift Lenovo's Brand Index? FIFA-specific effect (ADR-0043), with the total effect as upper band | `sponsorship_total_effect_v1` (headline, `share_of_search` and `search_salience` configs); `sponsorship_exposure_timing_v1` (FIFA vs other sponsorships); context from `sponsorship_counterfactual_v1` and `sponsorship_monetization_v1` (exposure) |
| [`15_exposure_and_survey_lift.ipynb`](15_exposure_and_survey_lift.ipynb) | How much FIFA exposure was delivered, how does it line up with survey lift by property, and what blocks a royalty-relief value? | `sponsorship_monetization_v1` |
| [`20_world_cup_close_up.ipynb`](20_world_cup_close_up.ipynb) | Close-up: the World Cup within the total effect, and its incremental effect (interim) | `sponsorship_total_effect_v1`, `world_cup_impact_v1` |
| [`30_cobrand_association.ipynb`](30_cobrand_association.ipynb) | Do people link Lenovo with FIFA more than other brands? | `cobrand_placebo_v1` |
| [`35_financial_links.ipynb`](35_financial_links.ipynb) | Do Brand Index moves show up in share-price returns or profit margins, and what per-point earnings coefficient is used for planning? | `stock_brand_response_v2`, `brand_financial_bridge_v1`, `market_implied_earnings_bridge_v1` |
| [`40_brand_value.ipynb`](40_brand_value.ipynb) | What is the brand worth (income split), and what did FIFA add? | `brand_value_dcf_v2` (primary, ADR-0045), `brand_value_dominance_v1` (brand contribution factor), cross-checks from `sponsorship_total_return_v3`, `valuation_routes_v1` |

## Markdown annexes

| Document | Status |
|---|---|
| [`survey_source_audit.md`](survey_source_audit.md) | Current (no new survey exports since July 2026) |
| [`world_cup_impact_preregistration.md`](world_cup_impact_preregistration.md) | Protocol current; implementation status noted at the top |
| [`experimental_sponsorship_counterfactual_v1.md`](experimental_sponsorship_counterfactual_v1.md) | Superseded by `10_total_sponsorship_effect.ipynb`; historical July record |
| [`data_readiness_audit.md`](data_readiness_audit.md) | Superseded for coverage by `00_data_inputs.ipynb`; survey findings current |
| [`brand_index_construction.md`](brand_index_construction.md) | Superseded by `05_brand_index.ipynb` (describes the search-salience index, now a cross-check) |
| [`multisignal_index_comparison.md`](multisignal_index_comparison.md) | Retired (ADR-0041); historical record of variants of the superseded search-salience index |
| [`stock_brand_response_v2.md`](stock_brand_response_v2.md), [`brand_financial_bridge_v1.md`](brand_financial_bridge_v1.md), [`market_implied_earnings_bridge_v1.md`](market_implied_earnings_bridge_v1.md) | Superseded by `35_financial_links.ipynb`; historical July record |
| [`experimental_sponsorship_monetization_v1.md`](experimental_sponsorship_monetization_v1.md) | Superseded by `15_exposure_and_survey_lift.ipynb`; historical July record |
| [`sponsorship_total_return_v2.md`](sponsorship_total_return_v2.md), [`world_cup_simulation_v1.md`](world_cup_simulation_v1.md) | Retired experiments (ADR-0036); historical record |

## Open documentation actions

None. Every experiment in `srmp/experiments/` has a current review notebook, and the Brand Index has `05_brand_index.ipynb`. The search-salience cross-check index (`srmp/index/composite.py`, `srmp/index/proxy_led.py`) is used only for cross-checks: its method is described in `brand_index_construction.md` (method unchanged; quoted statistics are July values) and its current series is compared with the Brand Index in `05_brand_index.ipynb` §5.7 and `10_total_sponsorship_effect.ipynb` §5.6. ADR-0041 retired the multi-signal comparison and repointed the monetisation gate to the headline.
