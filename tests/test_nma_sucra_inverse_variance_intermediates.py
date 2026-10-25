"""Synthesis | Hourly Statistical Parity: refuse non-finite DL pooled intermediates.

Cochrane Handbook chapter 10.3: study weights use reciprocal within-study variance.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10

These are synthetic refusal/positive controls, not native R/metafor validation.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_inverse_variance_intermediate_refusal():
    proc = subprocess.run(
        ["node", "tests/nma_sucra_inverse_variance_intermediates.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert proc.returncode == 0, (
        f"Node DL intermediate refusal gate failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "60 source-executed SUCRA inverse-variance intermediate guard scenarios" in proc.stdout
