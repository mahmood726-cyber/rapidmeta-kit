"""Run actual JS engine/panel negative source-integrity cases in all three copies.

These are synthetic input/refusal tests. They do NOT establish native R parity.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_summary_hr_nnt_fails_closed_in_every_shipped_copy():
    completed = subprocess.run(
        ["node", str(ROOT / "tests/summary_hr_nnt_source_integrity.cjs")],
        cwd=ROOT, text=True, capture_output=True, timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "SOURCE GUARD PASS" in completed.stdout
