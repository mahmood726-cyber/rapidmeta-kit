"""Synthesis | Hourly Statistical Parity: respect specified reference comparator.

The Cochrane Handbook chapter 11, section 11.4.1, describes selecting a
reference treatment for basic relative treatment effects:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-11

Synthetic browser-gate tests are NOT independent R statistical validation.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_explicit_comparator_priority():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_reference_priority.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Explicit comparator priority regression failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "42 source-executed explicit reference comparator scenarios" in proc.stdout
