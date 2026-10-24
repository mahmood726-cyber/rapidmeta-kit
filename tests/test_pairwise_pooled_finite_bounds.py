"""Regression: never publish overflowed or underflowed pooled CI/PI ratios.

All cases here are synthetic numerical stress tests executed against real
shipped JavaScript using Node. They are NOT trial data, an R oracle, or
independent evidence-synthesis validation. Method-matched R parity remains in
the existing separate oracle suites.
"""
import json
import math
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VENDORS = [
    "assets/vendor/pairwise-pool.js",
    "template/assets/vendor/pairwise-pool.js",
    "docs/assets/vendor/pairwise-pool.js",
]
METHODS = ("DL", "PM")

JS = r"""
require('./' + process.argv[1]);
const trials = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const result = globalThis.PairwisePool.pool2x2(trials, opts);
console.log(JSON.stringify(result));
"""


def call_vendor(path, trials, measure, method):
    process = subprocess.run(
        ["node", "-e", JS, path, json.dumps(trials),
         json.dumps({"measure": measure, "tau2Method": method})],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(process.stdout)


def opposed_extreme_tables():
    # Exactly representable safe-integer 2x2 counts; no clinical claim.
    n = (1 << 53) - 1
    return [
        {"name": "high-OR synthetic", "tE": n - 1, "tN": n,
         "cE": 1, "cN": n},
        {"name": "low-OR synthetic", "tE": 1, "tN": n,
         "cE": n - 1, "cN": n},
    ]


@pytest.mark.parametrize("path", VENDORS)
@pytest.mark.parametrize("method", METHODS)
def test_extreme_or_must_refuse_unrepresentable_ci_not_serialize_null(path, method):
    # Before this fix: finite fitted mu and tau2, but exp(ciLo) == 0 and
    # exp(ciHi) == Infinity. JSON.stringify silently encoded ci_hi as null.
    result = call_vendor(path, opposed_extreme_tables(), "OR", method)
    assert "Unrepresentable pooled ratio or interval endpoint" in result.get("error", "")
    assert result["k_used"] == 0
    assert result["perStudy"] == []
    assert "ci_hi" not in result  # Never export a misleading 0/null CI.


@pytest.mark.parametrize("path", VENDORS)
@pytest.mark.parametrize("method", METHODS)
def test_extreme_rr_with_representable_ci_remains_eligible(path, method):
    # Guard must be based on *actual numerical representation*, not merely
    # the size of the input counts. These same independent counts yield a
    # representable RR CI, though interpretation would require expert review.
    result = call_vendor(path, opposed_extreme_tables(), "RR", method)
    assert "error" not in result
    assert result["k_used"] == 2
    for field in ("mu", "ci_lo", "ci_hi"):
        assert math.isfinite(result[field]) and result[field] > 0


@pytest.mark.parametrize("path", VENDORS)
@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("measure", ("RR", "OR"))
def test_moderate_heterogeneity_three_studies_remains_finite(path, method, measure):
    # Ordinary synthetic three-study calculation: both the CI and PI are
    # representable and should continue to pool unchanged.
    trials = [
        {"tE": 3, "tN": 120, "cE": 26, "cN": 120},
        {"tE": 41, "tN": 130, "cE": 16, "cN": 135},
        {"tE": 22, "tN": 110, "cE": 45, "cN": 125},
    ]
    result = call_vendor(path, trials, measure, method)
    assert "error" not in result
    assert result["k_used"] == 3
    for field in ("mu", "ci_lo", "ci_hi", "pi_lo", "pi_hi"):
        assert math.isfinite(result[field]) and result[field] > 0
    assert result["ci_lo"] < result["mu"] < result["ci_hi"]
    assert result["pi_lo"] < result["pi_hi"]
