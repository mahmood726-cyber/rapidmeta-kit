"""Near-null fixed-time HR-to-NNT arithmetic must not lose small effects.

Synthetic mathematical fixture; it does not verify source control survival,
common follow-up time, censoring, or clinical NNT applicability.
Altman & Andersen, BMJ 1999;319:1492, doi:10.1136/bmj.319.7223.1492.
"""
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "template/assets", "docs/assets")
NODE = r"""
const assert = require('node:assert/strict');
const S = require('./' + process.argv[1] + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
for (const [hr, risk, expectedDirection] of [
    [1-1e-10, 0.25, 'NNTB'],
    [1+1e-10, 0.25, 'NNTH'],
    [1-1e-10, 1e-8, 'NNTB']
]) {
  const got = S.nntForHR(hr, risk);
  const logSurvival = Math.log1p(-risk);
  const expectedArr = (1-risk) * Math.expm1((hr-1)*logSurvival);
  const expectedNnt = 1 / Math.abs(expectedArr);
  assert.equal(got.direction, expectedDirection, 'near-null sign must survive');
  assert.ok(Number.isFinite(got.nnt), 'valid near-null NNT must remain finite');
  assert.ok(Math.abs(got.nnt/expectedNnt-1) < 1e-10, 'near-null NNT mismatch');
  assert.ok(Math.abs(got.arr/expectedArr-1) < 1e-10, 'ARR cancellation');
}
const exactlyNull = S.nntForHR(1, 0.25);
assert.equal(exactlyNull.nnt, null, 'HR=1 has no finite NNT');
assert.equal(exactlyNull.direction, null, 'no benefit/harm direction at exact null');
const ordinary = S.nntForHR(0.75, 0.1);
const expectedOrdinary = 1/(0.1 - (1-Math.pow(0.9,0.75)));
assert.ok(Math.abs(ordinary.nnt-expectedOrdinary)<1e-9);
console.log('Near-null NNT arithmetic regression PASS');
"""

@pytest.mark.parametrize("copy", COPIES)
def test_near_null_nnt_avoids_catastrophic_cancellation(copy):
    p = subprocess.run(["node", "-e", NODE, copy], cwd=ROOT,
                       text=True, capture_output=True, timeout=30, check=False)
    assert p.returncode == 0, p.stdout + "\n" + p.stderr
    assert "Near-null NNT arithmetic regression PASS" in p.stdout
