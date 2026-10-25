"""Synthesis statistical correctness: reject ambiguous multiple MD effects.

Cochrane Handbook ch. 10: outcome and effect-measure choice must be
consistent before inverse-variance synthesis.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
Synthetic browser refusal checks; no clinical source validation or R parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_multiple_continuous_effect_rows_fail_closed():
    result = subprocess.run(
        ["node", "tests/nma_sucra_multiple_continuous_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"SUCRA multiple-outcome gate failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "54 source-executed SUCRA multiple-continuous-outcome cases" in result.stdout
