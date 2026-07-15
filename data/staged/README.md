# Staged data

Typed, deduplicated, and normalized intermediate artifacts belong here. Staged outputs should be parquet with an accompanying schema and a link to the raw input manifest.

## Survey exports

Generate `survey/` from the immutable client XLSX files with:

```powershell
python -m srmp.ingest.survey
```

The output includes convenient CSV and Parquet files, a source-hash manifest,
and lossless source-cell coordinates. It intentionally does not create a Brand
Index or combine survey measures that are not demonstrably comparable.
