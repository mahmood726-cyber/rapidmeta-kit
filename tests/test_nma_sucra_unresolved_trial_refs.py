"""Synthesis | Hourly Statistical Parity: unresolved direct-trial reference gate.

Cochrane Handbook chapter 10, section 10.12, describes handling and
reporting missing study outcome data:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10

These source-executed browser checks are not a fitted NMA or independent,
method-matched, version-pinned R oracle.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_unresolved_trial_references_refuse_silent_omission():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_unresolved_trial_refs.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Unresolved trial reference regression failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "60 source-executed unresolved-reference gate scenarios" in proc.stdout
