# Lenovo-only multi-signal index comparison

> **STALE: not synchronized with the October 2026 production state (labelled 2026-10-06).**
> - *Affected:* all comparison statistics (now include GDELT and Trends through early October 2026)
> - *Why not updated yet:* the October 2026 refresh (ADR-0027) re-ran this experiment; the narrative was not rewritten in the same session
> - *Consequence for interpretation:* comparison figures are July values
> - *Required action:* refresh within the Brand Index review notebook (tracked under "Open documentation actions" in `README.md`).

This is an experimental comparison of Lenovo-only brand-performance composites.
It does not replace the canonical simple parent-brand salience index. It is a
descriptive measurement comparison, not a forecast competition.

| Method | Final weights / loadings | GWI level correlation | Leave-one-quarter result |
|---|---:|---:|---|
| Evidence-weighted | Brand 26.1%, portfolio 33.1%, intent 17.6%, tone 23.2% | 0.681 | No component shifts by more than 7.8 percentage points. |
| PCA | Brand 0.572, portfolio 0.575, intent 0.543, tone 0.216 | 0.676 | Principal loadings are very stable; largest shift is 0.046. |
| Entropy reference | Brand 15.5%, portfolio 19.9%, intent 52.5%, tone 12.2% | 0.649 | Retained only as a mechanical sensitivity check. |

Evidence-weighted and PCA series have a 0.988 weekly correlation and a maximum
gap of 0.865 display-index points. The detailed construction, survey role,
exclusions, formulas, and choice guidance are in
[brand_index_construction.md](brand_index_construction.md).

Regenerate the comparison and manifest with:

    python -m srmp.index.multisignal_compare
