"""LIVE external metafor 4.8-0 continuous MD/SMD oracle for shipped JS.

Runs production assets/vendor/continuous-outcome.js in Node without copying
or rewriting its algorithms. Uses R 4.4.3 and SHA256-pinned metafor 4.8-0
from the existing GitHub Actions oracle job. Data are SYNTHETIC numerical
domain examples, not clinical evidence or human independent adjudication.

Metafor escalc(measure='MD'/'SMD', vtype='LS', correct=TRUE) supplies
independent raw-arm study yi/vi; rma(method='REML', test='adhoc') supplies
the model-level REML plus floored Knapp-Hartung comparator. JS's approx
Hedges J and tabulated t-quantiles are declared approximation limits.
"""
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "assets" / "vendor" / "continuous-outcome.js"
R_ORACLE = ROOT / "oracle-tests" / "oracle_continuous_metafor.R"
COLS = ("mean1", "mean2", "sd1", "sd2", "n1", "n2")

DATASETS = {
    "near_homogeneous": (
        (12.0, 10.0, 3.0, 3.1, 40, 45),
        (11.6, 9.5, 2.8, 2.9, 50, 52),
        (14.0, 12.05, 3.6, 3.7, 65, 63),
        (10.8, 8.8, 2.7, 2.5, 75, 72),
    ),
    # Heteroscedastic boundary: qStar>1 with JS REML tau2=0 and R near 0. Under
    # metafor(test="adhoc"), PI and HKSJ CI must coincide exactly.
    "heteroscedastic_boundary": (
        (11.53, 10.0, 7.6, 7.6, 100, 100),
        (8.38, 10.0, 5.0, 5.0, 100, 100),
        (8.61, 10.0, 2.67, 2.67, 100, 100),
        (8.65, 10.0, 2.70, 2.70, 100, 100),
    ),
    "heterogeneous": (
        (20.0, 16.0, 3.5, 4.1, 55, 56),
        (17.0, 16.1, 3.0, 3.5, 60, 59),
        (18.5, 15.8, 4.2, 4.0, 70, 69),
        (19.0, 17.7, 3.8, 3.9, 85, 84),
    ),
}

# Inject a test-only function export into the freshly loaded, actual shipped
# source, without modifying the file or substituting a copied implementation.
NODE = r"""
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(process.argv[1], 'utf8');
const marker = '  global.ContinuousOutcome = { render };';
if (source.split(marker).length !== 2) throw Error('missing or duplicated JS export marker');
const instrumented = source.replace(marker,
  '  global.__liveMetafor = { pickContinuousTrials, md, smdHedges, poolRE };\n' + marker);
const sandbox = {};
vm.runInNewContext(instrumented, sandbox, { filename: process.argv[1] });
const oracle = sandbox.__liveMetafor;
if (!oracle) throw Error('cannot access production continuous methods');
const realData = Object.fromEntries(input.rows.map((r, i) => [
  'case_' + i, { name: 'case_' + i, mean1: r[0], mean2: r[1],
                sd1: r[2], sd2: r[3], n1: r[4], n2: r[5] }
]));
const trials = oracle.pickContinuousTrials(realData);
if (trials.length !== input.rows.length) throw Error('silent study omission');
const points = trials.map(t => input.measure === 'MD' ? oracle.md(t) : oracle.smdHedges(t));
if (points.some(p => !Number.isFinite(p.yi) || !Number.isFinite(p.vi) || !(p.vi > 0))) {
  throw Error('invalid continuous effect / variance, refuse pool');
}
const pool = oracle.poolRE(points);
if (!pool || pool.k !== points.length) throw Error('pool missing or incorrect k');
console.log(JSON.stringify({points, pool}));
"""


def run_js(rows, measure):
    cp = subprocess.run(
        ["node", "-e", NODE, str(JS)],
        input=json.dumps({"rows": rows, "measure": measure}),
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=45,
    )
    if cp.returncode:
        raise AssertionError("Node production continuous engine failed:\n"
                             + cp.stderr + "\n" + cp.stdout)
    return json.loads(cp.stdout)


def run_r(rows, measure):
    tab = "\t".join(COLS) + "\n"
    tab += "".join("\t".join(str(v) for v in row) + "\n" for row in rows)
    return subprocess.run(
        ["Rscript", "--vanilla", str(R_ORACLE), measure],
        input=tab, cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=90,
    )


