"""Synthesis: reject unverified direction inferred from survival/mixed outcome labels.

This is a source-executed JS UI safeguard, not method-matched R validation.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_ambiguous_survival_and_mixed_polarity_directions():
    result = subprocess.run(
        ["node", "tests/nma_sucra_ambiguous_direction.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"SUCRA outcome direction guard failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "48 source-executed survival/mixed-direction" in result.stdout
