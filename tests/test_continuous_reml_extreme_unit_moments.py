"""Statistical-parity regression: REML Fisher scoring must be invariant to MD units.

This executes the three distributed *production* JS engines in Node. Data are
deliberately SYNTHETIC, not clinical, and scale invariance is a mathematical
property rather than an independent R/metafor oracle. The separate pinned
metafor-tests CI remains responsible for external method-matched comparisons.
"""
import json
import math
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
const source = fs.readFileSync(process.argv[1], 'utf8');
const marker = '  global.ContinuousOutcome = { render };';
if (source.split(marker).length !== 2) throw Error('production engine export changed');
const sandbox = {};
vm.runInNewContext(
  source.replace(marker, '  global.__remLInspection = { poolRE };\n' + marker),
  sandbox, { filename: process.argv[1] });
if (!sandbox.__remLInspection) throw Error('production engine uninspectable');
const points = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = sandbox.__remLInspection.poolRE(points);
console.log(JSON.stringify({ result }));
"""


def pool(engine, points):
    cp = subprocess.run(
        ["node", "-e", NODE, str(engine)],
        input=json.dumps(points),
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    if cp.returncode != 0:
        raise AssertionError(cp.stderr + "\n" + cp.stdout)
    return json.loads(cp.stdout)["result"]


def scale_points(unit_scale):
    return [
        {"yi": yi * unit_scale, "vi": vi * unit_scale * unit_scale}
        for yi, vi in ((0, .5), (2, 1), (4, 4), (9, 6))
    ]


class REMLNormalizedFisherMoments(unittest.TestCase):
    def test_extreme_unit_rescaling_cannot_masquerade_as_reml(self):
        """Previously finite, incorrect DL-start estimates were returned as REML.

        The rescaled estimates must not silently become tau2=6.5253 or zero;
        10.1302819 is an *internal* baseline, not a reported R reference.
        """
        for engine in ENGINES:
            base = pool(engine, scale_points(1))
            self.assertIsNotNone(base)
            self.assertGreater(base["tau2"], 10)
            for scale in (1e-40, 1e-100, 1e100):
                with self.subTest(engine=engine.name, scale=scale):
                    result = pool(engine, scale_points(scale))
                    self.assertIsNotNone(result)
                    self.assertEqual(result["k"], base["k"])
                    self.assertTrue(math.isclose(
                        result["tau2"] / (scale * scale),
                        base["tau2"], rel_tol=1e-8, abs_tol=0,
                    ), (engine, scale, base["tau2"], result["tau2"]))
                    for field in ("yi", "se", "ci_low", "ci_high",
                                  "pi_low", "pi_high"):
                        self.assertTrue(math.isclose(
                            result[field] / scale, base[field],
                            rel_tol=1e-8, abs_tol=0,
                        ), (engine, scale, field, result[field]))
                    for field in ("Q", "I2"):
                        self.assertTrue(math.isclose(
                            result[field], base[field], rel_tol=1e-8, abs_tol=0,
                        ), (engine, scale, field, result[field]))

    def test_unrepresentable_or_invalid_weights_refuse_entire_pool(self):
        for engine in ENGINES:
            cases = [
                scale_points(1e-160),  # finite input variance; 1/vi overflows
                [dict(p, vi=0) if i == 0 else p
                 for i, p in enumerate(scale_points(1))],
                [dict(p, vi=-1) if i == 0 else p
                 for i, p in enumerate(scale_points(1))],
            ]
            for i, points in enumerate(cases):
                with self.subTest(engine=engine.name, case=i):
                    self.assertIsNone(pool(engine, points))

    def test_distributed_js_sources_stay_identical(self):
        self.assertEqual(len({p.read_bytes() for p in ENGINES}), 1)


if __name__ == "__main__":
    unittest.main()
