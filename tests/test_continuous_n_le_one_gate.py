"""Raw continuous arm N<=1 must REFUSE instead of disappearing from a pool.

Executes each distributed JavaScript module through the repository's actual
Node UI harness with synthetic inputs only. Not a clinical source or an
independent R/metafor validation.

Cochrane Handbook Chapter 6, Section 6.5.2: sample mean, sample SD and number
of measured participants are the required summary data; a reported sample SD
from a one-person arm does not establish a usable sample variance.
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
@pytest.mark.parametrize("label,changed", (
    ("treatment_one", {"n1": 1}),
    ("control_one", {"n2": 1}),
    ("treatment_zero", {"n1": 0}),
    ("control_zero", {"n2": 0}),
    ("treatment_negative", {"n1": -2}),
    ("control_negative", {"n2": -3}),
    ("alternative_count_one", {"tN": 1, "cN": 17}),
))
def test_raw_n_le_one_refuses_without_silent_k_reduction(copy, label, changed):
    result = run_panel(copy, GOOD + ({**RAW, **changed},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "Pooling REFUSED" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,third", (
    ("valid_raw_n", RAW),
    ("two_each", {**RAW, "n1": 2, "n2": 2}),
    ("valid_alternative_count_names", {**RAW, "tN": 19, "cN": 17}),
))
def test_valid_raw_counts_keep_three_trial_pool(copy, label, third):
    result = run_panel(copy, GOOD + (third,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith("MD "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
