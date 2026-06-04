"""Unit tests for clone.py's pure rendering helpers.

These exercise the JS-literal generation that turns a config into the
``realData`` block. The highest-value case is js_escape on an apostrophe:
an unescaped ``'`` inside a single-quoted JS string literal terminates the
string and breaks the whole dashboard (a real past-incident class).
"""
from __future__ import annotations


def test_js_escape_apostrophe(clone_mod):
    # Trial / drug names with apostrophes must not break the JS literal.
    assert clone_mod.js_escape("Crohn's disease") == "Crohn\\'s disease"


def test_js_escape_backslash_before_quote(clone_mod):
    # Backslash must be escaped first so it can't eat the quote escape.
    assert clone_mod.js_escape("a\\'b") == "a\\\\\\'b"


def test_js_escape_coerces_non_strings(clone_mod):
    assert clone_mod.js_escape(2024) == "2024"


def test_jsnum_none_is_null(clone_mod):
    assert clone_mod._jsnum(None) == "null"


def test_jsnum_zero_preserved(clone_mod):
    # 0 events is a real value, not "missing" -> must render as 0, not null.
    assert clone_mod._jsnum(0) == "0"


def test_jsnum_float(clone_mod):
    assert clone_mod._jsnum(0.86) == "0.86"


def test_render_outcome_emits_quoted_labels_and_bare_numbers(clone_mod):
    out = clone_mod.render_outcome(
        {"shortLabel": "Primary", "title": "MACE", "type": "binary",
         "tE": 10, "effect": 0.8}
    )
    assert "shortLabel: 'Primary'" in out
    assert "title: 'MACE'" in out
    assert "type: 'binary'" in out
    assert "tE: 10" in out          # numbers are bare
    assert "effect: 0.8" in out
    assert out.startswith("{ ") and out.endswith(" }")


def test_render_trial_entry_defaults(clone_mod):
    entry = clone_mod.render_trial_entry(
        {"nct": "NCT01234567", "name": "ACME-1"}, "Drug vs Placebo"
    )
    assert entry.startswith("'NCT01234567':")
    assert "name: 'ACME-1'" in entry
    assert "phase: 'III'" in entry          # default phase
    assert "year: 2024" in entry            # default year
    assert "tE: null" in entry              # missing arm data -> null
    assert "group: 'Drug vs Placebo'" in entry
    assert "allOutcomes:" in entry          # synthesised default outcome
    assert "clinicaltrials.gov/study/NCT01234567" in entry
    # Default risk-of-bias is 5 "some-concerns" domains.
    assert entry.count("'some-concerns'") == 5


def test_render_trial_entry_published_hr_aliases(clone_mod):
    entry = clone_mod.render_trial_entry(
        {"nct": "NCT1", "name": "HR-trial", "publishedHR": 0.86,
         "hrLCI": 0.75, "hrUCI": 0.99}, "g"
    )
    # pubHR/pubHR_LCI/pubHR_UCI fall back to publishedHR/hrLCI/hrUCI.
    assert "publishedHR: 0.86" in entry
    assert "pubHR: 0.86" in entry
    assert "pubHR_LCI: 0.75" in entry
    assert "pubHR_UCI: 0.99" in entry


def test_replace_realdata_block_brace_matched(clone_mod):
    src = "var x = { realData: { 'OLD': { a: {b:1} } }, other: 2 };"
    out = clone_mod.replace_realdata_block(src, "'NEW': {}")
    assert "'NEW': {}" in out
    assert "'OLD'" not in out
    # Surrounding code is preserved.
    assert out.startswith("var x = { realData: {")
    assert out.endswith("}, other: 2 };")
