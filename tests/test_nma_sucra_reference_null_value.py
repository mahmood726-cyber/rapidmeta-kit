"""Reference-row null effect must follow its measure (MD=0, OR=1).

The Node test executes the actual browser source with synthetic inputs.
It is not a clinical data check or version-pinned external R oracle.
Cochrane Handbook chapter 6 section 6.1.2:
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_sucra_reference_null_matches_effect_measure():
    result = subprocess.run(
        ["node", "tests/nma_sucra_reference_null_value.cjs"],
        cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, (
        f"Node source regression failed ({result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "12 source-executed SUCRA reference-null-value scenarios" in result.stdout
