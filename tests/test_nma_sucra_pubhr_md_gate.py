"""Refuse mapping published hazard ratios to continuous mean differences.

Cochrane Handbook ch. 6: MD (difference) and HR (time-to-event ratio)
are different effect measures with different units and null effects.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06

Synthetic negative and positive UI gate tests, not native R/metafor parity.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_untyped_pubhr_md_gate():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_pubhr_md_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Node SUCRA untyped pubHR gate failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "24 source-executed pubHR/MD refusal scenarios" in proc.stdout
