"""Negative/positive near-boundary generalized-Q solver checks.

Synthetic huge-count inputs detect premature PM bisection termination; these
are not plausible clinical trial data or independent R/metafor validation.
The native R 4.4.3 check is in oracle-tests/test_pairwise_oracle.py.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = [
    "assets/vendor/pairwise-pool.js",
    "docs/assets/vendor/pairwise-pool.js",
    "template/assets/vendor/pairwise-pool.js",
]


def synthetic_rows(delta):
    n = 10_000_000_000
    mid = n // 2
    return [
        {"name": "synthetic-up", "tE": mid + delta, "tN": n, "cE": mid, "cN": n},
        {"name": "synthetic-middle", "tE": mid, "tN": n, "cE": mid, "cN": n},
        {"name": "synthetic-down", "tE": mid - delta, "tN": n, "cE": mid, "cN": n},
    ]


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("delta,positive", [(70710, False), (70711, True)])
def test_pm_root_respects_near_zero_generalized_q_boundary(copy, delta, positive):
    script = """
require('./' + process.argv[1]);
const r = globalThis.PairwisePool.pool2x2(JSON.parse(process.argv[2]),
                                           {measure: 'RR', tau2Method: 'PM'});
console.log(JSON.stringify({error: r.error || null, k: r.k_used,
                            Q: r.Q, tau2: r.tau2}));
"""
    cp = subprocess.run(
        ["node", "-e", script, copy, json.dumps(synthetic_rows(delta))],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=True,
    )
    result = json.loads(cp.stdout)
    assert result["error"] is None
    assert result["k"] == 3
    if positive:
        assert result["Q"] > 2
        # Before the fix, termination at bracket width <1e-12 reported
        # 4.547473508864641e-13, ~250x the actual PM root.
        assert 0 < result["tau2"] < 1e-13
    else:
        # A genuinely nonpositive Q excess must not create heterogeneity.
        assert result["Q"] < 2
        assert result["tau2"] == 0
