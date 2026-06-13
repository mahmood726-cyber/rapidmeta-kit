"""Panel-mount smoke test: drives each advanced-technique panel's render()
through a minimal DOM stub (tests/dom_smoke.cjs) to prove the full
getRealData -> extractBinaryTrials -> engine -> buildCollapsiblePanel ->
insertAfterRBadge path runs without a runtime DOM error. node --check only
proves the files parse; this proves they mount.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = Path(__file__).resolve().parent / "dom_smoke.cjs"


def test_advanced_panels_mount():
    result = subprocess.run(
        ["node", str(HARNESS)],
        capture_output=True, text=True, timeout=60, check=False, cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"panel mount smoke failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "SMOKE OK" in result.stdout, f"unexpected output:\n{result.stdout}"
