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
// The shipped panel uses Object.keys(seen).map(Number) for numeric windows.
// Only normalise the BREAKPOINTS: source iv.t0/t1 must stay raw so invalid
// lexemes still fail the strict source-typing check.
const bp = [...new Set(rows.flatMap(x=>[x[1],x[2]]).map(Number))].sort((a,b)=>a-b);
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

    def test_case_and_whitespace_alias_trial_ids_refused_by_js_and_r(self):
        # Source-backed R-oracle discrepancy: R previously keyed raw trial
        # labels while shipped JS normalises all stable IDs with trim/lower.
        # These are one synthetic study, not independent k=4 evidence.
        for alias in ("a", " A ", " a "):
            with self.subTest(alias=repr(alias)):
                rows = (NEAR[0], (alias,) + NEAR[0][1:]) + NEAR[1:]
                for separately in (False, True):
                    js = run_js(rows, separate_objects=separately)
                    self.assertEqual(js.get("intervals"), [])
                    self.assertRegex(js.get("error", ""), "Repeated interval-HR")
                native = r_process(rows)
                self.assertNotEqual(native.returncode, 0, native.stdout)
                self.assertIn("duplicate trial/time-window", native.stderr)
        # Genuine distinct trial IDs must remain eligible for pooling.
        compare(run_js(NEAR, separate_objects=True), run_r(NEAR))

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

    def test_non_numeric_effect_values_refused_by_js_and_native_r(self):
        # Distinct from time-boundary typing: the shipped JS previously
        # coerced bools/arrays to plausible HR/CI values and pooled them.
        # R's source table is deliberately strict about numeric column types.
        cases = (
            ("boolean_HR", True, 0.8, 1.2),
            ("array_HR", [0.8], 0.6, 1.2),
            ("boolean_lower_CI", 1.2, True, 1.5),
            ("array_upper_CI", 0.8, 0.6, [1.2]),
        )
        for label, hr, lo, hi in cases:
            with self.subTest(case=label):
                rows = (("A", 0, 6, hr, lo, hi),) + NEAR[1:]
                js = run_js(rows)
                self.assertEqual(js.get("intervals"), [])
                self.assertRegex(js.get("error", ""), "Invalid interval-HR effect")
                native = r_process(rows)
                self.assertNotEqual(native.returncode, 0, native.stdout)
                self.assertIn("invalid or incomplete interval-HR source table", native.stderr)
        # Source imports legitimately represent real numbers as decimal text.
        decimal_text = (("A", 0, 6, "0.75", "0.60", "0.92"),) + NEAR[1:]
        compare(run_js(decimal_text), run_r(decimal_text))

    def test_non_decimal_numeric_source_tokens_refused_in_js_and_native_r(self):
        # Prior JS Number coercion silently accepted non-decimal source
        # representations as plausible trial effects or follow-up months.
        # These are synthetic input-type refusals, not clinical R parity.
        cases = (
            ("hexadecimal_HR", ("A", 0, 6, "0x1", 0.8, 1.2),
             "Invalid interval-HR effect"),
            ("binary_HR", ("A", 0, 6, "0b1", 0.8, 1.2),
             "Invalid interval-HR effect"),
            ("octal_CI", ("A", 0, 6, 1.5, 1.0, "0o2"),
             "Invalid interval-HR effect"),
            ("hexadecimal_time", ("A", "0x0", 6, 0.75, 0.60, 0.92),
             "Invalid interval-HR time boundaries"),
        )
        for label, row, reason in cases:
            with self.subTest(source_token=label):
                rows = (row,) + NEAR[1:]
                observed = run_js(rows)
                self.assertEqual(observed.get("intervals"), [])
                self.assertRegex(observed.get("error", ""), reason)
                native = r_process(rows)
                self.assertNotEqual(native.returncode, 0, native.stdout)
                self.assertIn("invalid or incomplete interval-HR source table",
                              native.stderr)
        # Decimal scientific notation remains valid in both executables.
        good = (("A", "0e0", "6e0", "7.5e-1", "6e-1", "9.2e-1"),) + NEAR[1:]
        compare(run_js(good), run_r(good))

    def test_unrepresentable_pooled_hr_interval_refused_in_js_and_r(self):
        # Finite source rows can yield nonrepresentable exp(CI). Before
        # the correction, shipped JS returned a zero lower bound and
        # Infinity upper bound (JSON null). This negative test is a
        # refusal gate, NOT a positive numerical parity comparison.
        rows = (
            ("A", 0, 6, 1e308, 1e307, 1.79e308),
            ("B", 0, 6, 0.8, 0.6, 1.0),
        )
        js = run_js(rows)
        self.assertEqual(js.get("intervals"), [])
        self.assertRegex(js.get("error", ""),
                         "Unrepresentable interval-HR pooled estimate")
        native = r_process(rows)
        self.assertNotEqual(native.returncode, 0,
                            "Native R returned a pooled nonrepresentable CI")
        # A generic R runtime/optimizer failure must not masquerade as
        # validated refusal of an unrepresentable ratio/CI. Both the early
        # nonfinite guard and the later positive-ratio guard are legitimate
        # boundary refusals; an unrelated error is NOT an oracle PASS.
        self.assertRegex(
            native.stderr,
            r"(?:nonfinite external interval-HR estimate|"
            r"unrepresentable external interval-HR ratio or confidence limits)",
        )

    def test_single_study_underflow_refused_for_the_specific_reason(self):
        # Deliberately synthetic, grossly asymmetric source CI. Input HR
        # and bounds remain finite and positive, but the k=1 normal
        # interval underflows to a zero lower ratio endpoint. Before this
        # change, native R accepted 0 via is.finite(0); a mere nonzero exit
        # status could also hide an unrelated R error.
        rows = (("A", 0, 6, 1e-200, 1e-300, 1e300),)
        js = run_js(rows)
        self.assertEqual(js.get("intervals"), [])
        self.assertRegex(js.get("error", ""),
                         "Unrepresentable interval-HR pooled estimate")
        native = r_process(rows)
        self.assertNotEqual(native.returncode, 0, native.stdout)
        self.assertIn(
            "unrepresentable external interval-HR ratio or confidence limits",
            native.stderr,
        )

    def test_tampered_hr_must_fail_numerical_comparison(self):
        expected = run_r(NEAR)
        observed = run_js(NEAR)
        observed["intervals"][0]["HR"] += 0.10
        with self.assertRaisesRegex(AssertionError, "HR differs"):
            compare(observed, expected)


    def test_summary_hr_rem_l_hksj_against_live_metafor_and_nnt_r_formula(self):
        """Method-matched, synthetic summary HR + specified-risk algebra only.

        The separately executed interval-HR R oracle is valid here because
        summary fit() uses the same logHRfromCI and poolLogRE functions as
        intervalHRPool() but without time-window selection. Every input below
        has exactly one common analysis window; the JS call exercises the
        separate published summary fit(), not intervalHRPool(). The NNT R
        calculation conditions on an explicitly synthetic fixed baseline
        event risk and makes NO claim that crude counts are fixed-time
        censoring-adjusted survival or clinically valid NNT evidence.
        """
        import hashlib

        summary_js = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const records = JSON.parse(process.argv[1]);
