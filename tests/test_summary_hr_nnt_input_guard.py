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

 // Explicitly malformed effect-type labels must not be treated as absent.
const malformedTypes = [null, false, 0, [], {}, '', ' '];
for (const [index, badType] of malformedTypes.entries()) {
  const bad = {...goodA,estimandType:badType};
  assert.equal(S.fit([bad,goodB]),null,'invalid explicit type '+index);
  assert.equal(S.fit([goodB,bad]),null,'late invalid explicit type '+index);
}
assert.equal(S.fit([{...goodA,estimandType:' hR '},goodB]).k,2,
             'valid padded HR type positive control');


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

// Cochrane Handbook Chapter 4: several reports of one registered trial
// are one study, not independent inverse-variance observations.
const trialIdA = {...goodA, nct:'NCT00000421'};
const trialIdDuplicate = {...goodB, nct_id:' nct00000421 '};
const trialIdDistinct = {...goodB, nctId:'NCT00000422'};
const maskedDuplicate = {...trialIdDuplicate, nct:'NCT00000423'};
assert.equal(S.fit([trialIdA,trialIdDuplicate]),null,
             'same study across NCT aliases cannot be counted twice');
assert.equal(S.fit([trialIdDuplicate,trialIdA]),null,'order cannot conceal reuse');
assert.equal(S.fit([trialIdA,maskedDuplicate]),null,
             'unrelated first alias must not hide a repeated identifier');
assert.equal(S.fit([trialIdA,trialIdDistinct]).k,2,'distinct NCT positive');
assert.equal(S.fit([{...trialIdA,studyId:' nct00000421 '},trialIdDistinct]).k,2,
             'several aliases within one record are permitted');

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
// Identical source facts in paired aliases are permitted; contradictory
// effect and comparator aliases must not silently select the primary value.
// Cochrane Handbook Ch 6: source effect and arm denominators must be coherent.
P.getRealData=()=>({a:{...goodA,publishedHR:'0.750',hrLCI:'0.60',
                        hrUCI:'0.920',cE:'20',cN:'100'},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true,'equivalent aliases accepted');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/,'equivalent alias positive');
