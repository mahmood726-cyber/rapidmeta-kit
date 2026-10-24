"""Numerical-integrity tests for zero-cell corrections in shipped PairwisePool.

Node executes the real modules on INVENTED 2x2 counts. Passing these tests
does not establish R/metafor parity or independent clinical validation.
Methods: Cochrane Handbook Chapter 10 §10.4.4.1;
https://wviechtb.github.io/metafor/reference/escalc.html
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
# Synthetic data, not reported clinical trials.
WITH_ZERO = [
    {"name": "A", "tE": 5, "tN": 100, "cE": 25, "cN": 100},
    {"name": "B", "tE": 15, "tN": 100, "cE": 20, "cN": 100},
    {"name": "C", "tE": 0, "tN": 100, "cE": 8, "cN": 100},
]


def _pool(copy, rows, correction):
    script = """
require('./' + process.argv[1]);
const trials = JSON.parse(process.argv[2]), opts = JSON.parse(process.argv[3]);
if (opts.haldane === '__NaN__') opts.haldane = NaN;
if (opts.haldane === '__Infinity__') opts.haldane = Infinity;
if (opts.haldane === '__-Infinity__') opts.haldane = -Infinity;
const r = globalThis.PairwisePool.pool2x2(trials, opts);
console.log(JSON.stringify({
  error: r.error || null, k_used: r.k_used,
  perStudyLength: r.perStudy.length,
  mu: Number.isFinite(r.mu) ? r.mu : null,
  boundaryRR: r.perStudy.length ? r.perStudy[r.perStudy.length-1].eff : null
}));
"""
    opts = {} if correction == "__OMITTED__" else {"haldane": correction}
    p = subprocess.run(
        ["node", "-e", script, copy, json.dumps(rows), json.dumps(opts)],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("correction", ["__OMITTED__", None, 0.5])
def test_default_and_numeric_half_preserve_results(copy, correction):
    r = _pool(copy, WITH_ZERO, correction)
    assert r["error"] is None
    assert r["k_used"] == r["perStudyLength"] == 3
    # Frozen pre-fix JS anchor, NOT an R/metafor oracle.
    assert r["mu"] == pytest.approx(0.3072346402549919, abs=1e-12)
    assert r["boundaryRR"] == pytest.approx(1 / 17, abs=1e-12)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("correction", [0.25, 1.0])
def test_positive_numeric_correction_is_accepted(copy, correction):
    r = _pool(copy, WITH_ZERO, correction)
    assert r["error"] is None
    assert r["k_used"] == r["perStudyLength"] == 3
    assert r["mu"] > 0
    assert 0 < r["boundaryRR"] < 1


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("correction", [
    0, -0.5, "0.5", "", "junk", True, False,
    [], {}, "__NaN__", "__Infinity__", "__-Infinity__",
])
@pytest.mark.parametrize("rows", [WITH_ZERO, WITH_ZERO[:2]], ids=["boundary", "no-boundary"])
def test_invalid_correction_refuses_entire_pool(copy, correction, rows):
    r = _pool(copy, rows, correction)
    assert "Invalid zero-cell continuity correction" in r["error"]
    assert "pooling refused" in r["error"]
    assert r["k_used"] == r["perStudyLength"] == 0
    assert r["mu"] is None


def test_distributed_sources_remain_byte_identical():
    assert (ROOT / COPIES[0]).read_bytes() == (ROOT / COPIES[1]).read_bytes()
    assert (ROOT / COPIES[1]).read_bytes() == (ROOT / COPIES[2]).read_bytes()
