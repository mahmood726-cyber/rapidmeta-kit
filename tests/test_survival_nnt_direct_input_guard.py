"""Direct public NNT converter must reject coercible non-evidence tokens.

The Altman–Andersen fixed-time arithmetic is preserved for legitimate finite
numbers and decimal/exponential text. These checks do NOT validate a clinical
time-specific control-group survival probability or independent R parity.
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "docs/assets", "template/assets")
NODE = r"""
const assert = require('node:assert/strict');
const S = require('./' + process.argv[1] + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const bad = [
 [true, 0.1], [false, 0.1], [[0.75], 0.1],
 [{valueOf: () => 0.75}, 0.1], ['0x1', 0.1], ['', 0.1],
 [0.75, [0.1]], [0.75, {valueOf: () => 0.1}],
 [0.75, '0x0.1'], [0.75, []], [0.75, null]
];
for (const [hr, risk] of bad) {
  const r = S.nntForHR(hr, risk);
  assert.deepEqual(r, {nnt: null, arr: null, tx_risk: null, direction: null},
    'invalid HR or baseline risk must refuse without partial effect: ' + String(hr));
}
const expectedBenefit = 1 / (0.1 - (1 - Math.pow(0.9, 0.75)));
for (const [hr, risk] of [[0.75, 0.1], ['7.5e-1', '1e-1']]) {
  const r = S.nntForHR(hr, risk);
  assert.equal(r.direction, 'NNTB');
  assert.ok(Number.isFinite(r.nnt));
  assert.ok(Math.abs(r.nnt - expectedBenefit) < 1e-10);
}
const harm = S.nntForHR(1.5, 0.1);
assert.equal(harm.direction, 'NNTH');
assert.ok(Math.abs(harm.nnt - (1 / ((1-Math.pow(0.9,1.5))-0.1))) < 1e-10);
console.log('NNT DIRECT SOURCE INPUT GUARD PASS ' + process.argv[1]);
"""

@pytest.mark.parametrize("copy", COPIES)
def test_nnt_direct_refuses_coercible_inputs(copy):
    p = subprocess.run(["node", "-e", NODE, copy], cwd=ROOT,
                       text=True, capture_output=True, timeout=30,
                       check=False)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert "NNT DIRECT SOURCE INPUT GUARD PASS" in p.stdout
