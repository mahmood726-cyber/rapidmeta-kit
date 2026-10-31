"""Live, method-matched metafor 4.8-0 oracle for shipped PairwisePool.

This test MUST run native R. It is deliberately separate from our self-written
base-R oracle and cannot pass from stored/cached numerical anchors.
Scope: synthetic independent 2x2 tables, RR/OR, DL/PM, floored HKSJ,
plus an explicitly matched 0.5 per-study correction for informative
single-arm-zero/all-events cells. Cochrane PI and I2 conventions are not
asserted equal to metafor; REML, GLMM and clinical data remain NOT TESTED.
"""
import math
import subprocess
import sys
import unittest
from pathlib import Path

# Keep this externally provisioned test OUTSIDE base-R-only discovery.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "oracle-tests"))
from test_pairwise_oracle import CASESETS, run_js

R_SCRIPT = ROOT / "oracle-tests" / "oracle_metafor.R"
FIELDS = frozenset(("k_used", "mu_log", "tau2", "Q", "ci_lo", "ci_hi"))


def parse_metafor_result(output):
    """Reject malformed, duplicate, missing and non-finite external results."""
    result = {}
    for line in output.splitlines():
        pair = line.split("\t")
        if len(pair) != 2 or pair[0] in result or pair[0] not in FIELDS:
            raise ValueError("malformed/duplicate metafor output: " + line)
        try:
            value = float(pair[1])
        except ValueError as exc:
            raise ValueError("invalid metafor number: " + line) from exc
        if not math.isfinite(value):
            raise ValueError("non-finite metafor number: " + line)
        result[pair[0]] = value
    if result.keys() != FIELDS:
        raise ValueError("missing metafor output field(s)")
    return result


def invoke_metafor(rows, measure, method, matched_cc05=False):
    # Preserve fractional source lexemes for the native R count gate.
    # Python's %d silently truncates 1.5 to 1, manufacturing false parity.
    tab = "tE\ttN\tcE\tcN\n" + "".join(
        "\t".join(str(value) for value in row) + "\n" for row in rows
    )
    args = ["Rscript", str(R_SCRIPT), measure, method]
    if matched_cc05:
        args.append("CC05")
    return subprocess.run(
        args,
        input=tab, cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=90,
    )


