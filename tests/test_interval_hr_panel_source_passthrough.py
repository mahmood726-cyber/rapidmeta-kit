"""Synthetic source-integrity checks for interval-HR panel, not native R parity."""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "template/assets", "docs/assets")
NODE = r"""
const assert=require('node:assert/strict');
const copy=process.argv[1];
const S=require('./'+copy+'/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const panel=require('./'+copy+'/vendor/interval-hr-pool.js');
let data,config;
panel.PanelHelper={getRealData(){return data;},fmt(x,n){return Number(x).toFixed(n);},
 buildCollapsiblePanel(c){config=c;return{};},insertAfterRBadge(){}};
panel.RapidMetaSurvival=S;
global.document={getElementById(){return null;}};
const iv=h=>({t0:0,t1:6,HR:h,HR_ci_lo:0.6,HR_ci_hi:1.05});
const source={a:{nct:'NCT00000001',intervals:[iv(.75)]},
 b:{nct:'NCT00000002',intervals:[iv(.8)]},
 c:{nct:'NCT00000003',intervals:[iv(.72)]}};
function render(s){data=s;config=null;assert.equal(panel.IntervalHRPoolPanel.render(),true);
 assert.ok(config);return config;}
function refuse(s,label,reason){
 const c=render(s);
 assert.match(c.summary,/^Refused:/,label);
 assert.match(c.bodyHtml,/role="alert"/,label);
 assert.match(c.bodyHtml,/Interval-HR pooling refused/,label);
 if(reason)assert.match(c.bodyHtml,reason,label);
 assert.doesNotMatch(c.bodyHtml,/<th[^>]*>Pooled HR<\/th>/,label);
}
assert.match(render(source).summary,/^Interval HRs across 1 windows/);
for(const [label,value] of [['null',null],['false',false],['zero',0],['empty','']]){
 refuse({...source,d:{nct:'NCT00000004',intervals:value}},label,/Malformed interval-HR/);
}
for(const type of ['RR','OR',null,false]){
 refuse({...source,b:{...source.b,estimandType:type}},String(type),/Non-HR estimand/);
}
for(const value of [null,false,0,'not-an-interval']){
 refuse({...source,d:{nct:'NCT00000004',intervals:[value]}},
        'malformed interval row',/Malformed interval-HR/);
}
for(const extra of [{name:'Unrelated row'}, {name:'Empty legacy list',intervals:[]}]){
 assert.match(render({...source,d:extra}).summary,/^Interval HRs across 1 windows/);
}
// Fixed synthetic identity of the degenerate sole interval; NOT clinical input.
const soleInvalid={single:{nct:'NCT00000005',intervals:[{...iv(.75),t0:0,t1:0}]}};
assert.equal(require('node:crypto').createHash('sha256')
  .update(JSON.stringify(soleInvalid),'utf8').digest('hex'),
  '8d4b71c5be58e5376fa865c9497a35ebb6bc301ee96b25b94f79924c492dbb30',
  'degenerate source fixture SHA-256');
// A declared but malformed one-window source must not disappear merely
// because breakpoint collection produces fewer than two distinct values.
// Cochrane Handbook Ch 10: source follow-up definitions must be coherent.
assert.match(render({single:{nct:'NCT00000005',intervals:[iv(.75)]}}).summary,
             /^Interval HRs across 1 windows/, 'valid single source window');
for (const [label,t0,t1] of [
  ['zero-width window',0,0],
  ['explicit null windows',null,null],
  ['nonnumeric duplicate windows','not-a-time','not-a-time']
]) {
  refuse({single:{nct:'NCT00000005',intervals:[{...iv(.75),t0,t1}]}},
         label,/time boundar|invalid.*window/i);
}
console.log('interval-HR panel source-refusal tests PASS');
"""
@pytest.mark.parametrize("copy", COPIES)
def test_interval_hr_panel_does_not_drop_or_retype_source(copy):
    p=subprocess.run(["node","-e",NODE,copy],cwd=ROOT,
                     capture_output=True,text=True,timeout=30,check=False)
    assert p.returncode==0,p.stdout+"\n"+p.stderr
    assert "interval-HR panel source-refusal tests PASS" in p.stdout
