"""Refuse reused multi-arm references in independent SUCRA direct-pool rankings.

Cochrane Handbook 23.3.4: shared intervention arms imply correlated contrasts.
https://training.cochrane.org/handbook/current/chapter-23

Executes distributed browser JavaScript with synthetic negative and positive controls.
No clinical-effects changes, fitted NMA validation, or native R parity is claimed.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_shared_study_refusal():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_shared_study_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Node SUCRA shared-study gate failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "42 source-executed SUCRA shared-study refusal scenarios" in proc.stdout
