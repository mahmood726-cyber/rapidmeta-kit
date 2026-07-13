"""The load-bearing tests: the Python harness reproduces the app's OWN number
(computed by the app's JS engine), and it FAILS loudly on a wrong number."""
import copy
import json
import os
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)
KIT = os.path.dirname(HARNESS)
CONFIG = os.path.join(KIT, "configs", "example_finerenone_ckd.json")
JS = os.path.join(HARNESS, "js_engine.js")

from rmharness import pool, Study            # noqa: E402
from rmharness import bundle as _bundle      # noqa: E402
from rmharness import verify as _verify      # noqa: E402


def _have_node():
    return shutil.which("node") is not None


FINERENONE = [
    Study("FIDELIO", ai=367, n1=2833, ci=420, n2=2841),
    Study("FIGARO", ai=458, n1=3686, ci=519, n2=3666),
    Study("FINEARTS", ai=624, n1=3003, ci=719, n2=2998),
]


@pytest.mark.skipif(not _have_node(), reason="node not available")
def test_python_reproduces_js_headline_exactly():
    """Two independent engines (browser JS + Python stdlib) must agree to <1e-9
    on the log-scale pooled estimate. This is the clean-room reproduction proof."""
    out = subprocess.run(["node", JS, CONFIG, "RR", "headline"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    js = json.loads(out.stdout)
    py = pool(FINERENONE, measure="RR", method="REML")
    assert abs(py["estimate_log"] - js["estimate_log"]) < 1e-9
    assert abs(py["se"] - js["se"]) < 1e-9
    assert abs(py["tau2"] - js["tau2"]) < 1e-9
    assert abs(py["Q"] - js["Q"]) < 1e-9
    assert abs(py["estimate_ratio"] - js["estimate_ratio"]) < 1e-9


def test_known_finerenone_value():
    """Guard the headline number against silent drift (no node needed)."""
    r = pool(FINERENONE, measure="RR", method="REML")
    assert round(r["estimate_ratio"], 4) == 0.8722
    assert r["tau2"] == 0.0
    assert r["I2_percent"] == 0.0


def test_reproduce_passes_on_good_bundle(built_bundle):
    b, _ = built_bundle
    r = _verify.reproduce(b)
    assert r["passed"] is True


def test_reproduce_FAILS_on_tampered_reference(built_bundle):
    """If the app's stored number is wrong, `reproduce` must catch it. This is
    the whole point of the harness: it can prove us wrong."""
    b, _ = built_bundle
    tampered = copy.deepcopy(b)
    # pretend the app displayed a rosier RR than the data supports
    tampered["reference"]["estimate_log"] = -0.30    # RR ~0.74 instead of 0.87
    tampered["reference"]["estimate_ratio"] = 0.74
    r = _verify.reproduce(tampered)
    assert r["passed"] is False
    assert r["diffs"]["estimate_ratio"]["match"] is False


def test_reproduce_FAILS_on_tampered_count(built_bundle):
    """If a trial's count is silently changed, the recomputed pool no longer
    matches the frozen reference."""
    b, _ = built_bundle
    tampered = copy.deepcopy(b)
    tampered["trials"][0]["tE"] = 200            # was 367
    r = _verify.reproduce(tampered)
    assert r["passed"] is False
