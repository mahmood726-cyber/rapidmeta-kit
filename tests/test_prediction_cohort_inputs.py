"""Fail-closed, executable regression tests for prediction-model C/AUC ingestion.

Uses each of the actual three shipped vendor copies through Node's vm. This
checks coercion/selection only; it is NOT an independent R statistical oracle.
"""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "template/assets/vendor/prediction-pool.js"
COPIES = [
    "template/assets/vendor/prediction-pool.js",
    "assets/vendor/prediction-pool.js",
    "docs/assets/vendor/prediction-pool.js",
]

JS_TEST = r"""
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const filename = process.argv[1];
const sandbox = {};
sandbox.window = sandbox;
vm.runInNewContext(fs.readFileSync(filename, 'utf8'), sandbox, {filename});
const pick = sandbox.PredictionPool.__test__.pickPredictionCohorts;
function rows(record) { return pick({study: record}); }

let out = rows({name: 'top AUC', C: null, AUC: 0.78,
                C_se: null, AUC_se: 0.03});
assert.equal(out.length, 1, 'null C must not hide valid AUC');
assert.equal(out[0].C, 0.78);
assert.equal(out[0].C_se, 0.03);

out = rows({name: 'nested AUC',
            allOutcomes: [{type: 'PREDICTION', C: null, AUC: 0.81,
                           C_se: null, AUC_se: 0.04}]});
assert.equal(out.length, 1, 'nested null C must not be treated as zero');
assert.equal(out[0].C, 0.81);
assert.equal(out[0].C_se, 0.04);

out = rows({name: 'boundary recovery', C: 1, AUC: 0.72,
            C_se: 0, AUC_se: 0.02});
assert.equal(out.length, 1);
assert.equal(out[0].C, 0.72);
assert.equal(out[0].C_se, 0.02);

out = rows({name: 'reported C', C: 0.77, C_se: null, AUC_se: null});
assert.equal(out.length, 1);
assert.equal(out[0].C, 0.77);
assert.equal(out[0].C_se, undefined, 'missing SE cannot become 0');

out = rows({name: 'positive numeric SE', C: 0.67, C_se: '0.025'});
assert.equal(out.length, 1);
assert.equal(out[0].C_se, 0.025);

for (const r of [
  {C: null, AUC: null},
  {C: false, AUC: ''},
  {C: 0, AUC: 1},
  {C: -0.2, AUC: 2},
  {C: Infinity, AUC: NaN},
  {allOutcomes: [{type: 'DISCRIMINATION', C: null, AUC: 2}]},
]) {
  assert.equal(rows(r).length, 0, 'invalid discrimination value accepted');
}
console.log('prediction-cohort input regression: 11 cases PASS');
"""


def test_vendor_copies_exactly_match_template():
    source = CANONICAL.read_bytes()
    for relative in COPIES[1:]:
        assert (ROOT / relative).read_bytes() == source, relative


@pytest.mark.parametrize("relative", COPIES)
def test_null_auc_fallback_and_missing_se_do_not_silently_corrupt(relative):
    result = subprocess.run(
        ["node", "-e", JS_TEST, relative],
        cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
    )
    assert result.returncode == 0, (
        f"{relative}: node exit {result.returncode}\\n"
        f"STDOUT:\\n{result.stdout}\\nSTDERR:\\n{result.stderr}"
    )
    assert "11 cases PASS" in result.stdout
