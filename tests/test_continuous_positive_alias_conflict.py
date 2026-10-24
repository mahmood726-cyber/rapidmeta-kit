"""Conflicting positive measured-N aliases must REFUSE rather than silently reweight.

Cochrane Handbook Chapter 6, section 6.5.2 requires arm-specific numbers
whose outcomes were measured; contradictory positive counts require human
source reconciliation, not a silent precedence rule.

Actual three shipped JS modules execute through the Node UI harness with
synthetic fixtures. These tests do not establish external R/metafor parity.
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
@pytest.mark.parametrize("label,aliases", (
    ("treatment_count_conflict", {"tN": 18}),
    ("control_count_conflict", {"cN": 18}),
    ("both_counts_conflict", {"tN": 18, "cN": 18}),
    ("numeric_string_treatment_conflict", {"tN": "18"}),
    ("numeric_string_control_conflict", {"cN": "18"}),
    ("positive_off_by_one", {"tN": 20, "cN": 16}),
))
def test_conflicting_positive_arm_counts_refuse_whole_pool(copy, label, aliases):
    result = run_panel(copy, GOOD + ({**RAW, **aliases},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "conflicting arm sample-size aliases" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,aliases", (
    ("no_alias", {}),
    ("matching_both_aliases", {"tN": 19, "cN": 17}),
    ("matching_treatment_alias", {"tN": 19}),
    ("matching_control_alias", {"cN": 17}),
))
def test_unambiguous_arm_counts_still_pool(copy, label, aliases):
    result = run_panel(copy, GOOD + ({**RAW, **aliases},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith("MD "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
