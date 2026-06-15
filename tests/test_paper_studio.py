"""Structural tests for the Paper Studio report-length preset (paper-studio.js).

PS.render() builds the whole paper as an HTML string and writes it into #paperCanvas.
We eval the module under a minimal DOM stub, capture that HTML in both report
lengths, and assert the section gating:

  * SHORT (~1000 words): primary forest + Risk of bias (MANDATORY) + GRADE (optional)
    + Discussion, but NO publication-bias / subgroup / diagnostics battery.
  * FULL: all of the above PLUS publication bias, the NEW subgroup section, and the
    sensitivity/diagnostics battery (leave-one-out relabelled "Sensitivity analysis").

Risk of bias is never gated; GRADE stays present (optional) in both.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PS_JS = ROOT / "template" / "assets" / "js" / "paper-studio.js"


def _render_both():
    snippet = r"""
    global.window = { addEventListener: function(){}, matchMedia: function(){ return { matches:false, addEventListener:function(){}, addListener:function(){} }; } };
    global.localStorage = { getItem: function(){return null;}, setItem: function(){} };
    var captured = {};
    function fakeEl() {
      return {
        _h: "",
        get innerHTML(){ return this._h; },
        set innerHTML(v){ this._h = v; },
        querySelector: function(){ return null; },
        querySelectorAll: function(){ return []; },
        appendChild: function(){}, setAttribute: function(){}, removeAttribute: function(){},
        addEventListener: function(){}, classList: { add:function(){}, remove:function(){} },
        style: {}, hidden: false, value: "", innerText: ""
      };
    }
    global.document = {
      getElementById: function(id){ var e = captured[id] || (captured[id] = fakeEl()); return e; },
      querySelector: function(){ return null; },
      querySelectorAll: function(){ return []; },
      createElement: function(){ return fakeEl(); },
      addEventListener: function(){}
    };
    var fs = require('fs');
    eval(fs.readFileSync('template/assets/js/paper-studio.js','utf8'));
    var PS = global.window.PaperStudio;
    // post-render DOM builders are not under test — stub to no-ops
    PS.buildWizard = function(){}; PS.buildSectionGuides = function(){}; PS.updateProtocolLink = function(){};
    PS.state.analysis.kStudies = "4";  // few-studies path

    PS.state.style.reportLength = "full";  PS.render();
    var full = captured["paperCanvas"].innerHTML;
    PS.state.style.reportLength = "short"; PS.render();
    var short = captured["paperCanvas"].innerHTML;

    function has(s, re){ return new RegExp(re).test(s); }
    console.log(JSON.stringify({
      full_funnel:       has(full,  "Are small studies missing"),
      full_subgroup:     has(full,  "Subgroup analysis"),
      full_diagnostics:  has(full,  "Visual diagnostics"),
      full_sensitivity:  has(full,  "Sensitivity analysis \\(leave-one-out\\)"),
      full_rob:          has(full,  "Risk of bias"),
      full_grade:        has(full,  "Certainty of evidence"),
      full_forest:       has(full,  "Forest plot for the primary outcome"),
      full_optprompt:    has(full,  "optional extras this program generates"),
      short_funnel:      has(short, "Are small studies missing"),
      short_subgroup:    has(short, "Subgroup analysis"),
      short_diagnostics: has(short, "Visual diagnostics"),
      short_rob:         has(short, "Risk of bias"),
      short_grade:       has(short, "Certainty of evidence"),
      short_forest:      has(short, "Forest plot for the primary outcome"),
      short_discussion:  has(short, "Discussion"),
      few_optional_tag:  has(full,  "few studies")
    }));
    """
    r = subprocess.run(["node", "-e", snippet], capture_output=True, text=True,
                       timeout=60, check=False, cwd=str(ROOT))
    assert r.returncode == 0, f"node exited {r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert lines, f"no output.\nSTDERR:\n{r.stderr}"
    return json.loads(lines[-1])


def test_full_report_includes_optional_sections():
    o = _render_both()
    assert o["full_funnel"] is True
    assert o["full_subgroup"] is True          # NEW subgroup section
    assert o["full_diagnostics"] is True
    assert o["full_sensitivity"] is True       # leave-one-out relabelled
    assert o["full_forest"] is True
    assert o["full_optprompt"] is True         # "write about all analyses" prompt
    assert o["few_optional_tag"] is True       # k<10 -> "(optional, few studies)"


def test_short_report_omits_optional_but_keeps_rob_and_core():
    o = _render_both()
    # optional/diagnostic sections are dropped in the short paper
    assert o["short_funnel"] is False
    assert o["short_subgroup"] is False
    assert o["short_diagnostics"] is False
    # core + mandatory sections survive
    assert o["short_forest"] is True
    assert o["short_rob"] is True              # Risk of bias is NEVER gated
    assert o["short_grade"] is True            # GRADE stays (optional) in both
    assert o["short_discussion"] is True


def test_risk_of_bias_present_in_both_lengths():
    o = _render_both()
    assert o["full_rob"] is True and o["short_rob"] is True
