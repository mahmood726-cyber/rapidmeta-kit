"""Fail closed when individual-study exponentiated Wald limits cannot be represented.

These deliberately synthetic, extreme continuity-correction inputs test the
actual shipped JavaScript in Node. They are not clinical observations and do
not constitute native R/metafor numerical parity.
See https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/JSON/stringify
for the documented Infinity-to-null serialization hazard.
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
# Binomial counts are integers. Only the *user-configured* correction varies.
ROWS = [
    {"name": "synthetic boundary", "tE": 0, "tN": 100, "cE": 8, "cN": 100},
    {"name": "synthetic A", "tE": 8, "tN": 100, "cE": 16, "cN": 100},
    {"name": "synthetic B", "tE": 16, "tN": 200, "cE": 32, "cN": 200},
]
JS = """
require('./' + process.argv[1]);
const rows = JSON.parse(process.argv[2]);
const opts = JSON.parse(process.argv[3]);
const result = globalThis.PairwisePool.pool2x2(rows, opts);
console.log(JSON.stringify(result));
"""


def execute_shipped(copy, measure, method, correction):
    result = subprocess.run(
        ["node", "-e", JS, copy, json.dumps(ROWS),
         json.dumps({"measure": measure, "tau2Method": method,
                     "haldane": correction})],
        cwd=ROOT, text=True, capture_output=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ("RR", "OR"))
@pytest.mark.parametrize("method", ("PM", "DL"))
def test_extreme_positive_correction_refuses_null_or_zero_study_ci(copy, measure, method):
    # Pre-fix: all four method/measure combinations pooled k=3 with a valid
    # pooled estimate, but study 1 had ci_lo=0, ci_hi=Infinity; serialization
    # silently changed Infinity to null.
    result = execute_shipped(copy, measure, method, 1e-200)
    assert "Unrepresentable individual-study 2x2 ratio or 95% Wald CI" in result["error"]
    assert "trial 1" in result["error"]
    assert result["k_used"] == 0
    assert result["perStudy"] == []
    assert result["excludedStudies"] == []
    assert "mu" not in result and "ci_lo" not in result


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("measure", ("RR", "OR"))
@pytest.mark.parametrize("method", ("PM", "DL"))
@pytest.mark.parametrize("correction", (0.25, 0.5))
def test_representable_positive_corrections_preserve_study_and_pool(copy, measure, method, correction):
    result = execute_shipped(copy, measure, method, correction)
    assert "error" not in result
    assert result["k_used"] == len(result["perStudy"]) == len(ROWS)
    for study in result["perStudy"]:
        for key in ("eff", "ci_lo", "ci_hi"):
            assert math.isfinite(study[key]) and study[key] > 0
        assert study["ci_lo"] < study["eff"] < study["ci_hi"]
    for key in ("mu", "ci_lo", "ci_hi", "pi_lo", "pi_hi"):
        assert math.isfinite(result[key]) and result[key] > 0


def test_all_three_shipped_engine_copies_are_identical():
    blobs = [(ROOT / name).read_bytes() for name in COPIES]
    assert blobs[0] == blobs[1] == blobs[2]