const trials = records.map(x=>({studlab:x[0],HR:x[1],HR_ci_lo:x[2],HR_ci_hi:x[3]}));
const fitted = S.fit(trials);
const risk = Number(process.argv[2]);
console.log(JSON.stringify({fit:fitted,nnt:fitted?S.nntForHR(fitted.pooled_HR,risk):null}));
"""
        # Independent base-R implementation of S_control(t)^HR - S_control(t).
        # The comparator tests arithmetic at a supplied synthetic risk;
        # it does not validate estimation of S_control(t) in an actual trial.
        nnt_r = r"""
stopifnot(as.character(getRversion())=="4.4.3")
a <- commandArgs(trailingOnly=TRUE)
stopifnot(length(a)==2L)
hr <- as.numeric(a[1]); risk <- as.numeric(a[2])
stopifnot(is.finite(hr),hr>0,is.finite(risk),risk>0,risk<1)
s0 <- 1-risk
arr <- s0^hr-s0
stopifnot(is.finite(arr),abs(arr)>1e-9)
cat(sprintf("%.17g\t%.17g\t%.17g\t%s\n",arr,1-s0^hr,1/abs(arr),
            ifelse(arr>0,"NNTB","NNTH")))
"""
        positive = (
            ("single_normal", SINGLE),
            ("two_study_reml", PAIR_NEAR),
            ("three_study_reml", NEAR),
            ("heterogeneous_reml", HETERO),
        )
        for label, rows in positive:
            with self.subTest(case=label):
                raw = [(trial, hr, lo, hi) for trial, _t0, _t1, hr, lo, hi in rows]
                input_json = json.dumps(raw, separators=(",", ":"))
                digest = hashlib.sha256(input_json.encode("utf-8")).hexdigest()
                print(f"summary-HR native R synthetic fixture {label} sha256={digest}")
                proc = subprocess.run(
                    ["node", "-e", summary_js, input_json, "0.2"],
                    cwd=ROOT, capture_output=True, text=True, timeout=30,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                js = json.loads(proc.stdout)
                fitted = js["fit"]
                self.assertIsNotNone(fitted, "summary fit refused positive fixture")
                r_rows = run_r(rows)
                self.assertEqual(len(r_rows), 1, "expected one source-matched window")
                ref = r_rows[0]
                self.assertEqual(fitted["k"], int(ref["k"]))
                for js_key, r_key in (
                    ("pooled_HR", "HR"),
                    ("pooled_HR_ci_lo", "ci_lo"),
                    ("pooled_HR_ci_hi", "ci_hi"),
                    ("tau2", "tau2"),
                ):
                    self.assertTrue(
                        math.isclose(fitted[js_key], ref[r_key],
                                     rel_tol=1e-3, abs_tol=1e-3),
                        f"{label}: {js_key} JS={fitted[js_key]} R={ref[r_key]}",
                    )
                # Test the separate NNT function against actual base R,
                # using the JS pooled HR as the common formula input.
                r_nnt = subprocess.run(
                    ["Rscript", "--vanilla", "-e", nnt_r,
                     format(fitted["pooled_HR"], ".17g"), "0.2"],
                    cwd=ROOT, capture_output=True, text=True, timeout=30,
                    check=False,
                )
                self.assertEqual(r_nnt.returncode, 0, r_nnt.stderr)
                fields = r_nnt.stdout.strip().split("\t")
                self.assertEqual(len(fields), 4, r_nnt.stdout)
                for key, expected in zip(("arr", "tx_risk", "nnt"), fields[:3]):
                    self.assertTrue(
                        math.isclose(js["nnt"][key], float(expected),
                                     rel_tol=1e-10, abs_tol=1e-10),
                        f"{label}: NNT arithmetic {key} differs from live R",
                    )
                self.assertEqual(js["nnt"]["direction"], fields[3])
                # Negative perturbation: fitted estimator differences beyond
                # the declared tolerance MUST be detected, not swallowed.
                self.assertFalse(
                    math.isclose(fitted["pooled_HR"] + 0.1, ref["HR"],
                                 rel_tol=1e-3, abs_tol=1e-3)
                )

    def test_summary_hr_source_refusal_against_live_r_oracle(self):
        """R and summary JS refuse malformed declared evidence, never partial k."""
        summary_js = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const rows=JSON.parse(process.argv[1]);
console.log(JSON.stringify(S.fit(rows.map(x=>({HR:x[3],HR_ci_lo:x[4],HR_ci_hi:x[5]})))));
"""
        for label, bad_hr in (
            ("boolean", True), ("hexadecimal", "0x1"),
            ("nonpositive", -1), ("point_above_CI", 2.0),
        ):
            with self.subTest(case=label):
                # A bad middle record cannot be silently removed to pool k=2.
                rows = (NEAR[0], ("BAD", 0, 6, bad_hr, 0.6, 1.2), NEAR[1])
                js = subprocess.run(
                    ["node", "-e", summary_js, json.dumps(rows)],
                    cwd=ROOT, capture_output=True, text=True, timeout=30,
                    check=False,
                )
                self.assertEqual(js.returncode, 0, js.stderr)
                self.assertIsNone(json.loads(js.stdout),
                                  "malformed source must not yield summary HR")
                r = r_process(rows)
                self.assertNotEqual(r.returncode, 0, r.stdout)
                self.assertIn("invalid or incomplete interval-HR source table",
                              r.stderr)


    def test_summary_hksj_prediction_interval_matches_live_metafor(self):
        """Synthetic REML/adhoc PI including HKSJ-floored pooled-mean SE.

        This checks the *prediction* interval, which the prior external-R
        summary-HR fit comparisons did not test. A narrower pre-HKSJ formula
        must not pass. Not original clinical input or validated survival PI.
        """
        import hashlib
        yi = [0.18834274230829667, 0.6136462688923738,
              -0.8979944856056723, 0.1459654781547634]
        vi = [0.007078724762954062, 0.01585607885918258,
              0.3701926996080275, 0.007318246865161381]
        payload = json.dumps({"yi": yi, "vi": vi}, separators=(",", ":"))
        print("HKSJ PI synthetic raw JSON sha256="
              + hashlib.sha256(payload.encode("utf-8")).hexdigest())
        js_program = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const data=JSON.parse(process.argv[1]);
