"""Synthesis — refuse binary-vs-continuous effect-selection ambiguity per trial.

Node executes all distributed JavaScript sources, with refusal/positive
controls. These tests are NOT an R-based NMA/SUCRA scientific oracle.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_refuses_mixed_within_trial_candidate_effects():
    result = subprocess.run(
        ["node", "tests/nma_sucra_mixed_within_trial_effects.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"SUCRA mixed-effect gate failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "60 source-executed OR/MD same-study" in result.stdout
