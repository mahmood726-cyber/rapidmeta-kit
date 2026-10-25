"""Regression for REML Fisher-information scale invariance.

The same four SYNTHETIC mean-difference studies expressed in 10,000-times
larger units must have 10**8-times larger tau². Exercise the actual shipped
production continuous engine, not a copied numerical implementation.
The external version-pinned metafor check lives in
metafor-tests/test_continuous_metafor_oracle.py.
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
if (source.split(marker).length !== 2) throw Error('unexpected engine export marker');
const instrumented = source.replace(
  marker, '  global.__scaleAudit = { poolRE };\n' + marker);
const sandbox = {};
vm.runInNewContext(instrumented, sandbox, { filename: process.argv[1] });
if (!sandbox.__scaleAudit) throw Error('production engine cannot be inspected');
const pool = sandbox.__scaleAudit.poolRE(JSON.parse(fs.readFileSync(0, 'utf8')));
if (!pool) throw Error('production pool was refused');
console.log(JSON.stringify(pool));
"""


def pool(engine, scale):
    points = [
        {"yi": yi * scale, "vi": vi * scale * scale}
        for yi, vi in ((0, 0.5), (2, 1), (4, 4), (9, 6))
    ]
    cp = subprocess.run(
        ["node", "-e", NODE, str(engine)], input=json.dumps(points),
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    if cp.returncode:
        raise AssertionError(cp.stderr + "\n" + cp.stdout)
    return json.loads(cp.stdout)


class ContinuousREMLScaleInvariance(unittest.TestCase):
    def test_units_cannot_force_dl_initial_guess_as_reml(self):
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                base, rescaled = pool(engine, 1), pool(engine, 10_000)
                self.assertGreater(base["tau2"], 8)
                self.assertEqual(base["k"], 4)
                self.assertEqual(rescaled["k"], 4)
                self.assertTrue(math.isclose(
                    base["tau2"], rescaled["tau2"] / 1e8,
                    rel_tol=0, abs_tol=1e-5,
                ))
                for field in ("yi", "se", "ci_low", "ci_high",
                              "pi_low", "pi_high"):
                    self.assertTrue(math.isclose(
                        base[field], rescaled[field] / 10_000,
                        rel_tol=0, abs_tol=1e-5,
                    ), (engine, field, base[field], rescaled[field]))
                self.assertAlmostEqual(base["Q"], rescaled["Q"], places=9)
                self.assertAlmostEqual(base["I2"], rescaled["I2"], places=9)

    def test_small_units_cannot_prematurely_accept_dl_as_reml(self):
        """A fixed absolute tau2-step tolerance is not invariant to unit size.

        Four SYNTHETIC MD effects retain their original estimand after changing
        measurement units by 1e-3, 1e-6 or 1e-8. Before the correction, the
        1e-6 case stopped at the DL starting estimate rather than REML.
        """
        for engine in ENGINES:
            base = pool(engine, 1)
            self.assertGreater(base["tau2"], 10.0)
            for scale in (1e-3, 1e-6, 1e-8):
                with self.subTest(engine=str(engine.relative_to(ROOT)),
                                  units=scale):
                    smaller = pool(engine, scale)
                    self.assertEqual(smaller["k"], base["k"])
                    self.assertTrue(math.isclose(
                        smaller["tau2"] / scale**2, base["tau2"],
                        rel_tol=0, abs_tol=1e-5,
                    ), (engine, scale, base["tau2"], smaller["tau2"]))
                    for field in ("yi", "se", "ci_low", "ci_high",
                                  "pi_low", "pi_high"):
                        self.assertTrue(math.isclose(
                            smaller[field] / scale, base[field],
                            rel_tol=0, abs_tol=1e-5,
                        ), (engine, scale, field, base[field], smaller[field]))
                    self.assertAlmostEqual(base["Q"], smaller["Q"], places=8)
                    self.assertAlmostEqual(base["I2"], smaller["I2"], places=8)

    def test_engine_copies_remain_byte_identical(self):
        self.assertEqual(len({p.read_bytes() for p in ENGINES}), 1)


if __name__ == "__main__":
    unittest.main()
