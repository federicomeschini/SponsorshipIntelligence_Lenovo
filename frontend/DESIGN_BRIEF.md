# FIFA-first executive product redesign

> **Historical (FE-009, 2026-10-07).** This brief describes the retired V0–V7 screens. The Lenovo case is now `lenovo.html` in the EROI design.

## 1. Feature summary

Reframe the existing sponsorship dashboard as a Lenovo × FIFA decision product for Lenovo executives. Remove visible portfolio-property content and reorganize the experience around the financial case, causal proof, and the supporting FIFA evidence chain.

## 2. Primary user action

Understand and confidently communicate the answer to: “Is the Lenovo × FIFA partnership creating defensible financial and brand value?”

## 3. Design direction

The experience is assured, tournament-scale, and evidence-led. It should feel like an executive command brief: strong conclusions, sharp hierarchy, disciplined charts, and explicit evidence status rather than a collection of interchangeable dashboard cards.

## 4. Layout strategy

- Put Financial case and Proof directly after the overview in navigation.
- Turn the overview into an investment thesis: return and value as the dominant figures, proof and reach as supporting evidence.
- Use a two-speed hierarchy: large decision panels for proof/finance; quieter supporting screens for exposure, attention, and perception.
- Eliminate the portfolio comparison screen and all visible non-FIFA property lists.
- Keep charts full-width when they carry the principal argument; pair them with concise verdict rails rather than equal card grids.

## 5. Key states

- Default: illustrative demo data is available and clearly labelled.
- Narrow viewport: navigation becomes a horizontally scrollable chapter bar; decision panels stack in narrative order.
- Reduced motion: all content appears immediately and charts remain functional.
- Missing data: the shell must fail clearly instead of showing broken or misleading partial metrics.

## 6. Interaction model

- Hash-routed chapters remain directly addressable.
- Overview decision panels navigate to Proof and Financial case.
- Scenario controls update the financial waterfall and conclusion immediately.
- Chart export remains a secondary action.
- Hover and focus states clarify clickability but contain no unique information.

## 7. Content requirements

- Use “FIFA partnership” consistently; avoid “portfolio” except in methodology explaining excluded comparisons.
- State causal claims as counterfactual evidence, not certainty.
- Label illustrative, simulated, and modelled figures where users encounter them.
- Use executive questions as chapter titles and short verdicts as supporting copy.

## 8. Recommended references

- `spatial-design.md`
- `typography.md`
- `color-and-contrast.md`
- `responsive-design.md`
- `ux-writing.md`

## 9. Open questions

None blocking. The existing OpenEconomics design system, static no-build architecture, Chart.js data contract, and English executive audience remain fixed constraints.

