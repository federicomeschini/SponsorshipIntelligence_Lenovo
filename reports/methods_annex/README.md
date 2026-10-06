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
| [`10_total_sponsorship_effect.ipynb`](10_total_sponsorship_effect.ipynb) | **Headline:** how much did the FIFA sponsorship lift Lenovo's brand salience overall? | `sponsorship_total_effect_v1`; context from `sponsorship_counterfactual_v1` and `sponsorship_monetization_v1` (exposure) |
| [`20_world_cup_close_up.ipynb`](20_world_cup_close_up.ipynb) | Close-up: the World Cup within the total effect, and its incremental effect (interim) | `sponsorship_total_effect_v1`, `world_cup_impact_v1` |
| [`30_cobrand_association.ipynb`](30_cobrand_association.ipynb) | Do people link Lenovo with FIFA more than other brands? | `cobrand_placebo_v1` |
| [`40_brand_value.ipynb`](40_brand_value.ipynb) | What is the brand worth, and what does the total lift add? | `brand_value_dcf_v1`, `brand_value_dominance_v1`, `sponsorship_total_return_v3`, `valuation_routes_v1` |

## Markdown annexes

| Document | Status |
|---|---|
| [`survey_source_audit.md`](survey_source_audit.md) | Current (no new survey exports since July 2026) |
| [`world_cup_impact_preregistration.md`](world_cup_impact_preregistration.md) | Protocol current; implementation status noted at the top |
| [`experimental_sponsorship_counterfactual_v1.md`](experimental_sponsorship_counterfactual_v1.md) | Superseded by `10_total_sponsorship_effect.ipynb`; historical July record |
| [`data_readiness_audit.md`](data_readiness_audit.md) | Superseded for coverage by `00_data_inputs.ipynb`; survey findings current |
| [`brand_index_construction.md`](brand_index_construction.md) | **Stale** |
| [`multisignal_index_comparison.md`](multisignal_index_comparison.md) | **Stale** |
| [`stock_brand_response_v2.md`](stock_brand_response_v2.md) | **Stale** |
| [`brand_financial_bridge_v1.md`](brand_financial_bridge_v1.md) | **Stale** |
| [`market_implied_earnings_bridge_v1.md`](market_implied_earnings_bridge_v1.md) | **Stale** |
| [`experimental_sponsorship_monetization_v1.md`](experimental_sponsorship_monetization_v1.md) | **Stale** |
| [`sponsorship_total_return_v2.md`](sponsorship_total_return_v2.md), [`world_cup_simulation_v1.md`](world_cup_simulation_v1.md) | Retired experiments (ADR-0036); historical record |

## Open documentation actions

These outputs are **not done** under the definition of done in `AGENTS.md` until their review artifact is current:

1. Brand Index construction and multi-signal comparison: rewrite as a review notebook (`stock_brand_response_v2`, the valuation and the uplift analyses all depend on the index).
2. `stock_brand_response_v2`: rewrite as a review notebook; current estimates differ materially from the July text.
3. `brand_financial_bridge_v1` and `market_implied_earnings_bridge_v1`: rewrite or fold into `40_brand_value.ipynb`.
4. `sponsorship_monetization_v1`: rewrite as a review notebook.
