from srmp.common.contracts import ContractViolation, require_columns


def test_missing_contract_columns_fail_loudly():
    try:
        require_columns({"week"}, {"week", "index_level"}, "C-INDEX")
    except ContractViolation as exc:
        assert "C-INDEX" in str(exc)
    else:
        raise AssertionError("Expected a C-INDEX contract violation")


def test_media_value_is_relative_intensity_only_and_never_monetary_value():
    """P1 as amended by ADR-0028: media value may weight exposure, never value it."""
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "data/staged/media_values/pull_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["banned_as_feature"] is True
    # Only the ingest and the two relative-intensity sensitivities may read it.
    allowed = {
        root / "srmp/ingest/media_values.py",
        root / "srmp/pipeline.py",  # names the ingest step only
        root / "srmp/experiments/sponsorship_counterfactual_v1.py",
        root / "config/experiments/sponsorship_counterfactual_v1.yaml",
        root / "srmp/experiments/world_cup_impact_v1_estimator.py",
        root / "config/experiments/world_cup_impact_v1.yaml",
        root / "srmp/experiments/tv_exposure_check_v1.py",  # television check, ADR-0046
        root / "config/experiments/tv_exposure_check_v1.yaml",
        root / "config/base.yaml",  # declares the ban itself
        # P1 comparison line ("industry-claimed value"), never a breakeven input.
        root / "srmp/experiments/valuation_routes_v1.py",
        root / "config/experiments/valuation_routes_v1.yaml",
    }
    offenders = [
        str(path.relative_to(root))
        for folder in ("srmp", "config")
        for path in (root / folder).rglob("*")
        if path.suffix in {".py", ".yaml"} and path not in allowed
        and any(token in path.read_text(encoding="utf-8")
                for token in ("media_value", "staged/media_values"))
    ]
    assert not offenders, f"media value referenced outside the intensity sensitivity: {offenders}"
    sensitivity = json.loads((
        root / "data/curated/experimental/sponsorship_counterfactual_v1/"
        "media_value_intensity_sensitivity.json"
    ).read_text(encoding="utf-8"))
    assert sensitivity["monetary_totals_used"] is False
    assert sensitivity["role"] == "sensitivity_only_relative_exposure_intensity"
    tv = json.loads((root / "data/curated/experimental/tv_exposure_check_v1/tv_exposure_check_manifest.json").read_text(encoding="utf-8"))
    assert tv["monetary_totals_used"] is False and tv["role"] == "sensitivity_only_relative_exposure_intensity"