for (const [label, changed] of [
  ['conflicting point HR', {publishedHR:1.60}],
  ['conflicting HR lower limit', {hrLCI:0.30}],
  ['conflicting HR upper limit', {hrUCI:1.40}],
  ['conflicting comparator events', {cE:50}],
  ['conflicting comparator denominator', {cN:80}],
  ['invalid HR secondary alias', {publishedHR:true}],
  ['invalid count secondary alias', {cE:'bad'}]
]) {
  for (const data of [
    {a:{...goodA,...changed},b:goodB},
    {a:goodA,b:{...goodB,...changed}}
  ]) {
    P.getRealData=()=>data;
    assert.equal(panel.HRNNTPanel.render(),true,label);
    assert.match(cfg.summary,/^Refused:/,label);
    assert.match(cfg.bodyHtml,/Conflicting or malformed duplicated summary-HR/,label);
    assert.match(cfg.bodyHtml,/role="alert"/,label);
    assert.doesNotMatch(cfg.summary,/NNTB|NNTH|k=/,label);
  }
}
P.getRealData=()=>({a:goodA,b:goodB});
P.getRealData=()=>({a:{...goodA,HR:true,publishedHR:0.75},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/^Refused:/,'malformed primary must not use fallback');
P.getRealData=()=>({a:{...goodA,HR:undefined,publishedHR:0.75},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/^Refused:/,'missing explicit primary must not use fallback');
// Cochrane Ch 6: a declared RR/OR and a reported HR are distinct measures.
const rrOnly={name:'RR-only outcome',estimandType:'RR',RR:0.76};
const orOnly={name:'OR-only outcome',estimandType:'OR',OR:0.87};
P.getRealData=()=>({a:rrOnly,b:orOnly});
assert.equal(panel.HRNNTPanel.render(),false,'RR/OR-only pack cannot produce an HR NNT');
for (const [label,bad] of [
  ['RR type conflicts with explicit HR', {...goodA,estimandType:'RR'}],
  ['OR type conflicts with explicit HR', {...goodB,estimandType:'OR'}],
  ['RR type conflicts with HR alias', {
    name:'HR alias conflict',estimandType:'RR',
    publishedHR:0.75,hrLCI:0.60,hrUCI:0.92
  }]
]) {
  for (const payload of [
    {a:bad,b:goodA,c:goodB},
    {a:goodA,b:goodB,c:bad}
  ]) {
    P.getRealData=()=>payload;
    assert.equal(panel.HRNNTPanel.render(),true,label);
    assert.match(cfg.summary,/^Refused:/,label);
    assert.match(cfg.bodyHtml,/Conflicting non-HR estimand type/,label);
    assert.match(cfg.bodyHtml,/role="alert"/,label);
    assert.doesNotMatch(cfg.summary,/NNTB|NNTH|k=/,label);
  }
}
P.getRealData=()=>({a:goodA,b:goodB,c:rrOnly});
assert.equal(panel.HRNNTPanel.render(),true,
             'unambiguous separate RR-only outcome may be excluded');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/);

for (const [index, badType] of malformedTypes.entries()) {
  for (const data of [
    {a:{...goodA,estimandType:badType},b:goodB},
    {a:goodA,b:{...goodB,estimandType:badType}}
  ]) {
    P.getRealData=()=>data;
    assert.equal(panel.HRNNTPanel.render(),true,'malformed typed panel '+index);
    assert.match(cfg.summary,/^Refused:/,'malformed typed panel '+index);
    assert.match(cfg.bodyHtml,/role="alert"/,'visible type refusal '+index);
    assert.doesNotMatch(cfg.summary,/NNTB|NNTH|k=/,'no NNT on bad type '+index);
  }
}
P.getRealData=()=>({a:{...goodA,estimandType:' hR '},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true,'valid typed panel positive control');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/);

P.getRealData=()=>({a:{...goodA,HR:'7.5e-1',HR_ci_lo:'6e-1',HR_ci_hi:'9.2e-1'},
                    b:{...goodB,HR:'0.80',HR_ci_lo:'0.65',HR_ci_hi:'0.99'}});
assert.equal(panel.HRNNTPanel.render(),true);
assert.match(cfg.summary,/k=2/);
assert.doesNotMatch(cfg.summary,/^Refused:/);
// BMJ 1999 Altman-Andersen: time-to-event NNT requires baseline risk at a
// defined time; invented 10% baseline or impossible source counts must refuse.
const invalidBaselines = [
  ['all comparator counts absent', {...goodA,events_ctl:undefined,n_ctl:undefined},
    {...goodB,events_ctl:undefined,n_ctl:undefined}],
  ['one comparator count missing', goodA, {...goodB,n_ctl:undefined}],
  ['late invalid comparator events', goodA, {...goodB,events_ctl:-3}],
  ['events exceed arm size', {...goodA,events_ctl:200},goodB],
  ['fractional comparator events', {...goodA,events_ctl:1.5},goodB],
  ['fractional denominator', {...goodA,n_ctl:99.5},goodB],
  ['zero comparator size', {...goodA,n_ctl:0},goodB],
  ['boolean comparator size', {...goodA,n_ctl:true},goodB],
  ['hex comparator total', {...goodA,n_ctl:'0x64'},goodB],
  ['overflow comparator size', {...goodA,n_ctl:1e20},goodB],
  ['malformed primary baseline alias', {...goodA,events_ctl:'',cE:20},goodB],
  ['zero risk in all trials', {...goodA,events_ctl:0},{...goodB,events_ctl:0}],
  ['unit risk in all trials', {...goodA,events_ctl:100},{...goodB,events_ctl:100}]
];
for (const [label,a,b] of invalidBaselines) {
  P.getRealData=()=>({a,b});
  assert.ok(S.fit([a,b]) && S.fit([a,b]).k===2,
            label+' should not modify valid HR fit');
  assert.equal(panel.HRNNTPanel.render(),true,label);
  assert.match(cfg.summary,/^Refused:/,label);
  assert.match(cfg.bodyHtml,/role="alert"/,label);
  assert.doesNotMatch(cfg.summary,/NNTB|NNTH|k=/,label);
}
P.getRealData=()=>({a:{...goodA,events_ctl:'2e1',n_ctl:'1e2'},b:goodB});
assert.equal(panel.HRNNTPanel.render(),true,'integer scientific count control');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/);
assert.match(cfg.bodyHtml,/role="note"/);
assert.match(cfg.bodyHtml,/fixed follow-up time/);
P.getRealData=()=>({a:goodA,b:goodB});
assert.equal(panel.HRNNTPanel.render(),true,'valid comparator counts');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/);

// The panel must preserve source IDs rather than pooling duplicate reports.
P.getRealData=()=>({a:trialIdA,b:trialIdDuplicate});
assert.equal(panel.HRNNTPanel.render(),true,'duplicate NCT panel refusal');
assert.match(cfg.summary,/^Refused:/,'duplicate NCT visible refusal');
assert.match(cfg.bodyHtml,/role="alert"/,'no displayed NNT from duplicated study');
P.getRealData=()=>({a:trialIdA,b:maskedDuplicate});
assert.equal(panel.HRNNTPanel.render(),true,'checks all source ID aliases');
assert.match(cfg.summary,/^Refused:/,'masked duplicate visibly refused');
P.getRealData=()=>({a:trialIdA,b:trialIdDistinct});
assert.equal(panel.HRNNTPanel.render(),true,'two distinct NCT studies permitted');
assert.match(cfg.summary,/Exploratory NNTB.*k=2/,'distinct-study positive');

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
