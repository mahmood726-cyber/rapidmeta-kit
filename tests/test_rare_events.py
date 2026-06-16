"""Regression tests for the rare-event binomial-normal GLMM engine.

These guard two bugs that the pre-existing suite missed because it only asserted
the *sign/finiteness* of the pooled OR, never the between-study variance:

  1. Gauss-Hermite quadrature was missing the u = √2 z change of variable, so
     the random effect was integrated against N(0, τ²/2) instead of N(0, τ²) —
     reported τ² came out ~2× inflated. (rare-events-glmm.js _logL_study /
     _logL_study_uncond)

  2. The (θ, log τ) damped-Newton optimiser stalled near the τ seed on
     heterogeneous data, reporting τ² ≈ seed² instead of the MLE.

Engine loaded via node from template/assets/vendor (the clone source tree).
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _node(snippet):
    result = subprocess.run(
        ["node", "-e", snippet],
        capture_output=True, text=True, timeout=60, check=False, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"node exited {result.returncode}\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert lines, f"node printed nothing.\nSTDERR:\n{result.stderr}"
    return json.loads(lines[-1])


def test_ghq_integrates_against_n0_tau2_not_half():
    """Bug #1 guard: the per-study GHQ marginal must equal a fine numerical
    integral of the binomial likelihood against N(0, τ²) — NOT N(0, τ²/2).

    Without the √2 scaling the GHQ error vs the truth is ~9.5e-2; with it the
    error is ~7e-3 (10-point quadrature). A tolerance of 0.02 cleanly separates
    the fixed engine from the bug.
    """
    out = _node(r"""
        const M = require('./template/assets/vendor/rare-events-glmm.js');
        const eT=5,nT=200,eC=12,nC=200,theta=-0.4,tau=0.7;
        const mu = Math.log(eC/(nC-eC));
        const llC = M._logBin(eC,nC,mu);
        let I=0; const dz=0.0005;
        for (let z=-8; z<=8; z+=dz) {
          const phi = Math.exp(-z*z/2)/Math.sqrt(2*Math.PI);
          I += Math.exp(M._logBin(eT,nT,mu+theta+tau*z))*phi*dz;
        }
        const truth = Math.log(I) + llC;                      // integrates N(0,τ²)
        const ghq = M._logL_total(
          [{events_T:eT,n_T:nT,events_C:eC,n_C:nC}], theta, tau);
        // What the bug would have produced: N(0, τ²/2) == fine integral at τ/√2.
        let J=0;
        for (let z=-8; z<=8; z+=dz) {
          const phi = Math.exp(-z*z/2)/Math.sqrt(2*Math.PI);
          J += Math.exp(M._logBin(eT,nT,mu+theta+(tau/Math.SQRT2)*z))*phi*dz;
        }
        const broken = Math.log(J) + llC;
        console.log(JSON.stringify({
          fixedDiff: Math.abs(truth-ghq), brokenDiff: Math.abs(truth-broken)}));
    """)
    assert out["fixedDiff"] < 0.02, f"GHQ marginal off by {out['fixedDiff']}"
    # Sanity: the bug really would have failed this tolerance (regression intent).
    assert out["brokenDiff"] > 0.05


def test_fit_recovers_heterogeneity():
    """Bug #2 guard: on clearly heterogeneous data the fitter must report a
    substantial τ², not the stalled τ²≈seed²≈0.01 the old Newton returned.

    The CM.AL grid MLE for this set is θ≈-0.6, τ²≈0.9.
    """
    out = _node(r"""
        const M = require('./template/assets/vendor/rare-events-glmm.js');
        const rows=[
         {events_T:4, n_T:200,events_C:18,n_C:200},
         {events_T:6, n_T:200,events_C:20,n_C:200},
         {events_T:22,n_T:200,events_C:10,n_C:200},
         {events_T:25,n_T:200,events_C:12,n_C:200},
         {events_T:14,n_T:200,events_C:14,n_C:200},
         {events_T:9, n_T:200,events_C:16,n_C:200},
        ];
        const c = M.fit(rows);
        console.log(JSON.stringify({theta:c.theta, tau2:c.tau2, ok:c.ok}));
    """)
    assert out["ok"] is True
    assert out["tau2"] > 0.5, f"fitter stalled: τ²={out['tau2']}"
    assert out["tau2"] < 1.5
    assert -1.0 < out["theta"] < -0.2


def test_fit_matches_exact_on_realistic_rare_data():
    """On realistic rare-event data (mild heterogeneity) the conditional
    approximation fit() and the exact CM.EL fit must agree closely on θ — a
    cross-check that needs no external oracle. Pre-fix, fit() disagreed because
    of the √2 inflation / optimiser stall.
    """
    out = _node(r"""
        const M = require('./template/assets/vendor/rare-events-glmm.js');
        const rows=[
         {events_T:5, n_T:500,events_C:11,n_C:500},
         {events_T:8, n_T:600,events_C:15,n_C:600},
         {events_T:3, n_T:400,events_C:9, n_C:400},
         {events_T:12,n_T:700,events_C:14,n_C:700},
         {events_T:6, n_T:450,events_C:13,n_C:450},
        ];
        const c = M.fit(rows), e = M.fitConditionalExact(rows);
        console.log(JSON.stringify({
          cTheta:c.theta, eTheta:e.theta, cTau2:c.tau2, eTau2:e.tau2}));
    """)
    assert abs(out["cTheta"] - out["eTheta"]) < 0.05
    assert out["cTau2"] < 0.05 and out["eTau2"] < 0.05  # homogeneous here


def test_fit_homogeneous_tau2_near_zero_and_direction():
    """Homogeneous protective data: τ²≈0 and OR<1 (treatment fewer events)."""
    out = _node(r"""
        const M = require('./template/assets/vendor/rare-events-glmm.js');
        const rows=[
         {events_T:3,n_T:200,events_C:8, n_C:200},
         {events_T:5,n_T:300,events_C:12,n_C:300},
         {events_T:2,n_T:150,events_C:4, n_C:150},
         {events_T:9,n_T:400,events_C:10,n_C:400},
         {events_T:1,n_T:120,events_C:6, n_C:120},
         {events_T:4,n_T:250,events_C:9, n_C:250},
        ];
        const c = M.fit(rows);
        console.log(JSON.stringify({tau2:c.tau2, OR:c.OR, se:c.se_theta}));
    """)
    assert out["tau2"] < 0.05
    assert 0.2 < out["OR"] < 1.0
    assert out["se"] > 0 and out["se"] < 1.0
