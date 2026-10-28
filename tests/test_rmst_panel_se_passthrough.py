"""Source-executed RMST panel/engine SE wiring, positive and negative controls.

The panel must carry the reported source RMST difference SE into the engine.
This is synthetic JavaScript source-integrity coverage, NOT native-R RMST
parity or independently checked clinical survival data. The engine uses
experimental trapezoid integration of supplied survival curves.
RMST methods: https://doi.org/10.1177/17407745241254995
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "docs/assets", "template/assets")

NODE = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const copy = process.argv[1];
const S = require('./' + copy + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const curve = (a,b,c,d) => [
  {t_months:0,surv_trt:1,surv_ctl:1},
  {t_months:3,surv_trt:a,surv_ctl:b},
  {t_months:6,surv_trt:c,surv_ctl:d}
];
const rd = {
  syntheticA:{name:'Synthetic A',km_curve:curve(.8,.6,.7,.5),rmst_diff_se:.3},
  syntheticB:{name:'Synthetic B',km_curve:curve(.9,.7,.8,.6),rmst_diff_se:.4}
};
let built;
const P = {
  getRealData:()=>rd,
  fmt:(v,n)=>Number.isFinite(v) ? v.toFixed(n) : 'UNAVAILABLE',
  buildCollapsiblePanel:(opts)=>{built=opts;return {replaceWith(){}};},
  insertAfterRBadge:()=>{}
};
const ctx = {
  RapidMetaSurvival:S, PanelHelper:P,
  document:{
    readyState:'loading',
    addEventListener:()=>{},
    getElementById:()=>null
  },
  console, setTimeout:()=>{}
};
ctx.window=ctx;
vm.runInNewContext(fs.readFileSync(copy+'/vendor/rmst-pool.js','utf8'),ctx,
                   {filename:copy+'/vendor/rmst-pool.js'});
assert.equal(ctx.RMSTPanel.render(),true,'panel should render supplied KM sources');
assert.match(built.summary,/k=2/,'source SE must reach true numerical engine');
assert.match(built.bodyHtml,/Pooled RMST difference/);
assert.match(built.bodyHtml,/source-based RMST-difference standard errors/);
assert.match(built.bodyHtml,/HKSJ/);
assert.doesNotMatch(built.summary,/UNAVAILABLE/);
assert.doesNotMatch(built.bodyHtml,/Greenwood-style finite-difference/);

// Later study's invalid reported uncertainty refuses the WHOLE calculation,
// rather than displaying an apparently valid one-study pooled estimate.
rd.syntheticB.rmst_diff_se=null;
assert.equal(ctx.RMSTPanel.render(),true,'refusal stays visible');
assert.match(built.summary,/RMST unavailable/);
assert.match(built.bodyHtml,/Missing or invalid reported RMST difference standard error/);
assert.doesNotMatch(built.bodyHtml,/Pooled RMST difference:/);
assert.doesNotMatch(built.summary,/k=1|k=2|UNAVAILABLE/);

// Missing source SE is also not a source-less set of zero trials.
delete rd.syntheticB.rmst_diff_se;
assert.equal(ctx.RMSTPanel.render(),true);
assert.match(built.bodyHtml,/RMST unavailable: Missing or invalid reported/);
assert.doesNotMatch(built.bodyHtml,/No trials supplied/);
console.log('RMST PANEL SOURCE SE WIRING PASS '+copy);
"""

@pytest.mark.parametrize("copy", COPIES)
def test_rmst_panel_preserves_reported_se_and_explains_refusal(copy):
    proc = subprocess.run(
        ["node", "-e", NODE, copy],
        cwd=ROOT, text=True, capture_output=True, timeout=30, check=False
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "RMST PANEL SOURCE SE WIRING PASS" in proc.stdout
