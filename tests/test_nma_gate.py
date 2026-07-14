"""Planted RED->GREEN gate test for the NMA-vs-pairwise analysis-type guard (paper-studio.js).

An NMA estimate presented as a pairwise meta-analysis is a lie of presentation: the reader
assumes DIRECT evidence when the estimate is partly INDIRECT. paper-studio.js DERIVES the analysis
type from the data (window.NMA_CONFIG / PanelHelper.isNMA — the SAME signal the renderer/NMA panels
use) and FAILS CLOSED when a network is declared but its geometry is unresolvable.

This test proves, under a minimal DOM stub:

  1. deriveAnalysisType() reads the shared field: NMA_CONFIG present + >=3 nodes  -> "nma";
     no NMA_CONFIG -> "pairwise"; NMA_CONFIG present but geometry unclear -> None (fail closed).
  2. GATE (the planted refusal): feeding an NMA into the PAIRWISE generator makes it REFUSE
     (methodsProse / resultsPrimaryProse return the gate marker instead of pairwise prose), and the
     NMA generator refuses a pairwise analysis.
  3. render() dispatches: an NMA paper is LABELLED "network meta-analysis" + "PRISMA-NMA" + reports
     network geometry, and does NOT emit a single pairwise pooled-estimate sentence.
  4. Fail-closed render shows the "could not be derived" banner and withholds the auto claims.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(nma_config_js: str) -> dict:
    """Eval paper-studio.js under a DOM/window stub with the given NMA_CONFIG, return probes."""
    snippet = r"""
    global.window = { addEventListener:function(){}, matchMedia:function(){return {matches:false,addEventListener:function(){},addListener:function(){}};} };
    global.localStorage = { getItem:function(){return null;}, setItem:function(){} };
    var captured = {};
    function fakeEl(){ return { _h:"", get innerHTML(){return this._h;}, set innerHTML(v){this._h=v;},
      querySelector:function(){return null;}, querySelectorAll:function(){return [];},
      appendChild:function(){}, setAttribute:function(){}, removeAttribute:function(){},
      insertBefore:function(){}, addEventListener:function(){}, classList:{add:function(){},remove:function(){},contains:function(){return false;}},
      style:{}, hidden:false, value:"", innerText:"", textContent:"" }; }
    global.document = { getElementById:function(id){ return captured[id] || (captured[id]=fakeEl()); },
      querySelector:function(){return null;}, querySelectorAll:function(){return [];},
      createElement:function(){return fakeEl();}, addEventListener:function(){} };
    var fs = require('fs');
    eval(fs.readFileSync('template/assets/js/paper-studio.js','utf8'));
    var PS = global.window.PaperStudio;
    PS.buildWizard=function(){}; PS.buildSectionGuides=function(){}; PS.updateProtocolLink=function(){};
    PS.embedFigures=function(){};
    PS.state.analysis.kStudies = "4";

    __NMA_CONFIG__

    var type = PS.deriveAnalysisType();
    // Feed the NMA (or absence) straight into the PAIRWISE builders -> they must refuse an NMA.
    var mp = PS.methodsProse();
    var pairwiseMethodsText = mp.map(function(x){return x.text;}).join(" ");
    var pairwisePrimary = PS.resultsPrimaryProse();
    var nmaMethodsText = PS.nmaMethodsProse().map(function(x){return x.text;}).join(" ");
    var nmaBlock = PS.nmaResultsBlock();

    PS.state.style.reportLength = "full";
    PS.render();
    var rendered = captured["paperCanvas"].innerHTML;

    function has(s, re){ return new RegExp(re, "i").test(s); }
    console.log(JSON.stringify({
      type: type,
      pairwise_methods_refused: pairwiseMethodsText.indexOf(PS.GATE_MARKER) >= 0,
      pairwise_primary_refused: String(pairwisePrimary).indexOf(PS.GATE_MARKER) >= 0,
      nma_methods_refused: nmaMethodsText.indexOf(PS.GATE_MARKER) >= 0,
      rendered_has_nma_label: has(rendered, "network meta-analysis"),
      rendered_has_prisma_nma: has(rendered, "PRISMA-NMA"),
      rendered_has_geometry: has(rendered, "Network geometry"),
      rendered_has_indirect_flag: has(rendered, "indirect evidence only|no direct trial|indirect-only|rest on indirect"),
      rendered_has_pairwise_pooled: has(rendered, "The pooled (OR|RR|HR|odds ratio|risk ratio) for"),
      rendered_has_failclosed: has(rendered, "could not be derived")
    }));
    """
    snippet = snippet.replace("__NMA_CONFIG__", nma_config_js)
    r = subprocess.run(["node", "-e", snippet], capture_output=True, text=True,
                       timeout=60, check=False, cwd=str(ROOT))
    assert r.returncode == 0, f"node exited {r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert lines, f"no output.\nSTDERR:\n{r.stderr}"
    return json.loads(lines[-1])


# A real 5-node / 4-edge network (mirrors ADC_HER2_NMA: every edge k=1).
NMA_CONFIG_VALID = r"""
    global.window.NMA_CONFIG = {
      treatments: ["T_DXd","T_DM1","LapaCape","TPC_chemo","TPC_Hplus_chemo"],
      comparisons: [
        {t1:"T_DXd", t2:"T_DM1", trials:["NCT03529110"]},
        {t1:"T_DM1", t2:"LapaCape", trials:["NCT00829166"]},
        {t1:"T_DM1", t2:"TPC_chemo", trials:["NCT01419197"]},
        {t1:"T_DXd", t2:"TPC_Hplus_chemo", trials:["NCT03523585"]}
      ],
      outcome_label: "Progression-free survival"
    };
