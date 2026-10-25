"""Regression: an exhausted REML Fisher-scoring budget is NOT convergence.

Runs the actual three shipped continuous-outcome.js engines in Node with
synthetic observations. A separate independently coded REML-score identity is
a stationarity check, NOT a method-matched external R/metafor oracle. That
external comparison remains in metafor-tests/test_continuous_metafor_oracle.py.
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

# Synthetic effects/variances, generated for numerical stress only.
# The previous 100-step engine returned tau2~101.167775615 without satisfying
# its explicit step tolerance; the same algorithm converges in 149 iterations
# at tau2~101.167771290. Neither value is independently validated clinical data.
SLOW_POINTS = [
    {"yi": -23.69506916146681, "vi": 1026.6281692945447},
    {"yi": -25.290818625165976, "vi": 0.0000014526669199396929},
    {"yi": -9.399146532900982, "vi": 25034.73858158717},
    {"yi": -1.5174902954115743, "vi": 89.49321155156305},
    {"yi": -9.58377583754835, "vi": 185.27487369966116},
    {"yi": 0.7373897002018609, "vi": 211.61526380643554},
    {"yi": -11.223848126572978, "vi": 181.41737421515495},
]

NODE = r"""
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
let source = fs.readFileSync(process.argv[1], 'utf8');
const marker = '  global.ContinuousOutcome = { render };';
if (source.split(marker).length !== 2) throw Error('engine export changed');
const original = 'for (let it = 0; it < 200; it++) {';
if (source.split(original).length !== 2) throw Error('REML convergence guard changed');
if (process.argv[2] === 'exhaust') {
  // Negative failure injection: exercise the actual production loop and
  // refusal, but force its maximum number of iterations to ONE for this test.
  source = source.replace(original, 'for (let it = 0; it < 1; it++) {');
} else if (process.argv[2] !== 'normal') {
  throw Error('unknown failure-injection mode');
}
source = source.replace(marker, '  global.__remlAudit = { poolRE };\n' + marker);
const sandbox = {};
vm.runInNewContext(source, sandbox, { filename: process.argv[1] });
if (!sandbox.__remlAudit) throw Error('production engine inaccessible');
const points = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = sandbox.__remlAudit.poolRE(points);
console.log(JSON.stringify({ result }));
"""


def execute_production(engine, points, mode="normal"):
    result = subprocess.run(
        ["node", "-e", NODE, str(engine), mode],
        input=json.dumps(points), text=True, capture_output=True, check=False,
        timeout=30, cwd=ROOT,
    )
    if result.returncode:
        raise AssertionError(
            f"Node execution failed for {engine}: {result.stderr}\n{result.stdout}"
        )
    return json.loads(result.stdout)["result"]


def relative_reml_score(points, tau2):
    """Independent scalar REML Fisher-score identity at the proposed tau²."""
    weights = [1.0 / (row["vi"] + tau2) for row in points]
    total = sum(weights)
    mu = sum(w * row["yi"] for w, row in zip(weights, points)) / total
    sum_w2 = sum(w * w for w in weights)
    # At a converged positive REML estimate the score should vanish.
    y_p2_y = sum(w * w * (row["yi"] - mu) ** 2
                 for w, row in zip(weights, points))
    tr_p = total - sum_w2 / total
    return abs(y_p2_y - tr_p) / total


class REMLConvergenceRefusal(unittest.TestCase):
    def test_slow_fisher_scoring_must_reach_stationary_tau2(self):
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                pool = execute_production(engine, SLOW_POINTS)
                self.assertIsNotNone(pool)
                self.assertEqual(pool["k"], len(SLOW_POINTS))
                self.assertGreater(pool["tau2"], 0)
                self.assertAlmostEqual(pool["tau2"], 101.16777129, delta=1e-6)
                self.assertLess(relative_reml_score(
                    SLOW_POINTS, pool["tau2"]), 1e-9)
                self.assertTrue(all(math.isfinite(pool[key]) for key in (
                    "yi", "se", "ci_low", "ci_high", "pi_low",
                    "pi_high", "tau2", "Q", "I2")))

    def test_exhausted_iteration_budget_refuses_complete_pool(self):
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                self.assertIsNone(execute_production(
                    engine, SLOW_POINTS, mode="exhaust"))
                self.assertIsNotNone(execute_production(
                    engine, SLOW_POINTS, mode="normal"))

    def test_regular_case_still_synthesizes_and_invalid_variance_refuses(self):
        normal = [
            {"yi": 0, "vi": .5}, {"yi": 2, "vi": 1},
            {"yi": 4, "vi": 4}, {"yi": 9, "vi": 6},
        ]
        bad = [*normal[:-1], {"yi": 9, "vi": 0}]
        for engine in ENGINES:
            with self.subTest(engine=str(engine.relative_to(ROOT))):
                self.assertIsNotNone(execute_production(engine, normal))
                self.assertIsNone(execute_production(engine, bad))

    def test_distributed_engines_are_byte_identical(self):
        self.assertEqual(len({path.read_bytes() for path in ENGINES}), 1)


if __name__ == "__main__":
    unittest.main()
