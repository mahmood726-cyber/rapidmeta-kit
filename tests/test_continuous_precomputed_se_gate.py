"""Regression: pre-extracted continuous SE <= 0 must refuse, not disappear.

Exercises the shipped Node panel through the established UI test harness.
All inputs below are synthetic numerical domain tests, NOT real trial data
or an external R/metafor parity execution.

Source: Cochrane Handbook 10.3, generic inverse-variance weighting:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
"""
import pytest

from test_continuous_variance_gate import COPIES, GOOD_MD, GOOD_SMD, run_panel


BAD_CASES = (
    ("nested_data_zero", GOOD_MD, {"data": {"md": 3.0, "se": 0.0}}, "MD"),
    ("nested_data_negative", GOOD_MD, {"data": {"md": 3.0, "se": -0.2}}, "MD"),
    ("all_outcomes_zero", GOOD_MD,
     {"allOutcomes": [{"type": "CONTINUOUS", "md": 3.0, "se": 0.0}]}, "MD"),
    ("all_outcomes_negative", GOOD_MD,
     {"allOutcomes": [{"type": "CONTINUOUS", "md": 3.0, "se": -0.2}]}, "MD"),
    ("top_level_md_zero", GOOD_MD, {"md": 3.0, "md_se": 0.0}, "MD"),
    ("top_level_md_negative", GOOD_MD, {"md": 3.0, "md_se": -0.2}, "MD"),
    ("top_level_smd_zero", GOOD_SMD, {"smd": 0.3, "smd_se": 0.0}, "SMD"),
    ("top_level_smd_negative", GOOD_SMD, {"smd": 0.3, "smd_se": -0.2}, "SMD"),
)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,base,row,effect", BAD_CASES)
def test_nonpositive_pre_extracted_se_refuses_entire_pool(copy, label, base, row, effect):
    result = run_panel(copy, base + (row,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert f"unrepresentable {effect} effect or variance" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


GOOD_CASES = (
    ("nested_data", GOOD_MD, {"data": {"md": 3.0, "se": 0.2}}, "MD"),
    ("all_outcomes", GOOD_MD,
     {"allOutcomes": [{"type": "CONTINUOUS", "md": 3.0, "se": 0.2}]}, "MD"),
    ("top_level_md", GOOD_MD, {"md": 3.0, "md_se": 0.2}, "MD"),
    ("top_level_smd", GOOD_SMD, {"smd": 0.3, "smd_se": 0.2}, "SMD"),
)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,base,row,effect", GOOD_CASES)
def test_positive_pre_extracted_se_still_pools(copy, label, base, row, effect):
    result = run_panel(copy, base + (row,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith(effect + " "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
