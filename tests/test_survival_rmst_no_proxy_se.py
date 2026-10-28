"""Synthetic, source-executed RMST uncertainty integrity regressions.

An RMST difference's standard error cannot be inferred by inventing n_eff=200
from survival curves. This is NOT original-study RMST verification and does
NOT provide independent R/metafor parity for RMST or censoring-adjusted SE.
Relevant methods: Wei et al. Statistics in Medicine 2015, doi:10.1002/sim.6556;
Lueza et al. BMC Medical Research Methodology 2016, doi:10.1186/s12874-016-0137-z.
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "docs/assets", "template/assets")

JS = r"""
const assert = require('node:assert/strict');
const copy = process.argv[1];
const S = require('./' + copy + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const records = [
  {name:'Synthetic A',km_curve:[
    {t_months:0,surv_trt:1,surv_ctl:1},
    {t_months:3,surv_trt:.8,surv_ctl:.6},
    {t_months:6,surv_trt:.7,surv_ctl:.5}]},
  {name:'Synthetic B',km_curve:[
    {t_months:0,surv_trt:1,surv_ctl:1},
    {t_months:3,surv_trt:.9,surv_ctl:.7},
    {t_months:6,surv_trt:.8,surv_ctl:.6}]}
];
function refusal(input, label) {
  const result = S.poolRMSTDiff(input,6);
  assert.equal(result.k,0,label + ': no partial k');
  assert.equal(result.per_study.length,0,label + ': no partial evidence');
  assert.match(result.error,/RMST difference standard error/,label);
  assert.equal(result.ci_lo,undefined,label + ': no invented lower CI');
  assert.equal(result.ci_hi,undefined,label + ': no invented upper CI');
}
refusal(records,'both SEs absent');
refusal([{...records[0],rmst_diff_se:.3},records[1]],'late missing SE');
refusal([{...records[0],n_eff:200,tN:100,cN:100},records[1]],
        'unsourced default n_eff must not become precision');
for (const bad of [null,0,-.1,true,[],{},'0x1','bad','',Infinity,NaN]) {
  refusal([{...records[0],rmst_diff_se:.3},
           {...records[1],rmst_diff_se:bad}],String(bad));
}
const valid = records.map((r,i)=>({...r,rmst_diff_se:i===0?.3:.4}));
const result = S.poolRMSTDiff(valid,6);
assert.equal(result.k,2,'valid independent sources pool');
assert.equal(result.error,undefined);
assert.ok(Math.abs(result.pooled_diff-.9)<1e-12);
assert.ok(Math.abs(result.ci_lo-(-2.149489136681656))<1e-9,
          'reported-SE positive control remains numerically unchanged');
assert.ok(Math.abs(result.ci_hi-3.949489136681656)<1e-9);
assert.deepEqual(result.per_study.map(x=>x.se),[.3,.4]);
// The same NCT can occur in separately materialized source records. Inverse
// variance pooling must not count it twice, even with differing local IDs.
const duplicated = S.poolRMSTDiff([
  {...valid[0],nct:'NCT00000042',studyId:'local-A'},
  {...valid[1],nct:' nct00000042 ',studyId:'local-B'}
],6);
assert.equal(duplicated.k,0,'repeated NCT must not inflate k');
assert.deepEqual(duplicated.per_study,[],'no partial evidence from duplicate');
assert.match(duplicated.error,/Repeated RMST study identity/);
assert.equal(duplicated.ci_lo,undefined,'no confidence interval on refusal');
// Alias-based duplicates must also fail; a different first alias must not
// conceal the canonical NCT shared by the source records.
const aliases = S.poolRMSTDiff([
  {...valid[0],studyId:'Trial One',nct:'NCT00000042'},
  {...valid[1],study_id:' trial one ',nct:'NCT00000043'}
],6);
assert.equal(aliases.k,0,'cross-alias duplicate must be refused');
assert.match(aliases.error,/Repeated RMST study identity/);
const independent = S.poolRMSTDiff([
  {...valid[0],nct:'NCT00000042',studyId:'local-A'},
  {...valid[1],nct:'NCT00000043',studyId:'local-B'}
],6);
assert.equal(independent.k,2,'genuinely separate studies remain eligible');
assert.ok(Math.abs(independent.pooled_diff-result.pooled_diff)<1e-12);
assert.ok(Math.abs(independent.ci_lo-result.ci_lo)<1e-12);
const decimal = S.poolRMSTDiff([
  {...records[0],rmst_diff_se:'3e-1'},
  {...records[1],rmst_diff_se:'0.4'}],6);
assert.equal(decimal.k,2,'valid decimal text remains compatible');
console.log('RMST SOURCE SE GUARD PASS ' + copy);
"""

@pytest.mark.parametrize("copy", COPIES)
def test_refuse_unsourced_or_malformed_rmst_standard_error(copy):
    proc = subprocess.run(
        ["node", "-e", JS, copy],
        cwd=ROOT, text=True, capture_output=True, timeout=30, check=False
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    assert "RMST SOURCE SE GUARD PASS" in proc.stdout
