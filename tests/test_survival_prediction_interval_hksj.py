"""HKSJ prediction interval must use the same adjusted pooled SE as its CI.

Synthetic algebraic guard only. Genuine R/metafor oracle runs separately in CI
(metafor-tests/test_interval_hr_metafor_oracle.py). No original clinical data.
"""
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "template/assets", "docs/assets")

# Four deliberately heterogeneous independent log effects and positive variances.
# These values trigger q*>1 after REML so using the pre-HKSJ SE narrows the PI.
YI = [0.18834274230829667, 0.6136462688923738,
      -0.8979944856056723, 0.1459654781547634]
VI = [0.007078724762954062, 0.01585607885918258,
      0.3701926996080275, 0.007318246865161381]

NODE = r"""
const assert = require('node:assert/strict');
const {RapidMetaSurvival: S} = require('./' + process.argv[1] +
                                        '/vendor/rapidmeta-survival.js');
const data = JSON.parse(process.argv[2]);
const p = S._poolLogRE(data.yi, data.vi);
assert(p && p.k === data.yi.length && p.k >= 3);
const t = S._tQuantile(.975, p.k - 1);
const weights = data.vi.map(v => 1 / (v + p.tau2));
const sumWeights = weights.reduce((a,b)=>a+b,0);
const oldSE = Math.sqrt(1 / sumWeights);
const qStar = (data.yi.reduce((a,y,i)=>a + weights[i] * (y-p.mu)**2,0)
               / (p.k - 1));
assert(qStar > 1.5, 'must stress a genuine HKSJ correction');
assert(p.tau2 > 0, 'test requires genuine heterogeneity');
const expectedHalfWidth = t*Math.sqrt(p.tau2 + p.se*p.se);
const legacyHalfWidth = t*Math.sqrt(p.tau2 + oldSE*oldSE);
const near = (x,y) => Math.abs(x-y) < 1e-9;
assert(near(p.pi_lo, p.mu-expectedHalfWidth),
       'PI lower endpoint must use HKSJ-adjusted pooled SE');
assert(near(p.pi_hi, p.mu+expectedHalfWidth),
       'PI upper endpoint must use HKSJ-adjusted pooled SE');
assert(expectedHalfWidth > legacyHalfWidth + .02,
       'negative control: unadjusted old formula must be detectably narrower');
console.log(JSON.stringify({k:p.k,tau2:p.tau2,qStar,
  oldHalfWidth:legacyHalfWidth,correctedHalfWidth:expectedHalfWidth}));
"""

@pytest.mark.parametrize("copy", COPIES)
def test_prediction_interval_uses_hksj_floored_mean_se(copy):
    proc = subprocess.run(
        ["node", "-e", NODE, copy, json.dumps({"yi": YI, "vi": VI})],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    result = json.loads(proc.stdout)
    assert result["qStar"] > 1.5
    assert result["correctedHalfWidth"] > result["oldHalfWidth"] + 0.02
