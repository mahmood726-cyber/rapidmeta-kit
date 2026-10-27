"""Summary-HR and HR-to-NNT must fail closed on malformed effect sources.

Synthetic JS input-safety regressions only. No original clinical data and NO
claim of method-matched R/metafor numerical parity for summary HR or NNT.
Issue #65; Cochrane Handbook Chapter 6 on effect-type/estimand selection.
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "template/assets", "docs/assets")
SCRIPT = r"""
const assert = require('node:assert/strict');
const copy = process.argv[1];
const S = require('./' + copy + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const goodA = {name:'Trial A', HR:0.75, HR_ci_lo:0.60, HR_ci_hi:0.92,
               events_ctl:20, n_ctl:100};
const goodB = {name:'Trial B', HR:0.80, HR_ci_lo:0.65, HR_ci_hi:0.99,
               events_ctl:18, n_ctl:100};
const good = S.fit([goodA,goodB]);
assert.ok(good && good.k===2 && good.pooled_HR>0 && good.pooled_HR<1);
assert.equal(good.method,'REML+HKSJ');
assert.equal(S.fit([goodA]).method,'FE');
assert.equal(S.fit([{...goodA,estimandType:'RR'},goodB]),null,
             'a direct fit must reject an explicit RR record');
assert.equal(S.fit([goodA,{...goodB,estimandType:'OR'}]),null,
             'a late OR record must not be counted as an HR');

const invalid = [
  ['boolean HR', {...goodA,HR:true}],
  ['array HR', {...goodA,HR:[0.75]}],
  ['hex HR', {...goodA,HR:'0x1'}],
  ['binary HR', {...goodA,HR:'0b1'}],
  ['octal CI', {...goodA,HR_ci_hi:'0o2'}],
  ['blank HR', {...goodA,HR:''}],
  ['null HR', {...goodA,HR:null}],
  ['point outside CI', {...goodA,HR:2}],
  ['point below CI', {...goodA,HR:0.4}],
  ['reversed CI', {...goodA,HR_ci_lo:1.2,HR_ci_hi:0.8}],
  ['missing CI', {...goodA,HR_ci_hi:undefined}],
  ['invalid HR', {...goodA,HR:-1}],
  ['nonnumeric CI', {...goodA,HR_ci_lo:'invalid'}],
  ['nonfinite HR', {...goodA,HR:Infinity}],
  ['boolean CI', {...goodA,HR_ci_lo:true}],
  ['zero width CI', {...goodA,HR_ci_hi:goodA.HR_ci_lo}]
];
for (const [label,bad] of invalid) {
  assert.equal(S.fit([bad,goodB]),null,label);
  assert.equal(S.fit([goodB,bad]),null,label+' late invalid input');
}
assert.equal(S.fit([goodA,{...goodB,HR:-1},goodA]),null,
             'must not silently drop one invalid study and show k=2');
for (const key of ['HR','HR_ci_lo','HR_ci_hi']) {
  const scientific = [{...goodA,[key]:String(goodA[key])}, {...goodB}];
  assert.equal(S.fit(scientific).k,2,key+' decimal positive control');
}
const textControl = S.fit([
  {HR:'7.5e-1',HR_ci_lo:'6e-1',HR_ci_hi:'9.2e-1'},
  {HR:'0.80',HR_ci_lo:'0.65',HR_ci_hi:'0.99'}
]);
assert.equal(textControl.k,2,'scientific notation accepted');
assert.ok(Math.abs(textControl.pooled_HR-good.pooled_HR)<1e-12);

const panel = require('./' + copy + '/vendor/hr-nnt-panel.js');
let cfg;
const P = {
  getRealData() { return {a:goodA,b:goodB}; },
  fmt(v,n) { return Number(v).toFixed(n); },
  buildCollapsiblePanel(x) { cfg=x; return {}; },
  insertAfterRBadge() {}
};
panel.PanelHelper=P;
panel.RapidMetaSurvival=S;
// require before introducing document; prevents unsolicited bootstrap timers.
global.document={getElementById(){return null;}};
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/NNTB.*k=2/);
assert.doesNotMatch(cfg.bodyHtml,/role="alert"/);
for (const [label,bad] of invalid) {
  P.getRealData=()=>({a:goodA,b:goodB,c:bad});
  assert.equal(panel.HRNNTPanel.render(),true,label);
  assert.match(cfg.summary,/^Refused:/,label);
  assert.match(cfg.bodyHtml,/role="alert"/,label);
  assert.doesNotMatch(cfg.bodyHtml,/<div[^>]*>Pooled HR<\/div>/,label);
  assert.doesNotMatch(cfg.summary,/NNTB|NNTH|k=/,label);
}
P.getRealData=()=>({a:{...goodA,HR:true,publishedHR:0.75},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/^Refused:/,'malformed primary must not use fallback');
P.getRealData=()=>({a:{...goodA,HR:undefined,publishedHR:0.75},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/^Refused:/,'missing explicit primary must not use fallback');
P.getRealData=()=>({a:{...goodA,estimandType:'RR'},b:{...goodB,estimandType:'OR'}});
assert.equal(panel.HRNNTPanel.render(),false,'RR/OR-only pack cannot produce an HR NNT');
P.getRealData=()=>({a:{...goodA,HR:'7.5e-1',HR_ci_lo:'6e-1',HR_ci_hi:'9.2e-1'},
                    b:{...goodB,HR:'0.80',HR_ci_lo:'0.65',HR_ci_hi:'0.99'}});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/k=2/);
assert.doesNotMatch(cfg.summary,/^Refused:/);
console.log('PASS: synthetic summary-HR and HR-NNT source/refusal guards');
"""


@pytest.mark.parametrize("copy", COPIES)
def test_summary_hr_and_nnt_fail_closed(copy):
    proc = subprocess.run(
        ["node", "-e", SCRIPT, copy],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False
    )
    assert proc.returncode == 0, (
        f"{copy}: node exit {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "PASS: synthetic summary-HR and HR-NNT source/refusal guards" in proc.stdout
