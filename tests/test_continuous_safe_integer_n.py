"""Synthetic domain regression: raw continuous N must be a safe integer.

Runs the actual Node continuous panel in all three shipped copies. Cochrane
Handbook 6.5.2 extracts the number of participants assessed in each arm:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
No source clinical effects or R/oracle outputs are inferred from these tests.
"""
import pytest
from test_continuous_variance_gate import COPIES, run_panel

BASE = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)
ROW = {"mean1": 3, "mean2": 1, "sd1": 1, "sd2": 2}
UNSAFE = 2 ** 53

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,counts", (
    ("fractional_treatment", {"n1": 9.5, "n2": 18}),
    ("fractional_control", {"n1": 9, "n2": 18.5}),
    ("unsafe_treatment", {"n1": UNSAFE, "n2": 18}),
    ("unsafe_control", {"n1": 9, "n2": UNSAFE}),
))
def test_invalid_raw_arm_n_refuses_whole_pool(copy, label, counts):
    result = run_panel(copy, BASE + ({**ROW, **counts},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "unrepresentable MD effect or variance" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,counts", (
    ("integer_counts", {"n1": 9, "n2": 18}),
    ("alternative_count_names", {"tN": 15, "cN": 40}),
))
def test_valid_raw_integer_arm_n_still_pools(copy, label, counts):
    result = run_panel(copy, BASE + ({**ROW, **counts},))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert result["summary"].startswith("MD "), label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
