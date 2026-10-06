-- D5 fallback for gdelt-bq.gdeltv2.gkg_partitioned
SELECT
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS date,
  COUNT(DISTINCT DocumentIdentifier) AS news_volume,
  AVG(SAFE_CAST(SPLIT(V2Tone, ',')[SAFE_OFFSET(0)] AS FLOAT64)) AS mean_tone
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONDATE BETWEEN DATE('2022-01-01') AND DATE('2026-10-05')
  AND REGEXP_CONTAINS(LOWER(COALESCE(V2Organizations, '')), r'(^|[;,])lenovo([,;]|$)')
GROUP BY date
ORDER BY date;
