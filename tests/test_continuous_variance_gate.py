"""Fail closed when a supplied continuous effect has invalid SE².

Actual shipped JS is exercised through Node and a minimal UI harness.
Synthetic numerical stress cases only: not clinical evidence and not native R
or metafor numerical-estimate parity. Cochrane Handbook §10.3 requires a
well-defined inverse-variance weight (1/SE²) for every included study.
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = (
    "assets/vendor/continuous-outcome.js",
    "docs/assets/vendor/continuous-outcome.js",
    "template/assets/vendor/continuous-outcome.js",
)
JS = r"""
require('./' + process.argv[1]); // No document yet: prevents auto-bootstrap.
const rows = JSON.parse(process.argv[2]);
let captured = null;
globalThis.PanelHelper = {
  getRealData: () => rows,
  fmt: (x, n) => Number(x).toFixed(n === undefined ? 2 : n),
  buildCollapsiblePanel: (opts) => (captured = opts, opts),
  insertAfterRBadge: () => {}
};
globalThis.document = { getElementById: () => null };
const rendered = globalThis.ContinuousOutcome.render();
console.log(JSON.stringify({
  rendered, badge: captured && captured.badge,
  summary: captured && captured.summary,
  bodyHtml: captured && captured.bodyHtml
}));
"""


def run_panel(copy, rows):
    data = {f"trial_{i}": dict(name=f"Synthetic {i}", **row)
            for i, row in enumerate(rows, start=1)}
    cp = subprocess.run(
        ["node", "-e", JS, copy, json.dumps(data)],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(cp.stdout)


GOOD_MD = ({"md": 1.0, "md_se": 0.1},
           {"md": 2.0, "md_se": 0.2})
GOOD_SMD = ({"smd": 0.1, "smd_se": 0.1},
            {"smd": 0.2, "smd_se": 0.2})


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("label,rows,effect", (
    ("md_se_overflow", GOOD_MD + ({"md": 3.0, "md_se": 1e300},), "MD"),
    ("md_se_underflow", GOOD_MD + ({"md": 3.0, "md_se": 1e-300},), "MD"),
    ("md_se_zero", GOOD_MD + ({"md": 3.0, "md_se": 0.0},), "MD"),
    ("smd_se_overflow", GOOD_SMD + ({"smd": 0.3, "smd_se": 1e300},), "SMD"),
    ("raw_sd_overflow", (
        {"mean1": 1, "mean2": 2, "sd1": 1, "sd2": 1, "n1": 80, "n2": 80},
        {"mean1": 2, "mean2": 1, "sd1": 2, "sd2": 2, "n1": 90, "n2": 90},
        {"mean1": 2, "mean2": 1, "sd1": 1e300, "sd2": 2, "n1": 90, "n2": 90},
    ), "MD"),
))
def test_bad_continuous_variance_refuses_whole_panel(copy, label, rows, effect):
    result = run_panel(copy, rows)
    assert result["rendered"] is True, label
    assert result["badge"] == "Continuous · REFUSED", label
    assert f"unrepresentable {effect} effect or variance" in result["summary"]
    assert "trial 3" in result["summary"]
    assert "No continuous outcome pooled" in result["bodyHtml"]
    assert "Pooled MD" not in result["bodyHtml"]
    assert "Pooled SMD" not in result["bodyHtml"]


@pytest.mark.parametrize("copy", COPIES)
@pytest.mark.parametrize("rows,effect", (
    (GOOD_MD + ({"md": 1.5, "md_se": 0.3},), "MD"),
    (GOOD_SMD + ({"smd": 0.25, "smd_se": 0.3},), "SMD"),
))
def test_finite_positive_se_controls_still_pool(copy, rows, effect):
    result = run_panel(copy, rows)
    assert result["rendered"] is True
    assert result["badge"] == "Continuous"
    assert result["summary"].startswith(f"{effect} ")
    assert "k=3" in result["summary"]
    assert "REFUSED" not in result["summary"]


def test_three_shipped_continuous_engines_remain_identical():
    blobs = [(ROOT / path).read_bytes() for path in COPIES]
    assert blobs[0] == blobs[1] == blobs[2]
