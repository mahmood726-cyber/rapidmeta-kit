"""Interval-HR breakpoint arrays must not silently discard valid source effects.

Cochrane Handbook Ch 6: time windows for survival analyses are distinct
estimands. Synthetic source-executed JS validation only, NOT external R parity.
This is an input-integrity guard for the existing PR #62/#66 statistical stack.
"""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "docs/assets", "template/assets")

NODE = r"""
const assert = require('node:assert/strict');
const c = process.argv[1];
const S = require('./' + c + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const trials = [
  {nct: 'NCT_SYNTH_A', intervals: [
    {t0:0,t1:3,HR:.80,HR_ci_lo:.60,HR_ci_hi:.95},
    {t0:3,t1:6,HR:.90,HR_ci_lo:.70,HR_ci_hi:1.10}]},
  {nct: 'NCT_SYNTH_B', intervals: [
    {t0:0,t1:3,HR:.75,HR_ci_lo:.55,HR_ci_hi:.94},
    {t0:3,t1:6,HR:.85,HR_ci_lo:.65,HR_ci_hi:1.02}]}
];
const syntheticRawJSON = JSON.stringify({trials, breakpoints:[0,3,6]});
const inputSHA256 = require('node:crypto').createHash('sha256')
  .update(syntheticRawJSON, 'utf8').digest('hex');
assert.equal(inputSHA256,
  'efefeb2583d2cdc4b5006706aac19aaea1e76f92976aec30e7144092172866ec',
  'canonical synthetic raw fixture identity must not drift');
const reference = S.intervalHRPool(trials, [0,3,6]);
assert.equal(reference.error, undefined);
assert.equal(reference.intervals.length, 2, 'numeric windows should pool');
for (const [index, window] of reference.intervals.entries()) {
  assert.equal(window.k, 2, 'must preserve two independent studies');
  assert.equal(window.t0, [0,3][index]);
  assert.equal(window.t1, [3,6][index]);
  assert.ok(Number.isFinite(window.HR) && window.HR > 0);
  assert.ok(Number.isFinite(window.HR_ci_lo));
  assert.ok(Number.isFinite(window.HR_ci_hi));
}
// Decimal/scientific source text must be interpreted consistently in the
// coverage-alignment and effect-selection stages, not silently omitted.
const textual = S.intervalHRPool(trials, [' 0 ', '3e0', '6.0']);
assert.equal(textual.error, undefined,
    'ordinary numeric-source text must remain a permitted boundary');
assert.equal(textual.intervals.length, reference.intervals.length,
    'text boundaries must not erase all correctly aligned source effects');
for (let i=0; i<reference.intervals.length; i++) {
  const wanted=reference.intervals[i], actual=textual.intervals[i];
  assert.equal(actual.k, wanted.k);
  assert.equal(actual.t0, wanted.t0);
  assert.equal(actual.t1, wanted.t1);
  for (const key of ['HR','HR_ci_lo','HR_ci_hi','tau2','I2'])
    assert.ok(Math.abs(actual[key]-wanted[key]) < 1e-12,
      'numerical breakpoint aliases changed ' + key);
}
// An invalid, unsorted, non-decimal, or duplicate boundary must refuse
// the entire synthesis. Returning only two apparently valid windows is unsafe.
const invalid = [
  ['duplicate interior', [0,3,3,6]],
  ['duplicate endpoint', [0,3,6,6]],
  ['nondecimal hex', [0,3,6,'0x8']],
  ['blank endpoint', [0,3,6,'']],
  ['boolean endpoint', [0,3,6,false]],
  ['null endpoint', [0,3,6,null]],
  ['array endpoint', [0,3,6,[]]],
  ['object endpoint', [0,3,6,{}]],
  ['infinite endpoint', [0,3,6,Infinity]],
  ['overflow decimal', [0,3,6,'1e309']],
  ['negative endpoint', [0,3,6,-1]],
  ['unsorted endpoint', [0,3,6,5]]
];
for (const [label, boundaries] of invalid) {
  const result = S.intervalHRPool(trials, boundaries);
  assert.ok(result && result.error && Array.isArray(result.intervals) &&
       result.intervals.length === 0,
       label + ' must refuse without a partial pooled interval');
}
console.log('INTERVAL BP SOURCE INTEGRITY PASS ' + c);
"""

@pytest.mark.parametrize("copy", COPIES)
def test_interval_breakpoints_are_numeric_aligned_and_fail_closed(copy):
    p = subprocess.run(["node", "-e", NODE, copy], cwd=ROOT,
                       capture_output=True, text=True, timeout=30,
                       check=False)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert "INTERVAL BP SOURCE INTEGRITY PASS" in p.stdout
