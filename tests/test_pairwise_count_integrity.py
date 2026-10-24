"""Regression: never pool fractional/unsafe raw 2x2 counts.

The test executes each *shipped* JavaScript module in Node (not a Python
reimplementation). Synthetic counts test input integrity, not R/metafor parity.
"""
import json
import math
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
COPIES = [
    "assets/vendor/pairwise-pool.js",
    "template/assets/vendor/pairwise-pool.js",
    "docs/assets/vendor/pairwise-pool.js",
]
VALID = [
    {"name": "A", "tE": 4, "tN": 100, "cE": 7, "cN": 100},
    {"name": "B", "tE": 7, "tN": 120, "cE": 8, "cN": 120},
    {"name": "C", "tE": 5, "tN": 90, "cE": 9, "cN": 90},
]


def _pool(copy, trials, measure="RR"):
    script = """
require('./' + process.argv[1]);
const trials = JSON.parse(process.argv[2]);
const r = globalThis.PairwisePool.pool2x2(trials, {measure: process.argv[3]});
console.log(JSON.stringify({
    error: r.error || null, k_used: r.k_used,
    mu: Number.isFinite(r.mu) ? r.mu : null,
    ci_lo: Number.isFinite(r.ci_lo) ? r.ci_lo : null
}));
"""
    p = subprocess.run(
        ["node", "-e", script, copy, json.dumps(trials), measure],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=20,
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_integer_2x2_counts_keep_existing_pool(copy, measure):
    r = _pool(copy, VALID, measure)
    assert r["error"] is None
    assert r["k_used"] == 3
    assert math.isfinite(r["mu"]) and r["mu"] > 0
    assert math.isfinite(r["ci_lo"]) and r["ci_lo"] > 0
    if measure == "RR":
        # Frozen pre-fix JS baseline: not presented as an R/metafor oracle.
        assert r["mu"] == pytest.approx(0.669175890556646, abs=1e-12)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("field,value", [
    ("tE", 1.5),                         # invalid fractional event count
    ("cE", 2.25),                        # invalid control event count
    ("tN", 100.5),                       # fractional denominator
    ("cN", 9007199254740992),            # above exact JS integer range
    ("tE", "3"),                         # numeric strings require explicit normalization
])
def test_one_bad_count_refuses_entire_pool_not_silent_subset(copy, field, value):
    bad = {"name": "bad", "tE": 3, "tN": 100, "cE": 4, "cN": 100}
    bad[field] = value
    r = _pool(copy, VALID + [bad])
    assert r["k_used"] == 0
    assert r["mu"] is None
    assert "Non-integer or unsafe 2x2 raw count" in r["error"]
    assert "trial 4" in r["error"]
