"""Fail-closed double-zero/double-all relative-OR ranking regression (Cochrane Ch 10).

JavaScript execution is an engineering safeguard, not an independent R oracle.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_no_artificial_relative_or_from_double_zero_or_double_all_studies():
    result = subprocess.run(
        ["node", "tests/nma_sucra_uninformative_binary_or.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"SUCRA rare-event refusal regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "78 source-executed double-zero/double-all OR" in result.stdout