console.log(JSON.stringify(S._poolLogRE(data.yi,data.vi)));
"""
        js_proc = subprocess.run(
            ["node", "-e", js_program, payload],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(js_proc.returncode, 0, js_proc.stderr)
        js = json.loads(js_proc.stdout)
        self.assertEqual(js["k"], 4)
        self.assertTrue(js["tau2"] > 0)
        self.assertTrue(math.isfinite(js["pi_lo"]) and
                        math.isfinite(js["pi_hi"]))

        r_code = r"""
stopifnot(as.character(getRversion())=="4.4.3")
stopifnot(packageVersion("metafor")==package_version("4.8-0"))
a <- commandArgs(trailingOnly=TRUE)
stopifnot(length(a)==2L)
yi <- as.numeric(strsplit(a[1],",",fixed=TRUE)[[1]])
vi <- as.numeric(strsplit(a[2],",",fixed=TRUE)[[1]])
stopifnot(length(yi)==4L,length(vi)==4L,all(is.finite(yi)),
          all(is.finite(vi)),all(vi>0))
fit <- metafor::rma.uni(yi=yi,vi=vi,method="REML",test="adhoc")
prediction <- predict(fit)
out <- c(tau2=fit$tau2, mu=as.numeric(fit$b),
         pi_lo=prediction$pi.lb, pi_hi=prediction$pi.ub)
