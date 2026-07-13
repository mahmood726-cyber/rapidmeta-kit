"""add / remove / re-measure / bundle schema + CLI exit codes."""
import json
import os
import subprocess
import sys

import pytest

from rmharness import verify as _verify
from rmharness import bundle as _bundle

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)
BUNDLE = os.path.join(os.path.dirname(HARNESS), "bundle-example", "finerenone_ckd", "bundle.json")


def test_add_trial_moves_estimate(built_bundle):
    b, _ = built_bundle
    r = _verify.add_trial(b, {"name": "X", "tE": 10, "tN": 500, "cE": 40, "cN": 500})
    assert r["after"]["k"] == r["before"]["k"] + 1
    # a strongly protective added trial pulls the pooled ratio down
    assert r["after"]["estimate_ratio"] < r["before"]["estimate_ratio"]


def test_remove_trial_moves_estimate(built_bundle):
    b, _ = built_bundle
    r = _verify.remove_trial(b, "FINEARTS")
    assert r["after"]["k"] == r["before"]["k"] - 1


def test_add_by_hazard_ratio(built_bundle):
    b, _ = built_bundle
    r = _verify.add_trial(b, {"name": "HR-trial", "publishedHR": 0.7, "hrLCI": 0.55, "hrUCI": 0.9})
    assert r["after"]["k"] == 4


def test_remeasure_or_rd(built_bundle):
    b, _ = built_bundle
    ror = _verify.remeasure(b, "OR")
    assert ror["after"]["estimate_ratio"] is not None
    rrd = _verify.remeasure(b, "RD")
    # RD is difference-scale: no back-transformed ratio, estimate near a small number
    assert rrd["after"]["estimate_ratio"] is None
    assert abs(rrd["after"]["estimate_log"]) < 0.1


def test_bundle_schema_required_keys(built_bundle):
    b, _ = built_bundle
    for k in ("schema", "measure", "trials", "reference", "protocol", "git_commit"):
        assert k in b
    assert b["schema"] == "rapidmeta-bundle/v1"


def test_cli_reproduce_exit_zero():
    out = subprocess.run([sys.executable, "-m", "rmharness", "reproduce", BUNDLE],
                         capture_output=True, text=True, cwd=HARNESS)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "PASS" in out.stdout


def test_cli_gates_exit_zero():
    out = subprocess.run([sys.executable, "-m", "rmharness", "gates", BUNDLE],
                         capture_output=True, text=True, cwd=HARNESS)
    assert out.returncode == 0, out.stdout + out.stderr
