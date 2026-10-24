"""Explicit zero arm-count aliases must not be silently replaced in continuous pooling.

Exercise the actual three distributed JS modules through the existing Node UI
harness. These are synthetic input-validation checks, NOT continuous-outcome
numeric parity with native R/metafor, independent clinical validation, or a
decision about conflicting positive sample-size aliases.

Cochrane Handbook v6.5 Ch 6 §6.5.2 requires the number of participants whose
outcome was measured in each arm; no positive fallback may silently replace a
present zero/blank reported count without source adjudication.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
"""
import pytest

from test_continuous_variance_gate import COPIES, run_panel

GOOD = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)
RAW = {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2, "n1": 19, "n2": 17}


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,alias", (
    ("treatment_numeric_zero", {"tN": 0}),
    ("control_numeric_zero", {"cN": 0}),
    ("treatment_string_zero", {"tN": "0"}),
    ("control_string_zero", {"cN": "0"}),
    ("treatment_blank", {"tN": ""}),
    ("control_null", {"cN": None}),
))
def test_explicit_invalid_alias_refuses_instead_of_using_positive_alternate(
    copy, label, alias,
):
    result = run_panel(copy, GOOD + ({**RAW, **alias},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "Pooling REFUSED" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,alias", (
    ("no_alias", {}),
    ("matching_both_aliases", {"tN": 19, "cN": 17}),
    ("matching_treatment_alias", {"tN": 19}),
))
def test_valid_continuous_alias_controls_remain_pooled(copy, label, alias):
    result = run_panel(copy, GOOD + ({**RAW, **alias},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith("MD "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
