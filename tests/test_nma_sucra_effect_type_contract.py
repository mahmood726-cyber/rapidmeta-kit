"""SUCRA effect-type gate: actual JavaScript panel, not an R/metafor oracle."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_nma_sucra_rejects_mixed_or_and_md_in_shipped_panels():
    result = subprocess.run(
        ["node", "tests/nma_sucra_effect_type_contract.cjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        f"Node contract failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "15 actual-panel scenarios" in result.stdout
