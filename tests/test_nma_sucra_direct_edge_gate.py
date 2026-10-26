"""Network ranking must not ignore non-reference comparisons.

Runs actual distributed JavaScript using Node. Synthetic structural fixtures
are not independent R/metafor parity or clinical evidence validation.
Methodology: Cochrane Handbook chapter 11 (network estimates use direct
and indirect evidence across the connected intervention network).
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_refuses_unmodelled_network_edges_in_shipped_engines():
    result = subprocess.run(
        ["node", "tests/nma_sucra_direct_edge_gate.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"Node source regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "21 actual SUCRA-panel scenarios" in result.stdout
