"""Tests for the Synthēsis-styled Paper Studio figures (paper-figures-synthesis.js).

The SVG generator is pure string-building (no DOM), so it runs in node with a
`window` stub. We reproduce Figure 1 of the Synthēsis metapaper PDF (JAK
inhibitors / ACR20, 4 trials) and assert the journal-style elements are present
and the numbers are right: weight-proportional squares (inverse-variance
weights 11/37/17/34%), the maroon pooled diamond + value, the red 95%
prediction-interval bracket, the log x-axis, and the default annotation callout.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "template" / "assets" / "js" / "paper-figures-synthesis.js"


def _node(snippet):
    result = subprocess.run(
        ["node", "-e", snippet],
        capture_output=True, text=True, timeout=60, check=False, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"node exited {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert lines, f"node printed nothing.\nSTDERR:\n{result.stderr}"
    return json.loads(lines[-1])


# Shared node prelude: stub window, eval the module, build the PDF's Figure-1 data.
PRELUDE = r"""
global.window = {};
const fs = require('fs');
eval(fs.readFileSync('template/assets/js/paper-figures-synthesis.js','utf8'));
const PS = global.window.PaperStudio;
function mk(name,or_,lo,hi,tE,tN,cE,cN){
  const logOR=Math.log(or_), se=(Math.log(hi)-Math.log(lo))/(2*1.959964);
  return {id:name,name,logOR,se,vi:se*se,tE,tN,cE,cN};
}
const res = {isContinuous:false,confLevel:95,or:3.40,lci:2.89,uci:3.99,
  piLCI:2.61,piUCI:4.42,k:4,effectMeasure:'Odds ratio',tau2:0,
  plotData:[
    mk('ORAL Solo',4.08,2.53,6.59,144,241,32,120),
    mk('RA-BEAM',3.41,2.62,4.45,339,487,196,488),
    mk('SELECT-NEXT',3.17,2.15,4.67,141,221,79,221),
    mk('FINCH 1',3.29,2.49,4.35,364,475,237,475)]};
"""


def test_synthesis_forest_reproduces_pdf_figure1():
    out = _node(PRELUDE + r"""
        const svg = PS.synthesisForestSVG(res, {label:'ACR20 response'});
        console.log(JSON.stringify({
          studyLabels: ['ORAL Solo','RA-BEAM','SELECT-NEXT','FINCH 1'].every(s => svg.includes(s)),
          counts: svg.includes('144/241 vs 32/120') && svg.includes('339/487 vs 196/488'),
          weights: svg.includes('>11%') && svg.includes('>37%') && svg.includes('>17%') && svg.includes('>34%'),
          maroonDiamond: svg.includes('<polygon') && svg.includes('#9c2b27'),
          greenSquares: (svg.match(/#2f7d34/g)||[]).length >= 4,
          pooledValue: svg.includes('3.40 (2.89'),
          piBracket: svg.includes('95% prediction interval 2.61'),
          logAxis: svg.includes('Odds ratio (log scale)'),
          nullLine: svg.includes('stroke-dasharray'),
          isSvg: svg.startsWith('<svg') && svg.trim().endsWith('</svg>')
        }));
    """)
    for k, v in out.items():
        assert v is True, f"forest SVG check failed: {k}"


def test_default_annotation_voice_and_toggle():
    out = _node(PRELUDE + r"""
        const ann = PS.defaultForestAnnotation(res);
        const withAnn = PS.synthesisForestSVG(res, {});
        const noAnn = PS.synthesisForestSVG(res, {annotation:false});
        const custom = PS.synthesisForestSVG(res, {annotation:'My own caption here'});
        console.log(JSON.stringify({
          annText: ann,
          mentionsPooled: ann.includes('Pooled odds ratio 3.40'),
          mentionsAllTrials: ann.includes('all 4 trials point the same way'),
          excludesNull: ann.includes('excludes no effect'),
          defaultHasArrow: withAnn.includes('marker-end'),
          falseHidesArrow: !noAnn.includes('marker-end'),
          customApplied: custom.includes('My own caption here')
        }));
    """)
    assert out["mentionsPooled"] is True
    assert out["mentionsAllTrials"] is True
    assert out["excludesNull"] is True
    assert out["defaultHasArrow"] is True
    assert out["falseHidesArrow"] is True      # annotation:false removes the callout
    assert out["customApplied"] is True        # writer can override the text


def test_continuous_measure_uses_linear_axis_null_zero():
    """Mean-difference outcomes get a linear axis with the no-effect line at 0."""
    out = _node(r"""
        global.window = {};
        const fs = require('fs');
        eval(fs.readFileSync('template/assets/js/paper-figures-synthesis.js','utf8'));
        const PS = global.window.PaperStudio;
        const res = {isContinuous:true,confLevel:95,or:-0.45,lci:-0.70,uci:-0.20,k:3,
          effectMeasure:'Mean difference',tau2:0,
          plotData:[{id:'T1',name:'T1',md:-0.5,se:0.15,vi:0.0225},
                    {id:'T2',name:'T2',md:-0.4,se:0.12,vi:0.0144},
                    {id:'T3',name:'T3',md:-0.45,se:0.18,vi:0.0324}]};
        const svg = PS.synthesisForestSVG(res, {});
        console.log(JSON.stringify({
          linearLabel: svg.includes('Mean difference') && !svg.includes('log scale'),
          hasDiamond: svg.includes('<polygon'),
          rendered: svg.startsWith('<svg')
        }));
    """)
    assert out["linearLabel"] is True
    assert out["hasDiamond"] is True
    assert out["rendered"] is True
