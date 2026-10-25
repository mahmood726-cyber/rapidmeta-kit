"""Synthetic negative tests for GLMM integer counts and no silent trial exclusion.

Execute the three *actual distributed JavaScript engines* in Node. These are
input-integrity checks, NOT an external R/metafor oracle or clinical validation.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = [
    "assets/vendor/rare-events-glmm.js",
    "docs/assets/vendor/rare-events-glmm.js",
    "template/assets/vendor/rare-events-glmm.js",
]

NODE = r"""
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const engines = JSON.parse(process.argv[1]);
const good = [
  {events_T:0, n_T:20, events_C:2, n_C:20},
  {events_T:3, n_T:30, events_C:4, n_C:30},
];
const bad = [
  ['fractional event', {events_T:0.5, n_T:20, events_C:2, n_C:20}],
  ['fractional denominator', {events_T:0, n_T:20.5, events_C:2, n_C:20}],
  ['missing field', {events_T:0, n_T:20, events_C:2}],
  ['negative event', {events_T:-1, n_T:20, events_C:2, n_C:20}],
  ['events exceed N', {events_T:21, n_T:20, events_C:2, n_C:20}],
  ['unsafe integer', {events_T:0, n_T:9007199254740992, events_C:2, n_C:20}],
  ['string count', {events_T:'0', n_T:20, events_C:2, n_C:20}],
  ['nonfinite count', {events_T:Infinity, n_T:20, events_C:2, n_C:20}],
  ['null record', null],
];
let negative = 0, valid = 0;
for (const file of engines) {
  const engine = require(path.resolve(file));
  for (const method of ['fit', 'fitUnconditional', 'fitConditionalExact']) {
    for (const [label, row] of bad) {
      const result = engine[method]([...good, row]);
      assert.equal(result.ok, false, file+' '+method+' '+label+' must refuse');
      assert.match(result.error, /GLMM REFUSED.*study 3/);
      negative++;
    }
    for (const input of [null, {}, [], [good[0], undefined]]) {
      const result = engine[method](input);
      assert.equal(result.ok, false, file+' '+method+' malformed input must refuse');
      assert.match(result.error, /GLMM REFUSED/);
      negative++;
    }
  }
  const result = engine.fitConditionalExact(good);
  assert.equal(result.ok, true, file+' valid 2-study CM.EL must remain available');
  assert.equal(result.k, 2);
  assert.ok(Number.isFinite(result.theta));
  valid++;
}
console.log(JSON.stringify({negative, valid}));
"""

def test_invalid_and_ambiguous_glmm_rows_refuse_without_partial_pooling():
    completed = subprocess.run(
        ["node", "-e", NODE, json.dumps(ENGINES)],
        cwd=ROOT, check=False, capture_output=True, text=True, timeout=100,
    )
    assert completed.returncode == 0, completed.stderr + "\n" + completed.stdout
    counts = json.loads(completed.stdout.strip())
    assert counts == {"negative": 126, "valid": 3}, counts
