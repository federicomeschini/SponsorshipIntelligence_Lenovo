# Raw data

Raw client/API pulls are immutable. Files are grouped by source and retain their original format. Any parsing, typing, deduplication, normalization, or aggregation belongs in `data/staged/` or `data/curated/`.

Every future connector pull must also emit a `pull_manifest.json` containing the source, query parameters, pull timestamp, row count, and content hash.

## Vintages

Connectors whose raw filenames carry no date write each refresh to its own
vintage folder named by the pull end date, so earlier pulls are never
overwritten: `trends/anonymous/<end>/` and `trends_joint_donors/<end>/`. The
July 2026 vintage predates this layout and sits directly in those folders.
Market, GDELT and Wikipedia filenames already carry their date window.

## Client exposure exports

- `blinkfire/lenovo_sponsorship_exposure_daily_export.csv` — daily impressions/views,
  2024-10-01 to 2026-06-11.
- `blinkfire/impressions_views_by_wc.xlsx` — same layout, 2026-06-11 to 2026-07-20
  (Men's World Cup). On the overlapping day the later export replaces the earlier one.
- `media_values/lenovo_media_values_fifa_competitions_oct24_apr26.xlsx` — media
  equivalency (100% and QI-adjusted) by brand line, FIFA competition and market,
  dated 2025-05 to 2026-04 despite the filename. AVE-style value: comparison line
  only, banned as a model input (ARCHITECTURE P1, W-08).
