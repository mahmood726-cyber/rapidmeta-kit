"""Regression tests for continuous-vs-ratio outcome routing in the kit dashboard.

These extract the ACTUAL shipped helper methods (isContinuousOutcome,
trialPublishedRatio) from template/base_dupilumab_copd.html and evaluate them in
node, so the test breaks if the guards are removed or weakened.

Why this matters: the published-ratio pooling fix pools log(effect). A mean
difference is NOT a ratio (linear scale, null = 0), so a positive MD (e.g. +83 mL)
must never reach that path or it renders as "Risk Ratio 83". isContinuousOutcome
routes every continuous-family outcome to ContinuousMDEngine first; trialPublishedRatio
refuses any mean-difference value as a defensive second line.
"""
import re
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "template" / "base_dupilumab_copd.html"


def _extract_method(src, name):
    """Slice a `name(args) { ... }` object-method body by brace matching."""
    m = re.search(r"\b" + re.escape(name) + r"\s*\(", src)
    assert m, f"method {name} not found in source"
    # find the '{' that opens the body (after the parameter list)
    i = src.index("{", m.end())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    args = src[m.end():src.index("{", m.end())].strip().rstrip(") ").lstrip("(")
    body = src[i:j + 1]
    return f"function {name}({args}) {body}"


def _run():
    src = BASE.read_text(encoding="utf-8")
    is_cont = _extract_method(src, "isContinuousOutcome")
    pub_ratio = _extract_method(src, "trialPublishedRatio")
    # trialPublishedRatio uses `this` nowhere; isContinuousOutcome neither. Strip a leading
    # method-name collision by exposing them as plain functions.
    snippet = is_cont + "\n" + pub_ratio + "\n" + r"""
    function tpr(d){ return trialPublishedRatio({ data: d }); }
    console.log(JSON.stringify({
      cont_CONTINUOUS: isContinuousOutcome({type:'CONTINUOUS', md:83, se:21}),
      cont_MDtype:     isContinuousOutcome({type:'MD', effect:83, lci:41, uci:125, tE:null, cE:null}),
      cont_SMDestimand:isContinuousOutcome({estimandType:'SMD', effect:0.5}),
      ratio_not_cont:  isContinuousOutcome({type:'PRIMARY', estimandType:'RR', effect:0.70, tE:null, cE:null}),
      md_not_ratio:    tpr({md:83, se:21}) === null,
      smd_not_ratio:   tpr({effect:0.5, lci:0.2, uci:0.8, estimandType:'SMD'}) === null,
      rateratio_ok:    JSON.stringify(tpr({effect:0.70, lci:0.58, uci:0.86, estimandType:'RR'})) === JSON.stringify({est:0.70, lci:0.58, uci:0.86})
    }));
    """
    r = subprocess.run(["node", "-e", snippet], capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, f"node exited {r.returncode}\n{r.stdout}\n{r.stderr}"
    return json.loads([ln for ln in r.stdout.splitlines() if ln.strip()][-1])


def test_continuous_outcomes_route_to_md_engine():
    o = _run()
    assert o["cont_CONTINUOUS"] is True
    assert o["cont_MDtype"] is True
    assert o["cont_SMDestimand"] is True
    assert o["ratio_not_cont"] is False     # a rate ratio is NOT continuous


def test_mean_difference_never_pooled_as_ratio():
    o = _run()
    assert o["md_not_ratio"] is True        # md-bearing -> trialPublishedRatio returns null
    assert o["smd_not_ratio"] is True       # SMD estimand -> null


def test_rate_ratio_still_pools_as_ratio():
    o = _run()
    assert o["rateratio_ok"] is True
