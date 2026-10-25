"""Do not silently omit an explicitly supplied incomplete continuous study.

Cochrane Handbook chapter 6 §6.5.2: raw MD/SMD requires measured
arm-specific mean, SD and sample size. Missing values must trigger source
review, not an unexplained smaller k or JavaScript null/blank-to-zero coercion.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06

These are synthetic Node UI regressions on actual distributed JavaScript.
They do not demonstrate independently verified R/metafor MD/SMD parity.
"""
import pytest

from test_continuous_variance_gate import COPIES, run_panel

GOOD = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)
RAW = {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2, "n1": 19, "n2": 17}


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,broken", (
    ("missing_treatment_mean", {"mean2": 1, "sd1": 1, "sd2": 2, "n1": 19, "n2": 17}),
    ("missing_control_mean", {"mean1": 3, "sd1": 1, "sd2": 2, "n1": 19, "n2": 17}),
    ("missing_treatment_sd", {"mean1": 3, "mean2": 1, "sd2": 2, "n1": 19, "n2": 17}),
    ("missing_control_sd", {"mean1": 3, "mean2": 1, "sd1": 1, "n1": 19, "n2": 17}),
    ("missing_treatment_n", {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2, "n2": 17}),
    ("missing_control_n", {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2, "n1": 19}),
    ("null_treatment_mean", {**RAW, "mean1": None}),
    ("blank_control_mean", {**RAW, "mean2": ""}),
    ("nonnumeric_control_sd", {**RAW, "sd2": "not reported"}),
))
def test_explicit_incomplete_raw_continuous_refuses_instead_of_dropping(copy, label, broken):
    result = run_panel(copy, GOOD + (broken,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,rows,expected_k", (
    ("valid_raw", GOOD + (RAW,), 3),
    ("numeric_string_measurements", GOOD + ({**RAW, "mean1": "3", "mean2": "1",
                                            "sd1": "1", "sd2": "2"},), 3),
    ("unrelated_binary_row", GOOD + ({"tE": 2, "tN": 20, "cE": 3, "cN": 20},), 2),
))
def test_complete_continuous_still_pools_and_binary_rows_do_not_create_candidates(
    copy, label, rows, expected_k
):
    result = run_panel(copy, rows)
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert "k=" + str(expected_k) in result["summary"], label
    assert "REFUSED" not in result["summary"], label


@pytest.mark.parametrize("copy", COPIES)
def test_binary_only_input_is_not_misclassified_as_raw_continuous(copy):
    result = run_panel(copy, (
        {"tE": 1, "tN": 20, "cE": 2, "cN": 20},
        {"n1": 20, "n2": 20, "tE": 3, "cE": 2},
    ))
    assert result["rendered"] is False
