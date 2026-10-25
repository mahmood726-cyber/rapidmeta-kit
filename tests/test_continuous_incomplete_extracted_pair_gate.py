"""Prevent silent loss of incomplete pre-extracted continuous MD/SMD studies.

Runs actual production JS with synthetic input through Node, NOT clinical
validation or independent native R/metafor MD/SMD oracle verification.
Cochrane v6.5 chapters 6 and 10 require comparable continuous outcomes,
usable study-level effect estimates and uncertainty before inverse-variance
synthesis.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
"""
import pytest
from test_continuous_variance_gate import COPIES, run_panel

GOOD = (
    {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 20, "n2": 20},
    {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 30, "n2": 30},
)
BROKEN = (
    ("nested_missing_se", {"allOutcomes": [{"type": "CONTINUOUS", "md": 1.2}]}),
    ("nested_null_md", {"allOutcomes": [{"type": "continuous", "md": None, "se": 0.2}]}),
    ("nested_blank_se", {"allOutcomes": [{"type": "CONTINUOUS", "md": 1.2, "se": ""}]}),
    ("nested_nonnumeric_md", {"allOutcomes": [{"type": "CONTINUOUS", "md": "not reported", "se": 0.2}]}),
    ("data_missing_se", {"data": {"md": 1.2}}),
    ("data_null_md", {"data": {"md": None, "se": 0.2}}),
    ("data_missing_md", {"data": {"se": 0.2}}),
    ("top_md_missing_se", {"md": 1.2}),
    ("top_md_missing_md", {"md_se": 0.2}),
    ("top_md_null_se", {"md": 1.2, "md_se": None}),
    ("top_smd_missing_se", {"smd": 0.2}),
    ("top_smd_missing_smd", {"smd_se": 0.2}),
    ("top_smd_blank_smd", {"smd": "", "smd_se": 0.2}),
)
VALID = (
    ("nested_valid", {"allOutcomes": [{"type": "CONTINUOUS", "md": 1.2, "se": 0.2}]}, 3),
    ("data_valid", {"data": {"md": 1.2, "se": 0.2}}, 3),
    ("top_md_valid", {"md": 1.2, "md_se": 0.2}, 3),
    ("top_smd_valid", {"smd": 0.2, "smd_se": 0.2}, 2),
    ("unrelated_binary", {"tE": 1, "tN": 20, "cE": 2, "cN": 20}, 2),
)

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,broken", BROKEN)
def test_incomplete_preextracted_continuous_refuses(copy, label, broken):
    panel = run_panel(copy, GOOD + (broken,))
    assert panel["rendered"] is True, label
    assert panel["badge"] == "Continuous · REFUSED", label
    assert "trial 3" in panel["summary"], label
    assert "No continuous outcome pooled" in panel["bodyHtml"], label
    assert "Pooled MD" not in panel["bodyHtml"], label
    assert "Pooled SMD" not in panel["bodyHtml"], label

@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,valid,k", VALID)
def test_valid_extracted_or_unrelated_binary_still_renders(copy, label, valid, k):
    panel = run_panel(copy, GOOD + (valid,))
    assert panel["rendered"] is True, label
    assert panel["badge"] == "Continuous", label
    assert "k=" + str(k) in panel["summary"], label
