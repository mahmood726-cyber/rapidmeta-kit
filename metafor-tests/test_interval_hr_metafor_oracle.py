"""TRUE external R/metafor parity for shipped experimental interval-HR JS.

Test only explicitly synthetic, independent study/window HR+95%CI inputs.
No clinical study effect editing, no cached R anchors, no skipped oracle.
Requires R 4.4.3 + SHA-pinned metafor 4.8-0 via dedicated CI job.
The unit-of-analysis refusal must be tested independently of numerical parity.
"""
import csv
import io
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RSCRIPT = ROOT / "oracle-tests" / "oracle_interval_hr_metafor.R"
COLUMNS = ("trial", "t0", "t1", "HR", "lo", "hi")
OUTPUT = ("t0", "t1", "k", "HR", "ci_lo", "ci_hi", "tau2")

# Fixture tuples deliberately repeat no independent trial within one window.
# The same trial at a later NON-OVERLAPPING window is a separate analysis.
NEAR = (
    ("A", 0, 6, 0.75, 0.60, 0.92),
    ("B", 0, 6, 0.80, 0.65, 0.99),
    ("C", 0, 6, 0.72, 0.55, 0.95),
)
HETERO = (
    ("D", 0, 6, 0.50, 0.35, 0.71),
    ("E", 0, 6, 1.10, 0.85, 1.42),
    ("F", 0, 6, 0.80, 0.56, 1.14),
    ("G", 0, 6, 1.23, 0.88, 1.72),
    ("H", 0, 6, 0.60, 0.40, 0.90),
)
TWO_WINDOWS = NEAR + (
    ("A", 6, 12, 0.86, 0.63, 1.16),
    ("B", 6, 12, 1.05, 0.82, 1.33),
    ("C", 6, 12, 0.93, 0.72, 1.20),
)
JS = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const rows = JSON.parse(process.argv[1]);
const byTrial = new Map();
for (const [trial,t0,t1,HR,lo,hi] of rows) {
  if (!byTrial.has(trial)) byTrial.set(trial, {name:trial,intervals:[]});
  byTrial.get(trial).intervals.push({t0,t1,HR,HR_ci_lo:lo,HR_ci_hi:hi});
}
const bp = [...new Set(rows.flatMap(x=>[x[1],x[2]]))].sort((a,b)=>a-b);
const result = S.intervalHRPool([...byTrial.values()], bp);
console.log(JSON.stringify(result));
"""

def run_js(rows):
    p = subprocess.run(
        ["node", "-e", JS, json.dumps(rows)],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    if p.returncode:
        raise AssertionError("shipped JS failed: " + p.stderr)
    return json.loads(p.stdout)

def r_process(rows):
    tsv = "\t".join(COLUMNS) + "\n" + "".join(
        "\t".join(str(v) for v in row) + "\n" for row in rows
    )
    return subprocess.run(
        ["Rscript", "--vanilla", str(RSCRIPT)],
        input=tsv, capture_output=True, text=True,
        cwd=ROOT, timeout=120, check=False,
    )

def run_r(rows):
    p = r_process(rows)
    if p.returncode:
        raise AssertionError("external metafor refused positive case: " + p.stderr)
    reader = csv.DictReader(io.StringIO(p.stdout), delimiter="\t")
    if tuple(reader.fieldnames or ()) != OUTPUT:
        raise AssertionError("invalid native R output columns: " + p.stdout)
    data = []
    for r in reader:
        if set(r) != set(OUTPUT):
            raise AssertionError("malformed external R row")
        v = {k: float(r[k]) for k in OUTPUT}
        if not all(math.isfinite(x) for x in v.values()):
            raise AssertionError("nonfinite native R comparator")
        data.append(v)
    if not data:
        raise AssertionError("native R silently returned no windows")
    return data

def compare(js, external):
    if js.get("error") or len(js.get("intervals", [])) != len(external):
        raise AssertionError("shipped JS interval set mismatch/refusal")
    for observed, expected in zip(js["intervals"], external):
        for key in ("t0", "t1", "k"):
            if observed[key] != expected[key]:
                raise AssertionError("window identity/k mismatch " + key)
        for jk, rk in (("HR", "HR"), ("HR_ci_lo", "ci_lo"),
                       ("HR_ci_hi", "ci_hi"), ("tau2", "tau2")):
            x, y = observed[jk], expected[rk]
            # The JS Fisher-scoring REML and metafor's optimiser are not
            # bitwise-identical. This bounded 1e-3 is a TEST TOLERANCE,
            # not a clinical materiality threshold or accepted discrepancy.
            if not isinstance(x, (int, float)) or not math.isfinite(x) or (
                not math.isclose(x, y, rel_tol=1e-3, abs_tol=1e-3)
            ):
                raise AssertionError(
                    f"{jk} differs: shipped JS={x!r}, live metafor={y:.17g}"
                )

class IntervalHRMetaforOracle(unittest.TestCase):
    def test_runtime_exact_versions(self):
        p = subprocess.run(
            ["Rscript", "--vanilla", "-e",
             'stopifnot(as.character(getRversion())=="4.4.3"); '
             'stopifnot(packageDescription("metafor",fields="Version")=="4.8-0"); '
             'cat("pinned")'],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, "pinned")

    def test_actual_metafor_reml_hksj_window_concordance(self):
        for label, rows in (("near", NEAR), ("heterogeneous", HETERO),
                            ("disjoint_windows", TWO_WINDOWS)):
            with self.subTest(data=label):
                compare(run_js(rows), run_r(rows))

    def test_same_trial_window_duplicate_refused_by_both(self):
        dup = (NEAR[0], NEAR[0]) + NEAR[1:]
        self.assertRegex(run_js(dup).get("error", ""), "Repeated interval-HR")
        p = r_process(dup)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("duplicate trial/time-window", p.stderr)

    def test_malformed_hr_fails_closed_in_r_and_duplicate_js(self):
        bad = (NEAR[0], ("A", 0, 6, -1, 0, 2)) + NEAR[1:]
        self.assertRegex(run_js(bad).get("error", ""), "Repeated interval-HR")
        p = r_process(bad)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("invalid or incomplete", p.stderr)

    def test_single_malformed_study_is_not_silently_omitted(self):
        # Previously JS reported k=3 from four records while R refused
        # the same input, violating both the evidence set and oracle contract.
        cases = (
            ("negative_hr", NEAR + (("D", 0, 6, -1, 0.50, 1.20),)),
            ("inverted_ci", NEAR + (("D", 0, 6, 0.80, 1.20, 0.50),)),
            ("later_window", TWO_WINDOWS + (("D", 6, 12, -1, 0.50, 1.20),)),
        )
        for label, rows in cases:
            with self.subTest(case=label):
                result = run_js(rows)
                self.assertEqual(result.get("intervals"), [])
                self.assertRegex(result.get("error", ""), "Invalid interval-HR")
                external = r_process(rows)
                self.assertNotEqual(external.returncode, 0)
                self.assertIn("invalid or incomplete", external.stderr)

    def test_tampered_hr_must_fail_numerical_comparison(self):
        expected = run_r(NEAR)
        observed = run_js(NEAR)
        observed["intervals"][0]["HR"] += 0.10
        with self.assertRaisesRegex(AssertionError, "HR differs"):
            compare(observed, expected)

if __name__ == "__main__":
    unittest.main()
