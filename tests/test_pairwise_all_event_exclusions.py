"""Cochrane ch 6 s 6.4.1.2: both-all-events contribute no relative RR/OR information.

Synthetic fixtures only. These tests execute each shipped Node module; they
are not real R/metafor comparisons, independent adjudication, or clinical data.
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
    {"name": "A", "tE": 8, "tN": 40, "cE": 15, "cN": 40},
    {"name": "B", "tE": 10, "tN": 70, "cE": 20, "cN": 65},
    {"name": "C", "tE": 30, "tN": 80, "cE": 40, "cN": 75},
]
BOTH_ALL_1 = {"name": "all-first", "tE": 10, "tN": 10, "cE": 30, "cN": 30}
BOTH_ALL_2 = {"name": "all-last", "tE": 9, "tN": 9, "cE": 19, "cN": 19}
BOTH_ZERO = {"name": "no events", "tE": 0, "tN": 10, "cE": 0, "cN": 12}
ONE_ARM_ALL = {"name": "one arm 100%", "tE": 10, "tN": 10, "cE": 8, "cN": 10}


def _pool(copy, rows, measure="RR"):
    snippet = """
require('./' + process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const r = globalThis.PairwisePool.pool2x2(rows, opts);
console.log(JSON.stringify({
  error: r.error || null,
  k_used: r.k_used,
  excluded: r.excludedStudies,
  names: r.perStudy.map(s => s.name),
  mu: Number.isFinite(r.mu) ? r.mu : null,
  Q: Number.isFinite(r.Q) ? r.Q : null,
  tau2: Number.isFinite(r.tau2) ? r.tau2 : null
}));
"""
    p = subprocess.run(
        ["node", "-e", snippet, copy, json.dumps(rows), json.dumps({"measure": measure})],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_both_all_events_excluded_not_weighted_or_used_to_change_effect(copy, measure):
    reference = _pool(copy, VALID, measure)
    got = _pool(copy, [BOTH_ALL_1, *VALID, BOTH_ALL_2], measure)
    assert reference["error"] is None and got["error"] is None
    assert reference["k_used"] == got["k_used"] == 3
    assert got["names"] == ["A", "B", "C"]
    assert got["excluded"] == [
        {"trial_index": 1, "name": "all-first", "reason": "BOTH_ARMS_ALL_EVENTS"},
        {"trial_index": 5, "name": "all-last", "reason": "BOTH_ARMS_ALL_EVENTS"},
    ]
    assert got["mu"] == pytest.approx(reference["mu"], abs=1e-14)
    assert got["Q"] == pytest.approx(reference["Q"], abs=1e-14)
    assert got["tau2"] == pytest.approx(reference["tau2"], abs=1e-14)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_both_full_and_both_zero_exclusions_are_distinguished(copy, measure):
    got = _pool(copy, [BOTH_ZERO, BOTH_ALL_1, *VALID], measure)
    assert got["error"] is None
    assert got["k_used"] == 3
    assert got["excluded"] == [
        {"trial_index": 1, "name": "no events", "reason": "DOUBLE_ZERO_EVENTS"},
        {"trial_index": 2, "name": "all-first", "reason": "BOTH_ARMS_ALL_EVENTS"},
    ]


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_one_arm_with_all_events_still_uses_continuity_correction(copy, measure):
    got = _pool(copy, [*VALID, ONE_ARM_ALL], measure)
    assert got["error"] is None
    assert got["k_used"] == 4
    assert got["excluded"] == []
    assert "one arm 100%" in got["names"]


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_one_remaining_trial_refuses_to_pool_but_reports_exclusion(copy, measure):
    got = _pool(copy, [VALID[0], BOTH_ALL_1], measure)
    assert "Insufficient trials" in got["error"]
    assert got["k_used"] == 1
    assert got["mu"] is None
    assert got["excluded"] == [
        {"trial_index": 2, "name": "all-first", "reason": "BOTH_ARMS_ALL_EVENTS"}
    ]


@pytest.mark.parametrize("copy", COPIES)
def test_all_studies_with_every_patient_event_refuse_and_disclose(copy):
    got = _pool(copy, [BOTH_ALL_1, BOTH_ALL_2], "RR")
    assert "Insufficient trials" in got["error"]
    assert got["k_used"] == 0
    assert got["mu"] is None
    assert [x["trial_index"] for x in got["excluded"]] == [1, 2]


@pytest.mark.parametrize("copy", COPIES)
def test_invalid_counts_are_refused_not_mislabelled_as_all_events(copy):
    invalid = {"name": "impossible", "tE": 11, "tN": 10, "cE": 30, "cN": 30}
    got = _pool(copy, [*VALID, BOTH_ALL_1, invalid], "RR")
    assert "Impossible raw 2x2 counts" in got["error"]
    assert got["mu"] is None
    assert got["k_used"] == 0
    assert got["excluded"] == []


def test_three_shipped_modules_byte_identical():
    assert (ROOT / COPIES[0]).read_bytes() == (ROOT / COPIES[1]).read_bytes()
    assert (ROOT / COPIES[1]).read_bytes() == (ROOT / COPIES[2]).read_bytes()
