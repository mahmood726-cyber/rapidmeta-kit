"""Synthesis statistical parity: guard against unsupported SUCRA winner claims.

Method source: Wigle et al., Statistics in Medicine 2025,
https://doi.org/10.1002/sim.70176 (POTH bounded between 0 and 1).

Node/V8 UI behaviour checks are not independent, method-matched R parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_requires_valid_poth_before_naming_top_treatment():
    result = subprocess.run(
        ["node", "tests/nma_sucra_poth_validity_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"POTH validity regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "72 source-executed POTH-validity regression/negative scenarios" in result.stdout
