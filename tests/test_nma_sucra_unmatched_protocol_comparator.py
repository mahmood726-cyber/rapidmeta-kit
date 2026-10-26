"""Synthesis | Hourly Statistical Parity — protocol comparator integrity gate.
Cochrane Handbook Ch. 3 defines prospective intervention/comparator grouping:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-03
These browser source tests do not establish method-matched native R parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_protocol_reference_fails_closed_on_unmatched_comparator():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_unmatched_protocol_comparator.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Protocol comparator regression failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "78 source-executed protocol comparator identification cases" in proc.stdout