def parse_r(output, n):
    result = {}
    required = {"k", "mu", "tau2", "se", "ci_low", "ci_high", "pi_low", "pi_high"}
    for i in range(n):
        required.update((f"study_{i}_yi", f"study_{i}_vi"))
    for line in output.strip().splitlines():
        tokens = line.split("\t")
        if len(tokens) != 2 or tokens[0] not in required or tokens[0] in result:
            raise AssertionError("unknown/duplicate/malformed live metafor field: " + line)
        try:
            result[tokens[0]] = float(tokens[1])
        except ValueError as exc:
            raise AssertionError("invalid live metafor number: " + line) from exc
        if not math.isfinite(result[tokens[0]]):
            raise AssertionError("nonfinite live metafor number: " + line)
    if result.keys() != required:
        raise AssertionError("incomplete live metafor results: " + str(required - result.keys()))
    return result


class ContinuousMetaforOracle(unittest.TestCase):
    def test_exact_r_and_metafor_versions(self):
        cp = subprocess.run(
            ["Rscript", "--vanilla", "-e",
             'stopifnot(as.character(getRversion())=="4.4.3"); '
             'stopifnot(packageDescription("metafor",fields="Version")=="4.8-0"); '
             'cat("pinned")'],
            capture_output=True, text=True, check=False, timeout=30,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout, "pinned")

    def test_live_per_study_md_smd_metafor_escalc(self):
        for label, rows in DATASETS.items():
            for measure in ("MD", "SMD"):
                with self.subTest(data=label, measure=measure):
                    cp = run_r(rows, measure)
                    self.assertEqual(cp.returncode, 0, cp.stderr)
                    external = parse_r(cp.stdout, len(rows))
                    actual = run_js(rows, measure)
                    self.assertEqual(external["k"], len(rows))
                    # SMD JS explicitly uses a close but approximate Hedges J.
                    # Compare to metafor's independently calculated corrected SMD;
                    # do not pretend this is bitwise parity.
                    tol = 7e-4 if measure == "SMD" else 1e-10
                    for i, point in enumerate(actual["points"]):
                        for attr in ("yi", "vi"):
                            self.assertAlmostEqual(
                                point[attr], external[f"study_{i}_{attr}"],
                                delta=tol,
                                msg=f"{label} {measure} study {i} {attr}",
                            )

    def test_live_rem_hksj_95ci_against_metafor(self):
        for label, rows in DATASETS.items():
            for measure in ("MD", "SMD"):
                with self.subTest(data=label, measure=measure):
                    cp = run_r(rows, measure)
                    self.assertEqual(cp.returncode, 0, cp.stderr)
                    external = parse_r(cp.stdout, len(rows))
                    pool = run_js(rows, measure)["pool"]
                    self.assertEqual(pool["k"], external["k"])
                    for js_key, r_key in (
                        ("yi", "mu"), ("tau2", "tau2"), ("se", "se"),
                        ("ci_low", "ci_low"), ("ci_high", "ci_high"),
                    ):
                        self.assertTrue(
                            math.isclose(pool[js_key], external[r_key],
                                         rel_tol=0, abs_tol=3e-3),
                            f"{label} {measure} {js_key}: "
                            f"JS={pool[js_key]:.17g}; metafor={external[r_key]:.17g}",
                        )

    def test_live_hksj_prediction_intervals_against_metafor(self):
        # The R oracle calls metafor::predict(fit) at this exact version.
        # This checks real production JS intervals, not cached R numbers.
        for label, rows in DATASETS.items():
            for measure in ("MD", "SMD"):
                with self.subTest(data=label, measure=measure):
                    cp = run_r(rows, measure)
                    self.assertEqual(cp.returncode, 0, cp.stderr)
                    external = parse_r(cp.stdout, len(rows))
                    pool = run_js(rows, measure)["pool"]
                    for js_key, r_key in (("pi_low", "pi_low"),
                                          ("pi_high", "pi_high")):
                        self.assertIn(js_key, pool)
                        self.assertTrue(
                            math.isclose(pool[js_key], external[r_key],
                                         rel_tol=0, abs_tol=3e-3),
                            f"{label} {measure} {js_key}: "
                            f"JS={pool[js_key]:.17g}, R={external[r_key]:.17g}",
                        )
                    if label == "heteroscedastic_boundary" and measure == "MD":
                        # Deliberately catches using classical seMu instead
                        # of inflated HKSJ seH when REML is on its boundary.
                        # R/metafor 4.8-0 optimises to a residual boundary
                        # tau² of ~7e-7 on this stress case, not exact 0.
                        # This is numerical convergence tolerance, not a
                        # relaxation of the production JS equality invariant.
                        self.assertLessEqual(abs(external["tau2"]), 1e-5)
                        self.assertGreater(external["se"], 0.3)
                        for lohi in ("low", "high"):
                            self.assertAlmostEqual(
                                external[f"pi_{lohi}"], external[f"ci_{lohi}"],
                                delta=1e-5)
                            self.assertAlmostEqual(
                                pool[f"pi_{lohi}"], pool[f"ci_{lohi}"],
                                delta=1e-10)

    def test_prediction_interval_withheld_for_two_studies(self):
        out = run_js(DATASETS["near_homogeneous"][:2], "MD")["pool"]
        self.assertEqual(out["k"], 2)
        self.assertNotIn("pi_low", out)
        self.assertNotIn("pi_high", out)

    def test_live_reml_fisher_information_is_unit_scale_equivariant(self):
        """R 4.4.3 / metafor 4.8-0 independently checks both actual unit scales.

        The old JavaScript trP2 < 1e-15 threshold returned the DL starting
        variance (about 6.5253 in base units) instead of REML (about 10.13)
        only at the large scale. These are synthetic numerical stress inputs,
        never verified trial outcomes.
        """
        base_rows = tuple(
            (delta, 0.0, math.sqrt(variance * 10), math.sqrt(variance * 10), 20, 20)
            for delta, variance in ((0, 0.5), (2, 1), (4, 4), (9, 6))
        )
        scale = 10_000
        scaled_rows = tuple(
            tuple(value * scale if index < 4 else value
                  for index, value in enumerate(row))
            for row in base_rows
        )
        seen = {}
        for label, rows in (("base", base_rows), ("rescaled", scaled_rows)):
            with self.subTest(units=label):
                cp = run_r(rows, "MD")
                self.assertEqual(cp.returncode, 0, cp.stderr)
                external = parse_r(cp.stdout, len(rows))
                actual = run_js(rows, "MD")["pool"]
                factor = 1 if label == "base" else scale
                self.assertEqual(actual["k"], external["k"])
                self.assertGreater(external["tau2"], 0)
                self.assertTrue(
                    math.isclose(actual["tau2"] / factor**2,
                                 external["tau2"] / factor**2,
                                 abs_tol=0.05, rel_tol=0),
                    f"{label}: JS tau2={actual['tau2']}; "
                    f"live R tau2={external['tau2']}",
                )
                for js_key, r_key in (
                    ("yi", "mu"), ("ci_low", "ci_low"),
                    ("ci_high", "ci_high"), ("pi_low", "pi_low"),
                    ("pi_high", "pi_high"),
                ):
                    self.assertTrue(
                        math.isclose(actual[js_key] / factor,
                                     external[r_key] / factor,
                                     rel_tol=0, abs_tol=0.08),
                        f"{label}: {js_key}: JS={actual[js_key]}, "
                        f"live R={external[r_key]}",
                    )
                seen[label] = (actual, external)
        for source in (0, 1):
            base, rescaled = seen["base"][source], seen["rescaled"][source]
            self.assertAlmostEqual(
                base["tau2"], rescaled["tau2"] / scale**2, delta=0.08,
                msg="REML tau2 must be independent of measurement units",
            )

    def test_invalid_raw_continuous_rows_fail_closed(self):
        good = DATASETS["near_homogeneous"]
        invalid_rows = {
            "zero_sd": ((10, 9, 0, 2, 30, 30),) + good[:2],
            "negative_sd": ((10, 9, -1, 2, 30, 30),) + good[:2],
            "fractional_n": ((10, 9, 2, 2, 30.5, 30),) + good[:2],
            "small_n": ((10, 9, 2, 2, 1, 30),) + good[:2],
        }
        for label, rows in invalid_rows.items():
            for measure in ("MD", "SMD"):
                with self.subTest(case=label, measure=measure):
                    cp = run_r(rows, measure)
                    self.assertNotEqual(cp.returncode, 0)
                    self.assertIn("requires >=2 finite complete raw continuous", cp.stderr)
                    with self.assertRaisesRegex(AssertionError, "invalid continuous"):
                        run_js(rows, measure)


if __name__ == "__main__":
    unittest.main()
