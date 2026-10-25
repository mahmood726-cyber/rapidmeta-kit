"""Synthesis | Hourly Statistical Parity: malformed typed MD/SE gate.

Cochrane Handbook 10.3: generic inverse-variance models use 1/SE^2 weights.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10

Tests are synthetic refusal/positive controls, not native R/metafor parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_continuous_numeric_gate():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_continuous_numeric_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Node continuous input refusal gate failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "63 source-executed SUCRA continuous-numeric scenarios" in proc.stdout