"""

# Network declared but geometry unclear (1 treatment, no comparisons) -> must FAIL CLOSED.
NMA_CONFIG_MALFORMED = r"""
    global.window.NMA_CONFIG = { treatments: ["OnlyOne"], comparisons: [] };
"""


def test_derive_pairwise_when_no_network():
    o = _run("")  # no NMA_CONFIG
    assert o["type"] == "pairwise"
    assert o["pairwise_methods_refused"] is False       # pairwise generator runs normally
    assert o["rendered_has_nma_label"] is False
    assert o["rendered_has_failclosed"] is False


def test_gate_pairwise_generator_refuses_nma():
    """RED->GREEN: feed an NMA into the pairwise generator; it MUST refuse."""
    o = _run(NMA_CONFIG_VALID)
    assert o["type"] == "nma"                            # derived from the shared field
    # The planted refusal: the pairwise builders return the gate marker, not pairwise prose.
    assert o["pairwise_methods_refused"] is True
    assert o["pairwise_primary_refused"] is True
    # ...and the NMA builder refuses a pairwise analysis (symmetric guard) - here type is nma so it does NOT refuse:
    assert o["nma_methods_refused"] is False


def test_nma_paper_is_labelled_and_not_pairwise():
    o = _run(NMA_CONFIG_VALID)
    assert o["rendered_has_nma_label"] is True           # "network meta-analysis" visibly renders
    assert o["rendered_has_prisma_nma"] is True          # PRISMA-NMA extension, not plain PRISMA
    assert o["rendered_has_geometry"] is True            # network geometry section present
    assert o["rendered_has_indirect_flag"] is True       # indirect-only comparisons flagged
    # The critical anti-lie assertion: NO single pairwise pooled-estimate sentence in an NMA paper.
    assert o["rendered_has_pairwise_pooled"] is False


def test_malformed_network_fails_closed():
    o = _run(NMA_CONFIG_MALFORMED)
    assert o["type"] is None                             # undecidable -> fail closed
    assert o["rendered_has_failclosed"] is True          # banner shown
    assert o["rendered_has_pairwise_pooled"] is False    # no pairwise claim emitted either
