from srmp.common.contracts import ContractViolation, require_columns


def test_missing_contract_columns_fail_loudly():
    try:
        require_columns({"week"}, {"week", "index_level"}, "C-INDEX")
    except ContractViolation as exc:
        assert "C-INDEX" in str(exc)
    else:
        raise AssertionError("Expected a C-INDEX contract violation")
