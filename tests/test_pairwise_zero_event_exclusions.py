"""Disclose no-event-in-either-arm exclusions in the shipped pairwise RR/OR engine.

Synthetic fixtures validate an existing exclusion policy and accounting only.
They are NOT an external R/metafor validation or independent clinical evidence.
Source: Cochrane Handbook ch 10, section 10.4.4.2.
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
ZERO_1 = {"name": "zero-first", "tE": 0, "tN": 100, "cE": 0, "cN": 100}
ZERO_2 = {"name": "zero-last", "tE": 0, "tN": 11, "cE": 0, "cN": 21}


def _pool(copy, rows, measure="RR"):
    script = """
require('./' + process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const r = globalThis.PairwisePool.pool2x2(rows, opts);
console.log(JSON.stringify({
  error: r.error || null,
  k_used: r.k_used,
  exclusions: r.excludedStudies,
  names: r.perStudy.map(s => s.name),
  mu: Number.isFinite(r.mu) ? r.mu : null,
  tau2: Number.isFinite(r.tau2) ? r.tau2 : null,
  Q: Number.isFinite(r.Q) ? r.Q : null
}));
"""
    result = subprocess.run(
        ["node", "-e", script, copy, json.dumps(rows), json.dumps({"measure": measure})],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_double_zero_exclusions_disclosed_without_changing_effects(copy, measure):
    control = _pool(copy, VALID, measure)
    result = _pool(copy, [ZERO_1, *VALID, ZERO_2], measure)
    assert result["error"] is None
    assert result["k_used"] == control["k_used"] == 3
    assert result["names"] == ["A", "B", "C"]
    assert result["exclusions"] == [
        {"trial_index": 1, "name": "zero-first", "reason": "DOUBLE_ZERO_EVENTS"},
        {"trial_index": 5, "name": "zero-last", "reason": "DOUBLE_ZERO_EVENTS"},
    ]
    assert result["mu"] == pytest.approx(control["mu"], abs=1e-14)
    assert result["Q"] == pytest.approx(control["Q"], abs=1e-14)
    assert result["tau2"] == pytest.approx(control["tau2"], abs=1e-14)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_no_exclusion_when_all_trials_estimable(copy, measure):
    result = _pool(copy, VALID, measure)
    assert result["error"] is None
    assert result["exclusions"] == []
    assert result["k_used"] == 3


@pytest.mark.parametrize("copy", COPIES)
def test_all_double_zero_studies_refuse_pool_but_disclose_each(copy):
    result = _pool(copy, [ZERO_1, ZERO_2])
    assert "Insufficient trials" in result["error"]
    assert result["k_used"] == 0
    assert result["mu"] is None
    assert [x["trial_index"] for x in result["exclusions"]] == [1, 2]


@pytest.mark.parametrize("copy", COPIES)
def test_one_usable_study_and_one_double_zero_refuse_pool(copy):
    result = _pool(copy, [VALID[0], ZERO_1])
    assert "Insufficient trials" in result["error"]
    assert result["k_used"] == 1
    assert result["exclusions"] == [
        {"trial_index": 2, "name": "zero-first", "reason": "DOUBLE_ZERO_EVENTS"}
    ]


@pytest.mark.parametrize("copy", COPIES)
def test_impossible_raw_data_refuse_not_relabelled_as_approved_exclusion(copy):
    bad = {"name": "bad", "tE": 11, "tN": 10, "cE": 1, "cN": 10}
    result = _pool(copy, [*VALID, ZERO_1, bad])
    assert "Impossible raw 2x2 counts" in result["error"]
    assert result["k_used"] == 0
    assert result["mu"] is None
    assert result["exclusions"] == []


def test_three_shipped_copies_remain_byte_identical():
    assert (ROOT / COPIES[0]).read_bytes() == (ROOT / COPIES[1]).read_bytes()
    assert (ROOT / COPIES[1]).read_bytes() == (ROOT / COPIES[2]).read_bytes()