def match_model(js_result, r_result):
    for key in FIELDS:
        value = js_result[key]
        reference_value = r_result[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise AssertionError("non-finite shipped " + key)
        if (isinstance(reference_value, bool) or
                not isinstance(reference_value, (int, float)) or
                not math.isfinite(reference_value)):
            raise AssertionError("non-finite metafor " + key)
        if key == "k_used":
            reference_k = r_result[key]
            if (isinstance(reference_k, bool) or
                    not isinstance(reference_k, (int, float)) or
                    not math.isfinite(reference_k) or
                    value != reference_k or value != math.floor(value)):
                raise AssertionError(
                    "k_used differs or is not an integer: JS=%r metafor=%r" %
                    (value, reference_k)
                )
            continue
        # The externally implemented PM solver need not converge bitwise to
        # the JS bisection. This is a stated numerical, not semantic, bound.
        tolerance = 3e-6 if key in ("tau2", "ci_lo", "ci_hi") else 1e-8
        if not math.isclose(value, reference_value,
                            rel_tol=tolerance, abs_tol=tolerance):
            raise AssertionError(
                "%s differs: JS=%.17g metafor=%.17g" %
                (key, value, reference_value)
            )
        # Tolerance must not conceal opposite effect directions, a zero-vs-
        # positive heterogeneity boundary, or a CI crossing the null ratio 1.
        # Such a case needs adjudication even if the numeric drift is tiny.
        null = 0.0 if key in ("mu_log", "tau2") else (
            1.0 if key in ("ci_lo", "ci_hi") else None
        )
        if null is not None and (
                (value > null) - (value < null) !=
                (reference_value > null) - (reference_value < null)):
            raise AssertionError(
                "%s differs: null-boundary classification JS=%.17g metafor=%.17g" %
                (key, value, reference_value)
            )


class ActualMetaforOracle(unittest.TestCase):
    def test_external_package_and_r_versions_are_pinned(self):
        cp = subprocess.run(
            ["Rscript", "-e",
             'stopifnot(as.character(getRversion())=="4.4.3"); '
             'stopifnot(packageDescription("metafor",fields="Version")=="4.8-0"); '
             'cat("pinned")'],
            capture_output=True, text=True, check=False, timeout=30,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(cp.stdout, "pinned")

    def test_eight_real_metafor_rr_or_pm_dl_comparisons(self):
        for label, rows in CASESETS.items():
            for measure in ("RR", "OR"):
                for method in ("DL", "PM"):
                    with self.subTest(dataset=label, measure=measure,
                                      method=method):
                        cp = invoke_metafor(rows, measure, method)
                        self.assertEqual(cp.returncode, 0, cp.stderr)
                        external = parse_metafor_result(cp.stdout)
                        shipped = run_js(rows, measure, method)
                        self.assertEqual(shipped["k_used"], len(rows))
                        match_model(shipped, external)

    def test_pinned_metafor_matches_informative_single_zero_and_all_event_cells(self):
        # Synthetic comparisons; R genuinely executes metafor::escalc with
        # add=0.5,to='only0', matching PairwisePool's per-table correction.
        # These are inverse-variance tests, NOT validation of rare-event GLMMs.
        cases = {
            "zero_treatment": ((0, 100, 8, 100),) + CASESETS["near_homogeneous"],
            "zero_control": ((7, 90, 0, 105),) + CASESETS["near_homogeneous"],
            "all_treatment": ((40, 40, 11, 45),) + CASESETS["near_homogeneous"],
        }
        for label, rows in cases.items():
            for measure in ("RR", "OR"):
                for method in ("DL", "PM"):
                    with self.subTest(case=label, measure=measure, method=method):
                        cp = invoke_metafor(rows, measure, method, matched_cc05=True)
                        self.assertEqual(cp.returncode, 0, cp.stderr)
                        external = parse_metafor_result(cp.stdout)
                        shipped = run_js(rows, measure, method)
                        self.assertEqual(shipped["k_used"], len(rows))
                        match_model(shipped, external)
                        # Explicit opt-in is essential: the same non-interior
                        # data must not pass the uncorrected oracle.
                        raw = invoke_metafor(rows, measure, method)
                        self.assertNotEqual(raw.returncode, 0)
                        self.assertIn("interior-only", raw.stderr)

    def test_matched_correction_fails_closed_for_dual_arm_exclusions(self):
        for excluded in ((0, 100, 0, 100), (10, 10, 20, 20)):
            rows = (excluded,) + CASESETS["near_homogeneous"]
            for measure in ("RR", "OR"):
                cp = invoke_metafor(rows, measure, "DL", matched_cc05=True)
                self.assertNotEqual(cp.returncode, 0)
                self.assertIn("CC05 refuses uninformative", cp.stderr)

    def test_binomial_count_integrity_refuses_fractional_and_unsafe_sources(self):
        # Native R must see original values (not %d-truncated values).
        # These are malformed synthetic tables, never clinical data.
        malformed = {
            "fractional_event": (1.5, 100, 5, 100),
            "fractional_denominator": (4, 100.5, 5, 100),
            "unsafe_denominator": (4, 2**53, 5, 100),
            "unsafe_event": (2**53, 2**53 + 2, 5, 100),
        }
        for label, row in malformed.items():
            for matched_cc05 in (False, True):
                with self.subTest(case=label, matched_cc05=matched_cc05):
                    cp = invoke_metafor(
                        (row,) + CASESETS["near_homogeneous"],
                        "RR", "DL", matched_cc05=matched_cc05,
                    )
                    self.assertNotEqual(cp.returncode, 0)
                    self.assertIn("invalid binomial count integrity", cp.stderr)

        # Positive source-domain control: valid integer rows remain eligible
        # under either deliberately selected correction convention.
        for matched_cc05 in (False, True):
            with self.subTest(valid=True, matched_cc05=matched_cc05):
                cp = invoke_metafor(CASESETS["near_homogeneous"],
                                    "RR", "DL", matched_cc05=matched_cc05)
                self.assertEqual(cp.returncode, 0, cp.stderr)
                parse_metafor_result(cp.stdout)

    def test_refuses_unrecognised_correction_modes(self):
        # Never allow a typo to change the quantitative correction silently.
        tab = "tE\ttN\tcE\tcN\n0\t100\t8\t100\n" + "".join(
            "%d\t%d\t%d\t%d\n" % row for row in CASESETS["near_homogeneous"]
        )
        cp = subprocess.run(
            ["Rscript", str(R_SCRIPT), "RR", "DL", "CC01"],
            input=tab, cwd=ROOT, capture_output=True, text=True,
            check=False, timeout=90,
        )
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("usage:", cp.stderr)

    def test_refuses_unmatched_zero_cell_convention(self):
        rows = ((0, 100, 3, 100),) + CASESETS["heterogeneous"]
        for measure in ("RR", "OR"):
            with self.subTest(measure=measure):
                cp = invoke_metafor(rows, measure, "DL")
                self.assertNotEqual(cp.returncode, 0)
                self.assertIn("interior-only", cp.stderr)

    def test_refuses_unsupported_effect_and_estimator(self):
        rows = CASESETS["heterogeneous"]
        for measure, method in (("HR", "DL"), ("RR", "REML"),
                                ("OR", "unversioned")):
            with self.subTest(measure=measure, method=method):
                cp = invoke_metafor(rows, measure, method)
                self.assertNotEqual(cp.returncode, 0)
                self.assertIn("usage:", cp.stderr)

    def test_tamper_and_missing_external_fields_cannot_pass(self):
        good = "\n".join("%s\t1" % key for key in sorted(FIELDS))
        self.assertEqual(set(parse_metafor_result(good)), FIELDS)
        for bad in (good.replace("mu_log\t1\n", ""),
                    good + "\nmu_log\t2",
                    good.replace("mu_log\t1", "mu_log\tNaN"),
                    good + "\nPI\t4"):
            with self.subTest(payload=bad[-40:]):
                with self.assertRaises(ValueError):
                    parse_metafor_result(bad)
        model = dict((key, 1.0) for key in FIELDS)
        with self.assertRaisesRegex(AssertionError, "tau2 differs"):
            match_model(dict(model, tau2=1.1), model)
        # A JSON boolean must not pass as numeric k=1; tiny k mutations
        # cannot hide inside pooled-effect tolerances.
        with self.assertRaisesRegex(AssertionError, "non-finite shipped k_used"):
            match_model(dict(model, k_used=True), model)
        with self.assertRaisesRegex(AssertionError, "k_used differs"):
            match_model(dict(model, k_used=1.000000001), model)
        with self.assertRaisesRegex(AssertionError, "k_used differs"):
            match_model(model, dict(model, k_used=True))
        # False PASS previously: tiny tolerance-compatible changes reversed
        # the pooled log-effect direction, tau2 zero boundary, or CI null
        # crossing. These are synthetic comparator mutation tests, not R runs.
        for key, below, above in (
                ("mu_log", -1e-10, 1e-10),
                ("tau2", 0.0, 1e-10),
                ("ci_lo", 1.0 - 1e-10, 1.0 + 1e-10),
                ("ci_hi", 1.0 - 1e-10, 1.0 + 1e-10)):
            with self.subTest(null_boundary=key):
                with self.assertRaisesRegex(AssertionError, key + " differs"):
                    match_model(dict(model, **{key: below}),
                                dict(model, **{key: above}))
        # Valid same-side numerical drift must remain eligible for tolerance.
        match_model(
            dict(model, mu_log=2e-10, tau2=2e-10,
                 ci_lo=1 - 2e-10, ci_hi=1 + 2e-10),
            dict(model, mu_log=3e-10, tau2=3e-10,
                 ci_lo=1 - 3e-10, ci_hi=1 + 3e-10),
        )


if __name__ == "__main__":
    unittest.main()
