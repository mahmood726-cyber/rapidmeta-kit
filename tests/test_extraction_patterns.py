"""Regression tests for the effect-size extraction CI-separator fix.

Bug (confirmed empirically): rate-ratio and Cohen's d / Hedges' g confidence
intervals written with "to" (e.g. "rate ratio 0.70 (95% CI 0.58 to 0.86)") were
MISSED because those patterns used a dash-only CI separator. The dupilumab primary
outcome is exactly that shape, so the extractor would not see it.

Fix: SEP and TO are unified to (?:to|dash|comma) and every inline dash-only CI
separator now uses SEP. These tests extract the SHIPPED constants + a pattern from
the HTML and assert to/dash/comma all parse, and that no dash-only separator remains.
"""
import re
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "template" / "base_dupilumab_copd.html"


def _const(src, name):
    m = re.search(r"const " + name + r"\s*=\s*'((?:[^'\\]|\\.)*)'", src)
    assert m, f"const {name} not found"
    return m.group(1)


def test_sep_and_to_accept_to_dash_and_comma():
    src = BASE.read_text(encoding="utf-8")
    sep, to = _const(src, "SEP"), _const(src, "TO")
    for name, val in (("SEP", sep), ("TO", to)):
        assert "to" in val, f"{name} should accept the word 'to': {val!r}"
        assert "," in val, f"{name} should accept a comma separator: {val!r}"
        assert "2013" in val or "\\u2013" in val, f"{name} should still accept an en-dash: {val!r}"


def test_no_dash_only_ci_separator_remains():
    src = BASE.read_text(encoding="utf-8")
    # the old dash-only separator literal must be gone (replaced by SEP)
    assert "[-\\u2013\\u2014]\\s*' + " not in src, "a dash-only CI separator survived the fix"


def test_rate_ratio_and_cohens_d_with_to_now_parse():
    src = BASE.read_text(encoding="utf-8")
    sep = _const(src, "SEP")
    snippet = """
    const N = '(\\\\d+\\\\.?\\\\d*)', SN = '(-?\\\\d+\\\\.?\\\\d*)';
    const SEP = '%s';
    const CI_LABEL = '(?:95%%?[\\\\s-]*)?(?:CI|KI|IC|BI|CrI|CL)?';
    const irr = new RegExp('(?:incidence\\\\s+)?rate\\\\s*ratio[,;:\\\\s=]+' + N + '\\\\s*\\\\(\\\\s*' + CI_LABEL + '[,:\\\\s]*' + N + '\\\\s*' + SEP + '\\\\s*' + N, 'i');
    const smd = new RegExp("Cohen'?s?\\\\s+d[,;:\\\\s=]+" + SN + '\\\\s*\\\\(\\\\s*' + CI_LABEL + '[,:\\\\s]*' + SN + '\\\\s*' + SEP + '\\\\s*' + SN, 'i');
    function hit(re, s){ const m = re.exec(s); return m ? [parseFloat(m[1]),parseFloat(m[2]),parseFloat(m[3])] : null; }
    console.log(JSON.stringify({
      rr_to:    hit(irr, "rate ratio 0.70 (95%% CI 0.58 to 0.86)"),
      rr_dash:  hit(irr, "rate ratio 0.70 (95%% CI 0.58-0.86)"),
      rr_comma: hit(irr, "rate ratio 0.70 (95%% CI 0.58, 0.86)"),
      d_to:     hit(smd, "Cohen's d -0.45 (95%% CI -0.80 to -0.10)")
    }));
    """ % sep
    r = subprocess.run(["node", "-e", snippet], capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, f"node failed\n{r.stdout}\n{r.stderr}"
    out = json.loads([ln for ln in r.stdout.splitlines() if ln.strip()][-1])
    assert out["rr_to"] == [0.70, 0.58, 0.86], out      # the dupilumab "to" shape
    assert out["rr_dash"] == [0.70, 0.58, 0.86], out
    assert out["rr_comma"] == [0.70, 0.58, 0.86], out
    assert out["d_to"] == [-0.45, -0.80, -0.10], out
