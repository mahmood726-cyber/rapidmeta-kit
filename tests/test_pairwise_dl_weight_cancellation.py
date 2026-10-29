"""Executable Node regressions for cancellation in the DL weight denominator.

Only synthetic extreme-count tables are used. Analytic cross-product
calculation is independent of the shipped JS denominator implementation.
Native R 4.4.3 oracle coverage is in oracle-tests/test_pairwise_oracle.py.
No claim of metafor parity or clinical validation is made here.
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

# All source counts are safe IEEE-754 integers; huge counts are intentional
# numerical stress fixtures, not actual studies.
N = 2**53 - 1
A = (N - 1) // 2
ROWS = ((A, N, A, N), (1, 100, 90, 100), (90, 100, 1, 100))


def independent_dl_tau2(measure):
    yi = []
    vi = []
    for a, n1, c, n0 in ROWS:
        if measure == "RR":
            yi.append(math.log((a / n1) / (c / n0)))
            vi.append(1 / a - 1 / n1 + 1 / c - 1 / n0)
        else:
            yi.append(math.log(a * (n0 - c) / ((n1 - a) * c)))
            vi.append(1 / a + 1 / (n1 - a) + 1 / c + 1 / (n0 - c))
    weights = [1 / v for v in vi]
    sw = math.fsum(weights)
    mu = math.fsum(w * y for w, y in zip(weights, yi)) / sw
    q = math.fsum(w * (y - mu)**2 for w, y in zip(weights, yi))
    # Positive cross-weight identity: 2 * sum(i<j, wi*wj)/sum(wi).
    c_stable = 2 * math.fsum(
        weights[i] * weights[j]
        for i in range(len(weights)) for j in range(i + 1, len(weights))
    ) / sw
    assert q > len(weights) - 1
    assert c_stable > 0
    # Failure injection: the original subtraction implementation must
    # produce a detectably different tau2 for this deliberately bad scaling.
    c_legacy = sw - sum(w*w for w in weights) / sw
    wrong_tau2 = (q - (len(weights) - 1)) / c_legacy
    true_tau2 = (q - (len(weights) - 1)) / c_stable
    assert abs(wrong_tau2 - true_tau2) / true_tau2 > 0.005
    return q, true_tau2


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ("RR", "OR"))
def test_dl_denominator_is_stable_with_dominant_study_weight(copy, measure):
    script = """
require('./' + process.argv[1]);
const trials = JSON.parse(process.argv[2]);
const out = globalThis.PairwisePool.pool2x2(
    trials, {measure: process.argv[3], tau2Method: 'DL'});
console.log(JSON.stringify({
    error: out.error || null, k_used: out.k_used,
    Q: out.Q, tau2: out.tau2, mu: out.mu
}));
"""
    records = [
        {"name": "synthetic-%d" % i,
         "tE": a, "tN": n1, "cE": c, "cN": n0}
        for i, (a, n1, c, n0) in enumerate(ROWS, start=1)
    ]
    cp = subprocess.run(
        ["node", "-e", script, copy, json.dumps(records), measure],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    )
    observed = json.loads(cp.stdout)
    assert observed["error"] is None
    assert observed["k_used"] == 3
    q_expected, tau2_expected = independent_dl_tau2(measure)
    assert math.isclose(observed["Q"], q_expected, rel_tol=1e-10)
    assert math.isclose(observed["tau2"], tau2_expected, rel_tol=1e-10)
    assert math.isclose(observed["mu"], 1.0, rel_tol=1e-10)
