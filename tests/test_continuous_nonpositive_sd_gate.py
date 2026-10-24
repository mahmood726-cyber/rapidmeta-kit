"""Fail closed rather than silently omitting raw continuous nonpositive-SD trials.

Runs the actual shipped JavaScript through Node for all three copies, using
synthetic-only rows (not an external R oracle or clinical source validation).
Cochrane Handbook 6.5.2 requires arm means, SDs and assessed N.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
A reported zero SD can be genuine; this conservative joint MD/SMD gate asks
for manual source review instead of assuming a positive weighting variance.
"""
import pytest
from test_continuous_variance_gate import COPIES, run_panel

GOOD = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)
RAW = {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2, "n1": 19, "n2": 17}


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,changed", (
    ("negative_treatment_sd", {"sd1": -1}),
    ("negative_control_sd", {"sd2": -2}),
    ("zero_treatment_sd", {"sd1": 0}),
    ("zero_control_sd", {"sd2": 0}),
    ("negative_sd_alternative_count_aliases",
     {"sd2": -1, "tN": 19, "cN": 17}),
))
def test_nonpositive_raw_sd_refuses_instead_of_dropping_study(copy, label, changed):
    result = run_panel(copy, GOOD + ({**RAW, **changed},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "unrepresentable MD effect or variance" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "nonpositive reported SD" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,third", (
    ("positive_raw_sd", {**RAW, "sd1": 1, "sd2": 2}),
    ("positive_raw_sd_aliases",
     {**RAW, "sd1": 2, "sd2": 1, "tN": 19, "cN": 17}),
))
def test_positive_sd_raw_controls_keep_three_studies(copy, label, third):
    result = run_panel(copy, GOOD + (third,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith("MD "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
