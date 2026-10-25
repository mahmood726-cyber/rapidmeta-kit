"""No silent first-outcome selection when a trial supplies multiple extracted effects.

Cochrane Handbook Ch 3 and Ch 9 recommend prespecified, result-independent
outcome selection; these synthetic Node/UI checks are NOT clinical validation
or an independent R oracle.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-03
https://training.cochrane.org/handbook/current/chapter-09
"""
import pytest
from test_continuous_variance_gate import COPIES, run_panel

GOOD = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)

FIRST = {"type": "CONTINUOUS", "md": 1.2, "se": 0.2}
SECOND = {"type": "CONTINUOUS", "md": -3.4, "se": 0.3}

AMBIGUOUS = (
    ("two_distinct", {"allOutcomes": [FIRST, SECOND]}),
    ("duplicate_effects_not_proven_same_estimand", {"allOutcomes": [FIRST, dict(FIRST)]}),
    ("second_incomplete", {"allOutcomes": [FIRST, {"type": "continuous", "md": 2.1}]}),
    ("data_nested", {"data": {"allOutcomes": [FIRST, SECOND]}}),
)

ACCEPTED = (
    ("single_extracted", {"allOutcomes": [FIRST]}),
    ("unrelated_binary_entry", {"allOutcomes": [FIRST, {"type": "BINARY", "md": 0.7, "se": 0.1}]}),
    ("data_nested_single", {"data": {"allOutcomes": [FIRST]}}),
)

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,trial", AMBIGUOUS)
def test_multiple_extracted_effects_refuse_whole_panel(copy, label, trial):
    result = run_panel(copy, GOOD + (trial,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert "multiple extracted continuous outcomes" in result["summary"], label
    assert "trial 3" in result["summary"], label
    assert "No continuous outcome pooled" in result["bodyHtml"], label
    assert "Pooled MD" not in result["bodyHtml"], label
    assert "Pooled SMD" not in result["bodyHtml"], label

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,trial", ACCEPTED)
def test_unambiguous_continuous_effect_still_pools(copy, label, trial):
    result = run_panel(copy, GOOD + (trial,))
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous", label
    assert "k=3" in result["summary"], label
    assert "REFUSED" not in result["summary"], label
