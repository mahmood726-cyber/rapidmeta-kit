"""Synthetic Kaplan-Meier step-integral regression against shipped JavaScript.

This tests right-continuous curve arithmetic, not censoring-aware variance
or original clinical source records. Method: survRM2 package RMST vignette.
"""
from pathlib import Path
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
COPIES=("assets","docs/assets","template/assets")
NODE=r"""
const assert=require('node:assert/strict');
const copy=process.argv[1];
const S=require('./'+copy+'/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const data=[
 {name:'Synthetic A',rmst_diff_se:0.3,km_curve:[
  {t_months:0,surv_trt:1,surv_ctl:1},
  {t_months:3,surv_trt:0.8,surv_ctl:0.6},
  {t_months:6,surv_trt:0.7,surv_ctl:0.5}]},
 {name:'Synthetic B',rmst_diff_se:0.4,km_curve:[
  {t_months:0,surv_trt:1,surv_ctl:1},
  {t_months:3,surv_trt:0.9,surv_ctl:0.7},
  {t_months:6,surv_trt:0.8,surv_ctl:0.6}]}
];
function near(a,b,label){assert.ok(Number.isFinite(a)&&Math.abs(a-b)<1e-11,label+': '+a+' vs '+b)}
const p=S.poolRMSTDiff(data,6);
assert.equal(p.k,2);
assert.equal(p.error,undefined);
for(let i=0;i<2;i++){
 const row=p.per_study[i];
 near(row.rmst_trt,[5.4,5.7][i],'treatment area');
 near(row.rmst_ctl,[4.8,5.1][i],'control area');
 near(row.rmst_diff,0.6,'study difference');
 assert.ok(Math.abs(row.rmst_diff-0.9)>0.25,'former trapezoid result must fail');
}
near(p.pooled_diff,0.6,'pooled step difference');
const q=S.poolRMSTDiff(data,4);
assert.equal(q.k,2);
for(let i=0;i<2;i++){
 near(q.per_study[i].rmst_trt,[3.8,3.9][i],'intermediate treatment tau');
 near(q.per_study[i].rmst_ctl,[3.6,3.7][i],'intermediate control tau');
 near(q.per_study[i].rmst_diff,0.2,'intermediate difference');
}
const boundary=S.poolRMSTDiff([
 {name:'Synthetic boundary',rmst_diff_se:0.3,km_curve:[
  {t_months:0,surv_trt:1,surv_ctl:1},
  {t_months:3,surv_trt:0.8,surv_ctl:0.6},
  {t_months:6,surv_trt:0.1,surv_ctl:0.1}]}
],6);
assert.equal(boundary.k,1);
near(boundary.per_study[0].rmst_diff,0.6,'event at horizon');
console.log('KM STEP ARITHMETIC PASS '+copy);
"""

@pytest.mark.parametrize("copy",COPIES)
def test_km_step_area_not_trapezoid(copy):
    cp=subprocess.run(["node","-e",NODE,copy],cwd=ROOT,text=True,
                      capture_output=True,timeout=30,check=False)
    assert cp.returncode==0,cp.stdout+"\n"+cp.stderr
    assert "KM STEP ARITHMETIC PASS" in cp.stdout
