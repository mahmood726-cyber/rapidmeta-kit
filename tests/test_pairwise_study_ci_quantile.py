"""Precisely matched 95% normal study-level Wald intervals in shipped JS.

Entirely synthetic interior 2x2 data; native R is tested separately by
oracle-tests/test_study_wald.py (R 4.4.3), not emulated by this pytest.
"""
import json
import math
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = (
    "assets/vendor/pairwise-pool.js",
    "docs/assets/vendor/pairwise-pool.js",
    "template/assets/vendor/pairwise-pool.js",
)
ROWS = (
    {"name": "synthetic-A", "tE": 2, "tN": 23, "cE": 8, "cN": 29},
    {"name": "synthetic-B", "tE": 5, "tN": 40, "cE": 11, "cN": 44},
    {"name": "synthetic-C", "tE": 12, "tN": 80, "cE": 6, "cN": 75},
)
# Full normal quantile cross-checked by actual R stats::qnorm(0.975) CI.
Z975 = 1.959963984540054
NODE = """
require('./' + process.argv[1]);
const r = globalThis.PairwisePool.pool2x2(
  JSON.parse(process.argv[2]), JSON.parse(process.argv[3]));
console.log(JSON.stringify({error: r.error || null, k: r.k_used,
                            mu: r.mu, perStudy: r.perStudy}));
"""


def run_node(copy, measure):
    cp = subprocess.run(
        ["node", "-e", NODE, copy, json.dumps(ROWS),
         json.dumps({"measure": measure, "tau2Method": "PM"})],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(cp.stdout)


def log_effect_variance(row, measure):
    a, n1, c, n0 = (row[k] for k in ("tE", "tN", "cE", "cN"))
    if measure == "RR":
        return (math.log((a / n1) / (c / n0)),
                1 / a - 1 / n1 + 1 / c - 1 / n0)
    return (math.log((a * (n0 - c)) / ((n1 - a) * c)),
            1 / a + 1 / (n1 - a) + 1 / c + 1 / (n0 - c))


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ("RR", "OR"))
def test_study_intervals_use_full_normal_quantile(copy, measure):
    result = run_node(copy, measure)
    assert result["error"] is None
    assert result["k"] == len(ROWS)
    assert len(result["perStudy"]) == len(ROWS)
    for row, study in zip(ROWS, result["perStudy"]):
        yi, vi = log_effect_variance(row, measure)
        assert vi > 0
        lo = math.exp(yi - Z975 * math.sqrt(vi))
        hi = math.exp(yi + Z975 * math.sqrt(vi))
        assert math.isclose(study["eff"], math.exp(yi), rel_tol=2e-13)
        assert math.isclose(study["ci_lo"], lo, rel_tol=2e-13)
        assert math.isclose(study["ci_hi"], hi, rel_tol=2e-13)
    # Negative regression: the previously rounded multiplier 1.96 must
    # fail the same tight comparison on the first non-trivial study.
    y0, v0 = log_effect_variance(ROWS[0], measure)
    rounded_hi = math.exp(y0 + 1.96 * math.sqrt(v0))
    assert not math.isclose(result["perStudy"][0]["ci_hi"], rounded_hi,
                            rel_tol=1e-8, abs_tol=1e-12)
