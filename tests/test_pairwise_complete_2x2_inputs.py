"""Fail closed when malformed 2x2 rows would previously be silently omitted.

All numbers here are synthetic; these are real shipped-JavaScript regression
tests, not a version-pinned R/metafor comparison or clinical validation.
Methodology: Cochrane Handbook chapter 10 section 10.12 (missing outcome
summary data should be described, not silently ignored in a pooled analysis).
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
VALID = [
    {"name": "A", "tE": 5, "tN": 100, "cE": 25, "cN": 100},
    {"name": "B", "tE": 15, "tN": 100, "cE": 20, "cN": 100},
    {"name": "C", "tE": 10, "tN": 100, "cE": 12, "cN": 100},
]


def _pool(copy, rows):
    js = """
require('./' + process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const r = globalThis.PairwisePool.pool2x2(rows);
console.log(JSON.stringify({
  error: r.error || null,
  k_used: r.k_used,
  per_study: r.perStudy.length,
  mu: Number.isFinite(r.mu) ? r.mu : null
}));
"""
    p = subprocess.run(
        ["node", "-e", js, copy, json.dumps(rows)],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
def test_valid_counts_preserve_original_internal_js_result(copy):
    r = _pool(copy, VALID)
    assert r["error"] is None
    assert r["k_used"] == r["per_study"] == 3
    # This number is the previous JS output, explicitly NOT an R oracle.
    assert r["mu"] == pytest.approx(0.5216714003823785, abs=1e-12)


@pytest.mark.parametrize("copy", COPIES)
def test_double_zero_handling_is_unchanged(copy):
    r = _pool(copy, VALID + [
        {"name": "double-zero", "tE": 0, "tN": 90, "cE": 0, "cN": 90}
    ])
    assert r["error"] is None
    assert r["k_used"] == r["per_study"] == 3
    assert r["mu"] == pytest.approx(0.5216714003823785, abs=1e-12)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("field", ["tE", "tN", "cE", "cN"])
@pytest.mark.parametrize("mode", ["absent", "null"])
def test_missing_field_refuses_entire_pool(copy, field, mode):
    bad = {**VALID[0], "name": "missing-data-study"}
    if mode == "absent":
        del bad[field]
    else:
        bad[field] = None
    r = _pool(copy, VALID + [bad])
    assert "Missing raw 2x2 counts" in r["error"]
    assert "trial 4" in r["error"]
    assert r["k_used"] == r["per_study"] == 0
    assert r["mu"] is None


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("delta", [
    {"tN": 0}, {"cN": 0},
    {"tE": -1}, {"cE": -1},
    {"tE": 101}, {"cE": 101},
], ids=["zero-treated-denom", "zero-control-denom",
        "negative-treated-events", "negative-control-events",
        "treated-events-exceed-n", "control-events-exceed-n"])
def test_impossible_2x2_refuses_entire_pool(copy, delta):
    bad = {**VALID[0], "name": "impossible-data-study", **delta}
    r = _pool(copy, VALID + [bad])
    assert "Impossible raw 2x2 counts" in r["error"]
    assert "trial 4" in r["error"]
    assert r["k_used"] == r["per_study"] == 0
    assert r["mu"] is None


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("bad", [None, [], 17, "bad-row"])
def test_malformed_trial_record_refuses_entire_pool(copy, bad):
    r = _pool(copy, VALID + [bad])
    assert "malformed record in trial 4" in r["error"]
    assert r["k_used"] == r["per_study"] == 0
    assert r["mu"] is None


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("bad", [None, {"trials": VALID}, "not-array"])
def test_nonarray_trial_collection_refused(copy, bad):
    r = _pool(copy, bad)
    assert "Invalid raw 2x2 input" in r["error"]
    assert r["k_used"] == r["per_study"] == 0
    assert r["mu"] is None


def test_shipped_engine_copies_identical():
    assert (ROOT / COPIES[0]).read_bytes() == (ROOT / COPIES[1]).read_bytes()
    assert (ROOT / COPIES[1]).read_bytes() == (ROOT / COPIES[2]).read_bytes()
