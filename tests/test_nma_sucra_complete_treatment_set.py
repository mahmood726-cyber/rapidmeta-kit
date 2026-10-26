"""Synthesis | Hourly Statistical Parity — completeness of configured ranking set.

Source-backed rationale: Cochrane Handbook Chapter 11 §§11.4.3.3, 11.6.4.1:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-11

Synthetic browser behavior tests are not independent, method-matched R parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_refuses_unanalysable_configured_treatment_instead_of_silent_subset():
    result = subprocess.run(
        ["node", "tests/nma_sucra_complete_treatment_set.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"Complete-treatment-set regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "66 complete-treatment-set source-executed regression/negative scenarios" in result.stdout
