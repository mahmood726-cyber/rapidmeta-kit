"""Synthesis — refuse duplicate/malformed treatment categories before SUCRA.

Runs the shipped JS in Node V8. Does not establish R/NMA oracle parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_requires_unique_named_treatments():
    result = subprocess.run(
        ["node", "tests/nma_sucra_unique_treatment_labels.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"SUCRA treatment-identity gate failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "72 source-executed treatment-label" in result.stdout
