"""Live, method-matched metafor 4.8-0 oracle for shipped PairwisePool.

This test MUST run native R. It is deliberately separate from our self-written
base-R oracle and cannot pass from stored/cached numerical anchors.
Scope: synthetic, independent interior 2x2 tables, RR/OR, DL/PM, floored
HKSJ. The separate Cochrane PI and I2 conventions are NOT asserted equal
to metafor. Zero-cell policies, REML and published clinical data NOT TESTED.
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


def invoke_metafor(rows, measure, method):
    tab = "tE\ttN\tcE\tcN\n" + "".join(
        "%d\t%d\t%d\t%d\n" % row for row in rows
    )
    return subprocess.run(
        ["Rscript", str(R_SCRIPT), measure, method],
        input=tab, cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=90,
    )


def match_model(js_result, r_result):
    for key in FIELDS:
        value = js_result[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise AssertionError("non-finite shipped " + key)
        # The externally implemented PM solver need not converge bitwise to
        # the JS bisection. This is a stated numerical, not semantic, bound.
        tolerance = 3e-6 if key in ("tau2", "ci_lo", "ci_hi") else 1e-8
        if not math.isclose(value, r_result[key],
                            rel_tol=tolerance, abs_tol=tolerance):
            raise AssertionError(
                "%s differs: JS=%.17g metafor=%.17g" %
                (key, value, r_result[key])
            )


class ActualMetaforOracle(unittest.TestCase):
    def test_external_package_and_r_versions_are_pinned(self):
        cp = subprocess.run(
            ["Rscript", "-e",
             'stopifnot(as.character(getRversion())=="4.4.3"); '
             'stopifnot(as.character(packageVersion("metafor"))=="4.8-0"); '
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


if __name__ == "__main__":
    unittest.main()
