"""Refuse naive pooling of repeated registered trials in the 2x2 inverse-variance path.

Cochrane Handbook current Ch. 6 s 6.2.9 and Ch. 23 s 23.3.4: repeated
shared participants/arms cause unit-of-analysis errors. The kit has no
multi-arm covariance model, so a repeated NCT identifier must be resolved
manually before pooling. A repeated NCT is not proof of overlap: independent
comparisons within one study can be legitimate but require assessment.

All trial counts here are SYNTHETIC. Tests execute each shipped JS engine,
not R/metafor, RevMan, clinical records or an external validation oracle.
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
STUDIES = [
    {"name": "Study A", "nct": "NCT00000001", "tE": 5, "tN": 30, "cE": 9, "cN": 30},
    {"name": "Study B", "nct": "NCT00000002", "tE": 10, "tN": 45, "cE": 11, "cN": 45},
    {"name": "Study C", "nct": "NCT00000003", "tE": 8, "tN": 40, "cE": 13, "cN": 40},
]


def _pool(copy, rows, measure="RR"):
    snippet = """
require('./' + process.argv[1]);
const input = JSON.parse(process.argv[2]);
const options = JSON.parse(process.argv[3]);
const r = globalThis.PairwisePool.pool2x2(input, options);
console.log(JSON.stringify({
  error: r.error || null,
  k_used: r.k_used,
  per_study: r.perStudy.length,
  excluded: r.excludedStudies,
  mu: Number.isFinite(r.mu) ? r.mu : null
}));
"""
    result = subprocess.run(
        ["node", "-e", snippet, copy, json.dumps(rows), json.dumps({"measure": measure})],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
@pytest.mark.parametrize("kind", ["exact", "case-and-space", "adjacent", "different-counts"])
def test_repeated_nct_refuses_to_pool_without_independence_assessment(copy, measure, kind):
    repeated = {**STUDIES[0], "name": "Different comparison name"}
    rows = [*STUDIES]
    if kind == "case-and-space":
        repeated["nct"] = " nct00000001 "
    elif kind == "different-counts":
        repeated["tE"] = 9
    if kind == "adjacent":
        rows.insert(1, repeated)
        pair = "trials 1 and 2"
    else:
        rows.append(repeated)
        pair = "trials 1 and 4"
    result = _pool(copy, rows, measure)
    assert "Repeated NCT study identifier NCT00000001" in result["error"]
    assert pair in result["error"]
    assert "multi-arm/shared-participant" in result["error"]
    assert result["k_used"] == result["per_study"] == 0
    assert result["mu"] is None
    assert result["excluded"] == []


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
@pytest.mark.parametrize("bad", [123, {"id": "NCT00000004"}, "  "], ids=["numeric", "object", "blank"])
def test_malformed_present_study_identifier_refuses(copy, measure, bad):
    rows = [*STUDIES, {**STUDIES[0], "name": "Bad identifier", "nct": bad}]
    result = _pool(copy, rows, measure)
    assert "Invalid NCT identifier in trial 4" in result["error"]
    assert result["k_used"] == result["per_study"] == 0
    assert result["mu"] is None


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_distinct_identifiers_preserve_numerical_results(copy, measure):
    baseline = _pool(copy, [{k: v for k, v in row.items() if k != "nct"} for row in STUDIES], measure)
    tagged = _pool(copy, STUDIES, measure)
    assert baseline["error"] is None and tagged["error"] is None
    assert baseline["k_used"] == tagged["k_used"] == 3
    assert tagged["mu"] == pytest.approx(baseline["mu"], abs=1e-14)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
def test_absent_or_empty_optional_nct_remains_compatible(copy, measure):
    untagged = [{k: v for k, v in row.items() if k != "nct"} for row in STUDIES]
    empty_tagged = [dict(row, nct="") for row in untagged]
    a = _pool(copy, untagged, measure)
    b = _pool(copy, empty_tagged, measure)
    assert a["error"] is None and b["error"] is None
    assert a["k_used"] == b["k_used"] == 3
    assert a["mu"] == pytest.approx(b["mu"], abs=1e-14)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ["RR", "OR"])
@pytest.mark.parametrize("boundary", ["both-zero", "both-all"])
def test_repeated_nct_does_not_disappear_in_exclusion_filter(copy, measure, boundary):
    extra = {"name": "Same trial boundary comparison", "nct": "nct00000001",
             "tE": 0, "tN": 10, "cE": 0, "cN": 10}
    if boundary == "both-all":
        extra.update({"tE": 10, "cE": 10})
    result = _pool(copy, [*STUDIES, extra], measure)
    assert "Repeated NCT study identifier" in result["error"]
    assert result["k_used"] == result["per_study"] == 0
    assert result["excluded"] == []
    assert result["mu"] is None


def test_all_three_distributed_js_modules_have_identical_bytes():
    assert (ROOT / COPIES[0]).read_bytes() == (ROOT / COPIES[1]).read_bytes()
    assert (ROOT / COPIES[1]).read_bytes() == (ROOT / COPIES[2]).read_bytes()
