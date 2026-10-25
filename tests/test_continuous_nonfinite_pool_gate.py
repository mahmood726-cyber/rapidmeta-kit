"""Regression: finite per-study MD/SMD inputs must not render nonfinite pools.

Exercises each shipped production continuous-outcome.js through its actual
render() entrypoint. Synthetic numerical stress inputs are NOT clinical
data, independent source verification, or external R-oracle parity.
"""
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINES = (
    ROOT / "assets/vendor/continuous-outcome.js",
    ROOT / "docs/assets/vendor/continuous-outcome.js",
    ROOT / "template/assets/vendor/continuous-outcome.js",
)

NODE = r"""
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
const realData = Object.fromEntries(rows.map((r, i) => [
  'trial_' + i,
  Object.assign({name: 'trial_' + i}, r.kind === 'SMD'
    ? {smd: r.effect, smd_se: r.se}
    : {md: r.effect, md_se: r.se})
]));
let panel = null;
const document = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
};
const sandbox = {
  document,
  PanelHelper: {
    getRealData() { return realData; },
    fmt(value, digits) { return Number(value).toFixed(digits); },
    buildCollapsiblePanel(spec) { panel = spec; return spec; },
    insertAfterRBadge() {},
  },
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox,
                   {filename: process.argv[1]});
if (!sandbox.ContinuousOutcome || !sandbox.ContinuousOutcome.render() || !panel) {
  throw new Error('production continuous panel did not render');
}
console.log(JSON.stringify({badge: panel.badge, summary: panel.summary,
                            bodyHtml: panel.bodyHtml}));
"""


def md(effect, se):
    return {"kind": "MD", "effect": effect, "se": se}


def smd(effect, se):
    return {"kind": "SMD", "effect": effect, "se": se}


def render_actual_engine(engine, rows):
    cp = subprocess.run(
        ["node", "-e", NODE, str(engine)],
        input=json.dumps(rows), capture_output=True, text=True,
        check=False, timeout=30, cwd=ROOT,
    )
    if cp.returncode:
        raise AssertionError(f"{engine} failed: {cp.stderr}\n{cp.stdout}")
    return json.loads(cp.stdout)


class ContinuousNonfinitePoolGate(unittest.TestCase):
    def assert_refused_on_every_engine(self, rows):
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                out = render_actual_engine(engine, rows)
                self.assertIn("REFUSED", out["badge"])
                self.assertIn("Pooling REFUSED", out["summary"])
                self.assertIn("No continuous outcome pooled", out["bodyHtml"])
                self.assertNotIn("NaN", out["summary"])
                self.assertNotIn("Infinity", out["summary"])

    def test_positive_finite_variances_with_infinite_inverse_weights_refuse(self):
        # se**2 is a finite positive subnormal, but 1/vi overflows.
        # Old shipped code rendered 'MD NaN [NaN–NaN]' as a successful pool.
        self.assert_refused_on_every_engine(
            [md(0.00, 5e-155), md(0.01, 5e-155), md(0.02, 5e-155)]
        )

    def test_finite_effects_with_overflowed_heterogeneity_refuse(self):
        # All study-level effects/variances are finite; Q overflows.
        self.assert_refused_on_every_engine(
            [md(1e308, 1), md(-1e308, 1), md(0, 1)]
        )

    def test_invalid_smd_pool_must_not_publish_valid_partial_md_pool(self):
        self.assert_refused_on_every_engine(
            [md(0, 0.1), md(0.1, 0.1),
             smd(1e308, 1), smd(-1e308, 1), smd(0, 1)]
        )

    def test_normal_finite_md_pool_still_succeeds(self):
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                out = render_actual_engine(
                    engine, [md(0, 0.1), md(0.1, 0.1), md(0.2, 0.1)]
                )
                self.assertEqual(out["badge"], "Continuous")
                self.assertIn("MD ", out["summary"])
                self.assertIn("k=3", out["summary"])
                self.assertNotIn("NaN", out["summary"])

    def test_shipped_engine_mirrors_are_identical(self):
        self.assertEqual(len(set(p.read_bytes() for p in ENGINES)), 1)


if __name__ == "__main__":
    unittest.main()
