# Curated data

Analysis-ready contract artifacts belong here. Curated outputs must satisfy the relevant contract schema and must not recompute statistics in the visualization layer.

The current C-INDEX artifact is index/brand_index_weekly.parquet. It is a
provisional, proxy-led Lenovo brand-salience index (v4_proxy_led_brand_calibrated):
the worldwide Lenovo Trends query supplies weekly movement and the GWI
engagement/consideration composite supplies orientation and display-scale
calibration. Product, price, co-branded, competitor, Wikipedia and GDELT series
remain curated companion data; they are not pooled into the headline index.
The retained Trends dimensions are exposed separately in
index/brand_index_components_weekly.parquet.

Experimental Lenovo-only multi-signal alternatives are in
index/brand_index_method_comparison_weekly.parquet. They compare
evidence-weighted, PCA and Shannon-entropy rules without replacing C-INDEX;
see reports/methods_annex/multisignal_index_comparison.md for validation.
