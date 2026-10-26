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
# One-study inference is a normal CI, not a fitted meta-analysis; k=2 uses
# REML+floored HKSJ/t(1) and is not covered by a k>=3-only oracle.
SINGLE = NEAR[:1]
PAIR_NEAR = NEAR[:2]
PAIR_HETERO = HETERO[:2]
SMALL_MIXED_WINDOWS = SINGLE + (
    ("I", 6, 12, 0.86, 0.63, 1.16),
    ("J", 6, 12, 1.05, 0.82, 1.33),
)
JS = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const rows = JSON.parse(process.argv[1]);
const byTrial = new Map();
const separatedTrials = [];
const splitObjects = process.argv[2] === 'separate';
for (const [trial,t0,t1,HR,lo,hi] of rows) {
  const iv = {t0,t1,HR,HR_ci_lo:lo,HR_ci_hi:hi};
  if (splitObjects) {
    separatedTrials.push({nct:trial,name:trial,intervals:[iv]});
    continue;
  }
  if (!byTrial.has(trial)) byTrial.set(trial, {nct:trial,name:trial,intervals:[]});
  byTrial.get(trial).intervals.push(iv);
}
const bp = [...new Set(rows.flatMap(x=>[x[1],x[2]]))].sort((a,b)=>a-b);
const result = S.intervalHRPool(splitObjects ? separatedTrials : [...byTrial.values()], bp);
console.log(JSON.stringify(result));
"""

def run_js(rows, separate_objects=False):
    p = subprocess.run(
        ["node", "-e", JS, json.dumps(rows),
         "separate" if separate_objects else "grouped"],
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

    def test_small_k_normal_and_reml_hksj_are_externally_compared(self):
        # Must execute live R 4.4.3: k=1 normal 95% CI, k=2 actual
        # metafor 4.8-0 REML + floored HKSJ/t(1). No frozen R values.
        cases = (
            ("single_study_normal", SINGLE, (1,)),
            ("two_study_near_homogeneous", PAIR_NEAR, (2,)),
            ("two_study_heterogeneous", PAIR_HETERO, (2,)),
            ("mixed_small_k_windows", SMALL_MIXED_WINDOWS, (1, 2)),
        )
        for label, rows, expected_k in cases:
            with self.subTest(case=label):
                external = run_r(rows)
                self.assertEqual(tuple(int(r["k"]) for r in external), expected_k)
                compare(run_js(rows), external)

    def test_small_k_invalid_and_duplicate_evidence_fail_closed(self):
        # Negative controls prove the expanded k>=1 R oracle still refuses
        # a contradictory HR/CI and a duplicated one-study window.
        invalid = (("A", 0, 6, 2.0, 0.70, 1.20),)
        duplicate = SINGLE + SINGLE
        for label, rows, js_pattern, r_pattern in (
            ("single_invalid", invalid, "Invalid interval-HR", "invalid or incomplete"),
            ("single_duplicate", duplicate, "Repeated interval-HR", "duplicate trial/time-window"),
        ):
            with self.subTest(case=label):
                observed = run_js(rows)
                self.assertEqual(observed.get("intervals"), [])
                self.assertRegex(observed.get("error", ""), js_pattern)
                external = r_process(rows)
                self.assertNotEqual(external.returncode, 0)
                self.assertIn(r_pattern, external.stderr)

    def test_same_trial_window_duplicate_refused_by_both(self):
        dup = (NEAR[0], NEAR[0]) + NEAR[1:]
        self.assertRegex(run_js(dup).get("error", ""), "Repeated interval-HR")
        p = r_process(dup)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("duplicate trial/time-window", p.stderr)

    def test_separately_materialized_same_trial_refused_and_disjoint_allowed(self):
        # Against pre-fix JS: the same NCT in separate objects was counted as
        # a fourth independent study, while native R refused the input.
        duplicated = (NEAR[0], NEAR[0]) + NEAR[1:]
        observed = run_js(duplicated, separate_objects=True)
        self.assertEqual(observed.get("intervals"), [])
        self.assertRegex(observed.get("error", ""), "Repeated interval-HR")
        external = r_process(duplicated)
        self.assertNotEqual(external.returncode, 0)
        self.assertIn("duplicate trial/time-window", external.stderr)
        # The same NCT legitimately contributes to SEPARATE window analyses.
        compare(run_js(TWO_WINDOWS, separate_objects=True),
                run_r(TWO_WINDOWS))

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
            ("hr_above_ci", NEAR + (("D", 0, 6, 2.0, 0.70, 1.20),)),
            ("hr_below_ci", NEAR + (("D", 0, 6, 0.40, 0.60, 1.20),)),
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

    def test_mixed_window_union_must_refuse_in_js_and_native_r(self):
        # A complete [0,6] summary HR cannot be inferred for [0,3] or [3,6].
        # Previous R oracle would pool shorter windows (k=2 each) and the
        # browser would refuse: a missing native-R refusal parity gate.
        mixed = (
            ("A", 0, 6, 1.90, 1.50, 2.50),
            ("B", 0, 3, 0.80, 0.60, 1.05),
            ("B", 3, 6, 0.90, 0.68, 1.20),
            ("C", 0, 3, 0.78, 0.59, 1.04),
            ("C", 3, 6, 0.88, 0.66, 1.17),
        )
        for split in (False, True):
            with self.subTest(separately_materialized=split):
                observed = run_js(mixed, separate_objects=split)
                self.assertEqual(observed.get("intervals"), [])
                self.assertRegex(observed.get("error", ""),
                                 "Non-aligned interval-HR time window")
        external = r_process(mixed)
        self.assertNotEqual(external.returncode, 0)
        self.assertIn("non-aligned interval-HR source windows", external.stderr)
        # Positive: corresponding non-overlapping periods genuinely produce
        # matching k=2 estimates without silently dropping a study.
        short_only = mixed[1:]
        compare(run_js(short_only), run_r(short_only))

    def test_missing_source_time_boundaries_refused_by_js_and_r(self):
        # The source time is missing, not observed at t=0; numeric coercion
        # previously let JS pool a synthetic row as a month-zero HR.
        # The independently executed native R source table must also refuse.
        for label, start in (
            ("blank", ""), ("spaces", "  "), ("null", None),
            ("boolean", False), ("negative", -1),
        ):
            with self.subTest(case=label):
                rows = (("A", start, 6, 0.75, 0.60, 0.92),) + NEAR[1:]
                js = run_js(rows)
                self.assertEqual(js.get("intervals"), [])
                self.assertRegex(js.get("error", ""),
                                 "Invalid interval-HR time boundaries")
                native = r_process(rows)
                self.assertNotEqual(
                    native.returncode, 0,
                    "Native R accepted a source row without a valid start time",
                )

    def test_tampered_hr_must_fail_numerical_comparison(self):
        expected = run_r(NEAR)
        observed = run_js(NEAR)
        observed["intervals"][0]["HR"] += 0.10
        with self.assertRaisesRegex(AssertionError, "HR differs"):
            compare(observed, expected)

if __name__ == "__main__":
    unittest.main()