stopifnot(all(is.finite(out)), out[["tau2"]]>0,
          out[["pi_lo"]]<out[["pi_hi"]])
cat(paste(sprintf("%.17g",out),collapse="\t"),"\n",sep="")
"""
        r_proc = subprocess.run(
            ["Rscript", "--vanilla", "-e", r_code,
             ",".join(format(v, ".17g") for v in yi),
             ",".join(format(v, ".17g") for v in vi)],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        self.assertEqual(r_proc.returncode, 0, r_proc.stderr)
        ref = list(map(float, r_proc.stdout.strip().split("\t")))
        self.assertEqual(len(ref), 4, r_proc.stdout)
        for key, observed in zip(("tau2", "mu", "pi_lo", "pi_hi"), ref):
            self.assertTrue(
                math.isclose(js[key], observed, rel_tol=2e-3, abs_tol=2e-3),
                f"method-matched R {key}: JS {js[key]} vs R {observed}",
            )
        # Negative control: a materially narrowed interval cannot be accepted.
        self.assertFalse(math.isclose(js["pi_lo"] + 0.08, ref[2],
                                      rel_tol=2e-3, abs_tol=2e-3))


    def test_zero_heterogeneity_summary_pi_equals_ci_in_live_metafor(self):
        """Boundary oracle: at tau2=0, metafor's default adhoc PI equals CI.

        This covers an untested prediction-interval boundary, distinct from
        the prior heterogeneous q*>1 PI test. As documented by predict.rma,
        with k-p t degrees of freedom PI=CI when tau2=0:
        https://wviechtb.github.io/metafor/reference/predict.rma.html
        Synthetic only, no original clinical study effect or KM follow-up.
        A deliberately forged PI endpoint must fail the numerical comparator.
        """
        import hashlib

        yi = [math.log(0.8)] * 4
        vi = [0.02, 0.04, 0.03, 0.05]
        payload = json.dumps({"yi": yi, "vi": vi}, separators=(",", ":"))
        self.assertEqual(
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "6e3080edf042a0e1ff7f489e440a95f84344b32e39b2226e76f6426cd146ddbd",
            "synthetic zero-tau input identity changed",
        )
        js_code = r"""
