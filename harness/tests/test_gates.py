"""Gates pass on an honest bundle and CATCH tampering / divergence."""
import copy
import os
import subprocess
import sys

import pytest

from rmharness import verify as _verify
from rmharness import gates as _gates
from rmharness import bundle as _bundle
from rmharness import pool, Study

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)


def test_all_gates_pass(built_bundle):
    b, bdir = built_bundle
    r = _verify.run_gates(b, bdir)
    assert r["passed"] is True
    assert r["protocol_hash"]["ok"] is True


def test_protocol_hash_catches_edited_question(built_bundle, tmp_path):
    """Edit protocol.md by one character -> the pre-registration hash no longer
    matches."""
    b, bdir = built_bundle
    # copy protocol to tmp, tamper, point bundle_dir there
    import shutil
    shutil.copytree(bdir, tmp_path / "bundle")
    proto = tmp_path / "bundle" / "protocol.md"
    proto.write_text(proto.read_text(encoding="utf-8") + "\n(tampered)\n", encoding="utf-8")
    ok, computed, expected = _bundle.verify_protocol_hash(b, str(tmp_path / "bundle"))
    assert ok is False


def test_counts_imply_effect_catches_wrong_displayed_ratio(built_bundle):
    b, _ = built_bundle
    t = copy.deepcopy(b["trials"])
    # claim a displayed per-trial RR that the counts do NOT support
    t[0]["displayedRatio"] = 0.50   # real is ~0.876
    rep = _gates.counts_imply_effect(t, "RR")
    assert rep.ok is False
    assert any("counts_imply_effect" in c.name and not c.ok for c in rep.checks)


def test_plausibility_flags_divergent_pm(built_bundle):
    """The app's PM sensitivity path diverges (runaway tau2 -> absurd CI). The
    plausibility gate must reject that number even though the point estimate
    looks fine."""
    b, bdir = built_bundle
    table = _verify._load_table(b, bdir)
    # reproduce the PM divergence with the harness's own PM on this homogeneous data
    studies = _bundle.studies(b, "RR")
    pm = pool(studies, measure="RR", method="PM")
    # sanity: PM here should behave (harness PM clamps correctly) -> construct the
    # pathological result the JS PM path produces to prove the gate would catch it.
    bad = dict(pm)
    bad["se"] = 43799.0
    bad["ci_ratio"] = [1e-30, 1e30]
    bad["estimate_ratio"] = 0.87
    rep = _gates.plausibility_check(bad, "RR", table)
    assert rep.ok is False
    names = {c.name for c in rep.failures}
    assert "ci_width_sane" in names or "se_sane" in names


def test_harness_pm_clamps_where_app_diverges(built_bundle):
    """Independent check that the harness's PM does NOT diverge on the same data
    the app's PM path blows up on (Q < k-1) -> tau2 clamps to 0."""
    b, _ = built_bundle
    studies = _bundle.studies(b, "RR")
    pm = pool(studies, measure="RR", method="PM")
    assert pm["tau2"] == 0.0
    assert pm["se"] < 1.0
