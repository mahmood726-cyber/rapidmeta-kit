"""R-parity validation tests for the RapidMeta inline meta-analysis engine.

The MA math lives inline in ``template/base_dupilumab_copd.html``. It is ported
VERBATIM into ``tests/r_parity_harness.cjs`` (a Node harness); this test runs
that harness and checks the outputs two ways:

  (a) REGRESSION: outputs match the committed baseline JSON
      (``tests/baselines/ma_core_baseline.json``) to a tight 1e-9 tolerance.
  (b) ANCHOR PARITY: the BCG random-effects/REML log-RR quantities fall within
      stated tolerances of (i) the documented metafor published values
      (Viechtbauer 2010 JSS, dat.bcg), and (ii) an independent in-environment
      scipy re-derivation; and the fixed-effect case matches its exact by-hand
      closed form.

R / Rscript is NOT installed in this environment, so the metafor values are
literature anchors (cited), and the scipy re-derivation is an independent
implementation cross-check -- NOT metafor itself. See docs/VALIDATION_DOSSIER.md
for the honesty ledger of what is independently anchored vs baseline-only.

Tolerances:
  * REGRESSION (engine vs committed baseline): 1e-9  -- same code, deterministic.
  * Pooled logRR / SE / CI vs metafor-published: 1e-3  -- the published values are
    rounded to 4 dp, so 1e-3 is the resolution of the anchor itself.
  * tau2 (REML) vs metafor-published: 1e-3 -- REML is iterative; published to 4 dp.
  * Q vs published: 0.05 ; I2(%) vs published: 0.1 -- published to 1 dp.
  * BCG quantities vs scipy-rederived (full precision): 1e-6 -- two independent
    implementations of the same estimator should agree to well below this.
  * Fixed-effect exact vs by-hand: 1e-12 -- closed form, no iteration.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS = REPO_ROOT / "tests" / "r_parity_harness.cjs"
BASELINE = REPO_ROOT / "tests" / "baselines" / "ma_core_baseline.json"

REGRESSION_TOL = 1e-9


@pytest.fixture(scope="module")
def engine_out() -> dict:
    """Run the Node harness and return its parsed JSON (the live engine output)."""
    result = subprocess.run(
        ["node", str(HARNESS)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"node exited {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    last = [ln for ln in result.stdout.splitlines() if ln.strip()][-1]
    return json.loads(last)


@pytest.fixture(scope="module")
def baseline() -> dict:
    return json.loads(BASELINE.read_text())


# --------------------------------------------------------------------------- #
# (a) REGRESSION: engine output == committed baseline (tight)                  #
# --------------------------------------------------------------------------- #

def _flatten(prefix, obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}", v, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _flatten(f"{prefix}[{i}]", v, out)
    else:
        out[prefix] = obj


def test_engine_matches_baseline_regression(engine_out, baseline):
    """Every numeric in the live engine output matches the committed baseline."""
    live, base = {}, {}
    _flatten("", engine_out, live)
    _flatten("", baseline["engine_outputs"], base)
    assert set(live) == set(base), (
        f"key drift:\n only-live: {set(live)-set(base)}\n only-base: {set(base)-set(live)}"
    )
    mismatches = []
    for k, bv in base.items():
        lv = live[k]
        if isinstance(bv, (int, float)) and isinstance(lv, (int, float)):
            if not math.isclose(lv, bv, rel_tol=0, abs_tol=REGRESSION_TOL):
                mismatches.append((k, lv, bv))
        else:
            if lv != bv:
                mismatches.append((k, lv, bv))
    assert not mismatches, "engine drifted from baseline:\n" + "\n".join(
        f"  {k}: live={lv} base={bv}" for k, lv, bv in mismatches
    )


# --------------------------------------------------------------------------- #
# (b) ANCHOR PARITY: BCG vs metafor-published (Viechtbauer 2010 JSS)           #
# --------------------------------------------------------------------------- #

def test_bcg_vs_metafor_published(engine_out, baseline):
    b = engine_out["bcg"]
    anc = baseline["external_anchors"]["bcg_metafor_published"]
    checks = [
        ("pooled_logRR", b["pooled_logRR"], anc["pooled_logRR"], 1e-3),
        ("pooled_SE",    b["pooled_SE"],    anc["pooled_SE"],    1e-3),
        ("ci_lo_logRR",  b["ci_lo_logRR"],  anc["ci_lo_logRR"],  1e-3),
        ("ci_hi_logRR",  b["ci_hi_logRR"],  anc["ci_hi_logRR"],  1e-3),
        ("tau2_reml",    b["tau2_reml"],    anc["tau2_reml"],    1e-3),
        ("I2",           b["I2"],           anc["I2_pct"],       0.1),
        ("Q",            b["Q"],            anc["Q"],            0.05),
    ]
    fails = [(n, e, r, t) for (n, e, r, t) in checks if abs(e - r) > t]
    assert not fails, "BCG disagrees with metafor-published anchor:\n" + "\n".join(
        f"  {n}: engine={e:.6f} ref={r} |diff|={abs(e-r):.2e} tol={t}" for n, e, r, t in fails
    )
    assert b["df"] == anc["df"]


def test_bcg_vs_scipy_rederived(engine_out, baseline):
    """Independent implementation cross-check (Python+scipy), full precision."""
    b = engine_out["bcg"]
    anc = baseline["external_anchors"]["bcg_scipy_rederived"]
    tol = 1e-6
    checks = [
        ("pooled_logRR", b["pooled_logRR"], anc["pooled_logRR"]),
        ("pooled_SE",    b["pooled_SE"],    anc["pooled_SE"]),
        ("ci_lo_logRR",  b["ci_lo_logRR"],  anc["ci_lo_logRR"]),
        ("ci_hi_logRR",  b["ci_hi_logRR"],  anc["ci_hi_logRR"]),
        ("tau2_reml",    b["tau2_reml"],    anc["tau2_reml"]),
        ("Q",            b["Q"],            anc["Q"]),
        ("I2",           b["I2"],           anc["I2_pct"]),
    ]
    fails = [(n, e, r) for (n, e, r) in checks if abs(e - r) > tol]
    assert not fails, "BCG disagrees with independent scipy re-derivation:\n" + "\n".join(
        f"  {n}: engine={e:.10f} ref={r} |diff|={abs(e-r):.2e}" for n, e, r in fails
    )


# --------------------------------------------------------------------------- #
# (c) EXACT-BY-HAND: fixed-effect inverse-variance pool                        #
# --------------------------------------------------------------------------- #

def test_fixed_effect_exact_by_hand(engine_out):
    """FE IV pool of y=[.2,.4,.6], v=[.04,.01,.04] is exact by hand:
       mu=0.4, se=sqrt(1/150), Q=2, sumW=150."""
    fe = engine_out["fixed_effect_exact"]
    assert abs(fe["mu"] - 0.4) < 1e-12
    assert abs(fe["se"] - math.sqrt(1.0 / 150.0)) < 1e-12
    assert abs(fe["Q"] - 2.0) < 1e-12
    assert abs(fe["sumW"] - 150.0) < 1e-12


def test_baseline_schema(baseline):
    assert baseline["schema_version"]
    assert baseline["generated_against_commit"] == "WORKDIR"
    assert "bcg" in baseline["datasets"]
    assert "bcg_metafor_published" in baseline["external_anchors"]