const S = require('./assets/vendor/rapidmeta-survival.js').RapidMetaSurvival;
const d = JSON.parse(process.argv[1]);
console.log(JSON.stringify(S._poolLogRE(d.yi,d.vi)));
"""
        js_proc = subprocess.run(
            ["node", "-e", js_code, payload], cwd=ROOT, capture_output=True,
            text=True, timeout=30, check=False,
        )
        self.assertEqual(js_proc.returncode, 0, js_proc.stderr)
        js = json.loads(js_proc.stdout)
        self.assertEqual(js["k"], 4)
        self.assertTrue(math.isfinite(js["pi_lo"]) and
                        math.isfinite(js["pi_hi"]))
        self.assertAlmostEqual(js["tau2"], 0.0, delta=1e-12)

        r_code = r"""
stopifnot(as.character(getRversion())=="4.4.3")
stopifnot(packageVersion("metafor")==package_version("4.8-0"))
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L)
yi <- as.numeric(strsplit(args[1],",",fixed=TRUE)[[1]])
vi <- as.numeric(strsplit(args[2],",",fixed=TRUE)[[1]])
stopifnot(length(yi)==4L, length(vi)==4L,
          all(is.finite(yi)), all(is.finite(vi)), all(vi>0))
fit <- metafor::rma.uni(yi=yi, vi=vi, method="REML", test="adhoc",
                        control=list(tol=1e-12,maxiter=500))
pred <- predict(fit)
v <- c(as.numeric(fit$b), fit$tau2, fit$ci.lb, fit$ci.ub,
       pred$pi.lb, pred$pi.ub)
stopifnot(length(v)==6L, all(is.finite(v)), abs(v[2])<1e-10,
          abs(v[3]-v[5])<1e-10, abs(v[4]-v[6])<1e-10)
cat(paste(sprintf("%.17g",v),collapse="\t"),"\n",sep="")
"""
        r_proc = subprocess.run(
            ["Rscript", "--vanilla", "-e", r_code,
             ",".join(format(v, ".17g") for v in yi),
             ",".join(format(v, ".17g") for v in vi)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
            check=False,
        )
        self.assertEqual(r_proc.returncode, 0, r_proc.stderr)
        vals = r_proc.stdout.strip().split("\t")
        self.assertEqual(len(vals), 6, r_proc.stdout)
        ref = dict(zip(("mu", "tau2", "ci_lo", "ci_hi", "pi_lo", "pi_hi"),
                       map(float, vals)))
        self.assertAlmostEqual(js["pi_lo"], js["ci_lo"], delta=1e-9)
        self.assertAlmostEqual(js["pi_hi"], js["ci_hi"], delta=1e-9)

        def assert_method_concordance(observed):
            for key in ("mu", "tau2", "ci_lo", "ci_hi", "pi_lo", "pi_hi"):
                if not math.isclose(observed[key], ref[key],
                                    rel_tol=2e-5, abs_tol=2e-5):
                    raise AssertionError(
                        f"zero-tau {key} mismatch: JS={observed[key]!r}, "
                        f"live metafor={ref[key]:.17g}"
                    )
        assert_method_concordance(js)
        forged = dict(js, pi_lo=js["pi_lo"] + 0.05)
        with self.assertRaisesRegex(AssertionError, "pi_lo mismatch"):
            assert_method_concordance(forged)


if __name__ == "__main__":
    unittest.main()
