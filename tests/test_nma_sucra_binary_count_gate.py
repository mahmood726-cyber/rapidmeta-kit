"""Binary participant/event counts must be valid before the SUCRA OR computation.

Tests execute the actual distributed browser source with synthetic count fixtures.
These are engineering/refusal regressions, not native R/metafor parity or clinical
source verification. Cochrane Handbook ch. 6, §6.4.1–6.4.2:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_binary_counts_are_fail_closed():
    result = subprocess.run(
        ["node", "tests/nma_sucra_binary_count_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"Node source regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "90 source-executed SUCRA binary-count scenarios" in result.stdout
