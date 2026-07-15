# Raw data

Raw client/API pulls are immutable. Files are grouped by source and retain their original format. Any parsing, typing, deduplication, normalization, or aggregation belongs in `data/staged/` or `data/curated/`.

Every future connector pull must also emit a `pull_manifest.json` containing the source, query parameters, pull timestamp, row count, and content hash.
