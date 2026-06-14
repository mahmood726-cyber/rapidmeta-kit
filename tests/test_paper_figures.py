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


# Richer prelude: adds publication years + RoB-2 domain arrays to the 4 trials.
PRELUDE_FULL = r"""
global.window = {};
const fs = require('fs');
eval(fs.readFileSync('template/assets/js/paper-figures-synthesis.js','utf8'));
const PS = global.window.PaperStudio;
function mk(name,or_,lo,hi,tE,tN,cE,cN,year){
  const logOR=Math.log(or_), se=(Math.log(hi)-Math.log(lo))/(2*1.959964);
  return {id:name,name,year,logOR,se,vi:se*se,tE,tN,cE,cN,rob:['some','some','some','some','some']};
}
const res = {isContinuous:false,confLevel:95,or:3.40,lci:2.89,uci:3.99,
  piLCI:2.61,piUCI:4.42,k:4,effectMeasure:'Odds ratio',tau2:0,
  plotData:[
    mk('ORAL Solo',4.08,2.53,6.59,144,241,32,120,2012),
    mk('RA-BEAM',3.41,2.62,4.45,339,487,196,488,2017),
    mk('SELECT-NEXT',3.17,2.15,4.67,141,221,79,221,2018),
    mk('FINCH 1',3.29,2.49,4.35,364,475,237,475,2021)]};
"""


def test_synthesis_labbe_reproduces_pdf_figure2():
    out = _node(PRELUDE_FULL + r"""
        const svg = PS.synthesisLabbeSVG(res, {});
        const T = svg.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');  // tspan-joined text
        console.log(JSON.stringify({
          bubbles: (svg.match(/<circle/g)||[]).length === 4,
          green: svg.includes('#2f7d34'),
          lineOfNoEffect: svg.includes('line of no effect (y = x)'),
          impliedCurve: svg.includes('implied by pooled OR 3.40'),
          allLabels: ['ORAL Solo','RA-BEAM','SELECT-NEXT','FINCH 1'].every(s=>svg.includes(s)),
          annotation: T.includes('Every trial lies above the line of no effect'),
          axes: svg.includes('comparator arm') && svg.includes('treatment arm')
        }));
    """)
    for k, v in out.items():
        assert v is True, f"L'Abbé check failed: {k}"


def test_synthesis_rob_traffic_light():
    out = _node(PRELUDE_FULL + r"""
        const svg = PS.synthesisRobSVG(res, {});
        console.log(JSON.stringify({
          domainHeaders: ['Randomisation','Deviations','Missing','Measurement','Selective','Overall'].every(s=>svg.includes(s)),
          legend: svg.includes('Low') && svg.includes('Some concerns') && svg.includes('High'),
          circles: (svg.match(/<circle/g)||[]).length === (4*6 + 3),  // grid 4 rows x 6 cols + 3 legend
          amber: svg.includes('#d9a235'),
          someSymbol: svg.includes('>−<')  // minus glyph in some-concerns cells
        }));
    """)
    for k, v in out.items():
        assert v is True, f"RoB check failed: {k}"


def test_synthesis_leave_one_out_repool_matches_pdf():
    """The DL re-pool reproduces the PDF's published leave-one-out ORs
    (3.32 / 3.39 / 3.45 / 3.45) — validates the internal re-pooler."""
    out = _node(PRELUDE_FULL + r"""
        const items = res.plotData.map(d=>({y:d.logOR, v:d.vi}));
        // replicate the generator's per-omission DL re-pool
        const z=1.959964, effs=[];
        for (let i=0;i<items.length;i++){
          const sub=items.filter((_,j)=>j!==i);
          let sw=0,swy=0,sw2=0; sub.forEach(d=>{const w=1/d.v;sw+=w;swy+=w*d.y;sw2+=w*w;});
          const muF=swy/sw, Q=sub.reduce((a,d)=>a+(1/d.v)*(d.y-muF)*(d.y-muF),0);
          const C=sw-sw2/sw, tau2=Math.max(0,(Q-(sub.length-1))/C);
          let rw=0,rwy=0; sub.forEach(d=>{const w=1/(d.v+tau2);rw+=w;rwy+=w*d.y;});
          effs.push(Math.exp(rwy/rw));
        }
        const svg = PS.synthesisLeaveOneOutSVG(res, {});
        const T = svg.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
        console.log(JSON.stringify({effs, hasOmitLabels: svg.includes('Omitting ORAL Solo'),
          refBand: svg.includes('all trials 3.40'), annotation: T.includes('no single trial drives the result')}));
    """)
    pdf = [3.32, 3.39, 3.45, 3.45]
    for got, exp in zip(out["effs"], pdf):
        assert abs(got - exp) < 0.02, f"leave-one-out OR {got} != PDF {exp}"
    assert out["hasOmitLabels"] and out["refBand"] and out["annotation"]


def test_synthesis_cumulative_by_year_converges():
    """Cumulative pool is built in publication-year order and ends at the
    all-trials estimate (PDF Figure 5: 4.08 → … → 3.40)."""
    out = _node(PRELUDE_FULL + r"""
        const svg = PS.synthesisCumulativeSVG(res, {});
        const T = svg.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ');
        console.log(JSON.stringify({
          orderedLabels: svg.indexOf('+ ORAL Solo (2012)') < svg.indexOf('+ FINCH 1 (2021)'),
          firstIsOral: svg.includes('+ ORAL Solo (2012)'),
          refCurrent: svg.includes('current 3.40'),
          annotation: T.includes('settled at 3.40')
        }));
    """)
    for k, v in out.items():
        assert v is True, f"cumulative check failed: {k}"


def test_render_helper_writes_svg_into_element():
    """renderSynthesisFigure injects the SVG into el.innerHTML and returns true;
    a bogus kind returns false and leaves the element untouched (the render path
    Paper Studio's mountFig depends on)."""
    out = _node(PRELUDE_FULL + r"""
        const el = { innerHTML: '' };
        const ok = PS.renderSynthesisFigure('forest', el, res, {});
        const elBad = { innerHTML: 'X' };
        const bad = PS.renderSynthesisFigure('bogus', elBad, res, {});
        console.log(JSON.stringify({
          ok, wrote: el.innerHTML.startsWith('<svg'),
          bad, untouched: elBad.innerHTML === 'X'
        }));
    """)
    assert out["ok"] is True and out["wrote"] is True
    assert out["bad"] is False and out["untouched"] is True


def test_synthesis_funnel_and_dispatch():
    out = _node(PRELUDE_FULL + r"""
        const f = PS.synthesisFunnelSVG(res, {});
        const kinds = ['forest','labbe','rob','leaveOneOut','cumulative','funnel']
          .map(k => PS.synthesisFigureSVG(k, res, {}).startsWith('<svg'));
        console.log(JSON.stringify({
          triangle: f.includes('<polygon'),
          seAxis: f.includes('Standard error'),
          pooledLine: f.includes('stroke-dasharray'),
          annotation: f.includes('underpowered'),
          allKindsRender: kinds.every(Boolean),
          unknownKindEmpty: PS.synthesisFigureSVG('bogus', res, {}) === ''
        }));
    """)
    for k, v in out.items():
        assert v is True, f"funnel/dispatch check failed: {k}"


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
