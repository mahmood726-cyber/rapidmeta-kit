"""Numerical refusal regression for inverse-variance 2x2 pooling.

Synthetic precision stress only: 2**53-1 is not a clinical trial size.
The native R oracle is a separate CI job, not replaced by these Node tests.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = (
    "assets/vendor/pairwise-pool.js",
    "docs/assets/vendor/pairwise-pool.js",
    "template/assets/vendor/pairwise-pool.js",
)

MAX_SAFE = 2**53 - 1
BAD = {"name": "synthetic-near-saturated", "tE": MAX_SAFE - 1,
       "tN": MAX_SAFE, "cE": MAX_SAFE - 1, "cN": MAX_SAFE}
GOOD_A = {"name": "synthetic-A", "tE": 18, "tN": 150, "cE": 30, "cN": 150}
GOOD_B = {"name": "synthetic-B", "tE": 21, "tN": 160, "cE": 35, "cN": 160}
GOOD_C = {"name": "synthetic-C", "tE": 35, "tN": 170, "cE": 31, "cN": 170}

JS = """
require('./' + process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const r = globalThis.PairwisePool.pool2x2(rows, opts);
console.log(JSON.stringify({
  error: r.error || null, k_used: r.k_used,
  perStudy: r.perStudy, excludedStudies: r.excludedStudies,
  hasPooledEffect: Object.hasOwn(r, 'mu')
}));
"""


def run(copy, rows, measure, method="PM"):
    result = subprocess.run(
        ["node", "-e", JS, copy, json.dumps(rows),
         json.dumps({"measure": measure, "tau2Method": method})],
        cwd=ROOT, check=True, text=True, capture_output=True, timeout=30,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("bad_first", (True, False))
def test_rr_must_refuse_entire_pool_if_positive_variance_rounds_to_zero(copy, bad_first):
    # Before the fix, RR returned an apparently valid k=2 pool, silently
    # discarding the third, correctly bounded integer-count study.
    rows = [BAD, GOOD_A, GOOD_B] if bad_first else [GOOD_A, GOOD_B, BAD]
    result = run(copy, rows, "RR")
    assert result["error"] is not None
    assert "non-positive variance" in result["error"]
    assert "entire pool refused" in result["error"]
    assert result["k_used"] == 0
    assert result["perStudy"] == []
    assert result["excludedStudies"] == []
    assert not result["hasPooledEffect"]


@pytest.mark.parametrize("copy", COPIES)
def test_or_still_pools_valid_three_study_precision_stress(copy):
    # OR variance is representable for the same 2x2 tables; do not blanket
    # reject otherwise admissible raw counts merely because RR is unstable.
    result = run(copy, [BAD, GOOD_A, GOOD_B], "OR")
    assert result["error"] is None
    assert result["k_used"] == 3
    assert len(result["perStudy"]) == 3
    assert result["hasPooledEffect"]


@pytest.mark.parametrize("copy", COPIES)
def test_ordinary_rr_dl_control_unchanged(copy):
    result = run(copy, [GOOD_A, GOOD_B, GOOD_C], "RR", "DL")
    assert result["error"] is None
    assert result["k_used"] == 3
    assert len(result["perStudy"]) == 3
    assert result["hasPooledEffect"]
