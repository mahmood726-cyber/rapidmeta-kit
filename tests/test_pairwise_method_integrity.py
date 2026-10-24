"""PairwisePool must not substitute one estimand or tau2 estimator for another.

Runs all three *shipped* Node.js modules. Synthetic input tests method
routing/refusal and a frozen pre-fix JS baseline only; it is NOT an R oracle,
a real-trial reanalysis, or an independent scientific validation.

Methodological source: Cochrane Handbook Ch 6 §6.4 and Ch 10 §10.9:
2x2 risk/odds ratios are not hazard ratios.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
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
# Synthetic heterogeneous binomial counts: not clinical outcome data.
TRIALS = [
    {"name": "A", "tE": 5, "tN": 100, "cE": 30, "cN": 100},
    {"name": "B", "tE": 20, "tN": 100, "cE": 5, "cN": 100},
    {"name": "C", "tE": 10, "tN": 100, "cE": 20, "cN": 100},
]


def pool(copy, opts):
    script = """
require('./' + process.argv[1]);
const trials = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const r = globalThis.PairwisePool.pool2x2(trials, opts);
console.log(JSON.stringify({
  error: r.error || null,
  k_used: r.k_used,
  mu: Number.isFinite(r.mu) ? r.mu : null,
  tau2: Number.isFinite(r.tau2) ? r.tau2 : null,
  measure: r.measure,
  tau2Method: r.tau2Method || null,
  perStudyLength: r.perStudy.length
}));
"""
    p = subprocess.run(
        ["node", "-e", script, copy, json.dumps(TRIALS), json.dumps(opts)],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure,tau2_method,expected_mu,expected_tau2", [
    # Frozen JS behaviour before fix, not independently checked against R.
    ("RR", "PM", 0.6883368205430038, 2.3837417799818468),
    ("RR", "DL", 0.6874801432943429, 2.0055274247323625),
    ("OR", "PM", 0.6338996162813402, 3.1727350162768744),
    ("OR", "DL", 0.6333915340390825, 2.7630960323568075),
])
def test_supported_methods_preserve_existing_numeric_results(
    copy, measure, tau2_method, expected_mu, expected_tau2
):
    r = pool(copy, {"measure": measure, "tau2Method": tau2_method})
    assert r["error"] is None
    assert r["k_used"] == 3
    assert r["perStudyLength"] == 3
    assert r["measure"] == measure
    assert r["tau2Method"] == tau2_method
    assert r["mu"] == pytest.approx(expected_mu, abs=1e-12)
    assert r["tau2"] == pytest.approx(expected_tau2, abs=1e-10)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("opts,expected_measure,expected_tau2", [
    ({}, "RR", "PM"),
    ({"measure": "rr", "tau2Method": "dl"}, "RR", "DL"),
    ({"measure": "or", "tau2Method": "pm"}, "OR", "PM"),
    ({"measure": None, "tau2Method": None}, "RR", "PM"),
])
def test_valid_defaults_and_case_insensitive_methods(copy, opts, expected_measure, expected_tau2):
    r = pool(copy, opts)
    assert r["error"] is None
    assert r["measure"] == expected_measure
    assert r["tau2Method"] == expected_tau2
    assert r["k_used"] == 3


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("bad_measure", ["HR", "RD", "SMD", "RR_OR", "", 17, False])
def test_unsupported_effect_measures_refuse_without_pooling(copy, bad_measure):
    r = pool(copy, {"measure": bad_measure, "tau2Method": "PM"})
    assert "Unsupported raw 2x2 effect measure" in r["error"]
    assert "expected RR or OR" in r["error"]
    assert r["k_used"] == 0
    assert r["mu"] is None and r["tau2"] is None
    assert r["perStudyLength"] == 0


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("bad_tau2_method", ["REML", "ML", "SJ", "", 9, False])
def test_unsupported_tau2_estimators_refuse_without_pooling(copy, bad_tau2_method):
    r = pool(copy, {"measure": "RR", "tau2Method": bad_tau2_method})
    assert "Unsupported between-study variance method" in r["error"]
    assert "expected PM or DL" in r["error"]
    assert r["k_used"] == 0
    assert r["mu"] is None and r["tau2"] is None
    assert r["perStudyLength"] == 0
