"""Single-arm method-integrity regressions, not native-R parity tests."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_singlearm_r_badge_refuses_unmatched_methods():
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "singlearm_badge_contract.cjs")],
        cwd=ROOT, capture_output=True, text=True, timeout=45, check=False,
    )
    assert result.returncode == 0, (
        f"Node single-arm badge contract failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "no R" in result.stdout


def test_singlearm_vendor_mirrors_identical():
    for filename in ("r-validation-singlearm.js", "single-arm-proportion.js"):
        paths = [
            ROOT / prefix / "assets" / "vendor" / filename
            for prefix in ("", "docs", "template")
        ]
        assert paths[0].read_bytes() == paths[1].read_bytes() == paths[2].read_bytes(), filename
