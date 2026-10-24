"""An ACTUAL pinned base-R numerical oracle versus the shipped PairwisePool JS.

No fake metafor invocation, no stored baselines, and no fabricated clinical data.
The only positive cases here are deliberately synthetic interior 2x2 tables.
Run on a runner containing R 4.4.3, Node 20.19.5, Python 3.11.9.
"""
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R_SCRIPT = ROOT / "oracle-tests" / "oracle_pairwise.R"
EXPECTED_KEYS = frozenset((
    "k_used", "mu_log", "mu", "tau2", "Q", "I2", "hksjFactor",
    "ci_lo", "ci_hi", "pi_lo", "pi_hi",
))
# Synthetic, independent comparisons (no shared trial participants).
CASESETS = {
    "near_homogeneous": (
        (10, 100, 20, 100),
        (14, 140, 28, 140),
        (20, 200, 40, 200),
        (13, 130, 26, 130),
    ),
    "heterogeneous": (
        (3, 120, 26, 120),
        (41, 130, 16, 135),
        (22, 110, 45, 125),
        (30, 140, 20, 145),
        (8, 130, 35, 130),
    ),
}

JS_SNIPPET = """
require('./assets/vendor/pairwise-pool.js');
const rows = JSON.parse(process.argv[1]);
const opts = JSON.parse(process.argv[2]);
const result = globalThis.PairwisePool.pool2x2(rows, opts);
console.log(JSON.stringify({
 error: result.error || null,
 k_used: result.k_used, mu_log: result.mu_log, mu: result.mu,
 tau2: result.tau2, Q: result.Q, I2: result.I2,
 hksjFactor: result.hksjFactor,
 ci_lo: result.ci_lo, ci_hi: result.ci_hi,
 pi_lo: result.pi_lo, pi_hi: result.pi_hi
}));
"""


def run_js(rows, measure, method):
    trials = [
        {"name": "synthetic-%02d" % i, "tE": a, "tN": n1,
         "cE": c, "cN": n0}
        for i, (a, n1, c, n0) in enumerate(rows, 1)
    ]
    cp = subprocess.run(
        ["node", "-e", JS_SNIPPET, json.dumps(trials),
         json.dumps({"measure": measure, "tau2Method": method})],
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    )
    result = json.loads(cp.stdout)
    if result.get("error"):
        raise AssertionError("shipped JS refused the eligible oracle case: " + result["error"])
    if set(result) != EXPECTED_KEYS | {"error"}:
        raise AssertionError("shipped JS result keys changed")
    return {key: result[key] for key in EXPECTED_KEYS}


def parse_reference(text):
    """Fail closed on missing, duplicate, non-finite or extra R results."""
    fields = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 2 or parts[0] in fields or parts[0] not in EXPECTED_KEYS:
            raise ValueError("invalid/duplicate reference field: " + line)
        try:
            v = float(parts[1])
        except ValueError as exc:
            raise ValueError("non-numeric reference field: " + line) from exc
        if not math.isfinite(v):
            raise ValueError("non-finite reference field: " + line)
        fields[parts[0]] = v
    if fields.keys() != EXPECTED_KEYS:
        raise ValueError("R reference fields are incomplete")
    return fields


def run_r(rows, measure, method):
    tsv = "tE\ttN\tcE\tcN\n" + "".join(
        "%d\t%d\t%d\t%d\n" % row for row in rows
    )
    cp = subprocess.run(
        ["Rscript", str(R_SCRIPT), measure, method],
        input=tsv, cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=30,
    )
    if cp.returncode:
        raise AssertionError("independent R oracle failed (not SKIPPED): "
                             + cp.stderr.strip())
    return parse_reference(cp.stdout)


def compare_results(shipped, reference, endpoint_tolerance=1e-6):
    # Exact method-matching for 2x2 log effects, PM/DL, floored HKSJ,
    # and Cochrane t(k-1) PI. High-precision table for df<=30 and
    # independently R-checked asymptotic expansion for df>30.
    for key in EXPECTED_KEYS:
        a, b = shipped[key], reference[key]
        if not isinstance(a, (int, float)) or not math.isfinite(a):
            raise AssertionError(key + ": non-finite shipped result")
        if key in {"ci_lo", "ci_hi", "pi_lo", "pi_hi"}:
            ok = math.isclose(a, b, rel_tol=endpoint_tolerance,
                              abs_tol=endpoint_tolerance)
        else:
            ok = math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-8)
        if not ok:
            raise AssertionError(
                "%s differs: shipped=%.17g, independent R=%.17g"
                % (key, a, b)
            )


class ActualRPairwiseOracle(unittest.TestCase):
    def test_r_runtime_is_exactly_pinned(self):
        cp = subprocess.run(
            ["Rscript", "-e", 'cat(as.character(getRversion()))'],
            capture_output=True, text=True, check=True, timeout=30,
        )
        self.assertEqual(cp.stdout, "4.4.3")

    def test_synthetic_interior_rr_or_pm_dl_against_actual_r(self):
        # Eight genuinely executed comparisons, not committed snapshot replay.
        for case_name, rows in CASESETS.items():
            for measure in ("RR", "OR"):
                for method in ("PM", "DL"):
                    with self.subTest(case=case_name, measure=measure, method=method):
                        compare_results(
                            run_js(rows, measure, method),
                            run_r(rows, measure, method),
                        )

    def test_high_study_counts_against_actual_r_t_quantiles(self):
        # The former two-term df>30 approximation understated qt(.975, df).
        # Three independent synthetic comparison sets cross RR/OR with DL.
        # This really invokes R 4.4.3; it cannot pass by replaying snapshots.
        for k in (32, 45, 104):  # df 31, 44, 103: below and above 100
            rows = tuple(
                (7 + (i * 11) % 36, 140 + i % 9,
                 11 + (i * 13) % 34, 145 + i % 11)
                for i in range(k)
            )
            for measure in ("RR", "OR"):
                with self.subTest(k=k, measure=measure, method="DL"):
                    compare_results(
                        run_js(rows, measure, "DL"),
                        run_r(rows, measure, "DL"),
                        endpoint_tolerance=1e-7,
                    )

    def test_pm_near_zero_boundary_matches_high_precision_native_r(self):
        # Three deliberately synthetic, very-large-count studies stress the
        # absolute-tolerance defect; these are NOT plausible clinical trials.
        # Q(0) crosses df=2 between deltas 70710 and 70711. The positive
        # Paule-Mandel tau2 root is ~1.8e-15, not ~4.55e-13.
        n = 10_000_000_000
        mid = n // 2

        def rows(delta):
            return (
                (mid + delta, n, mid, n),
                (mid, n, mid, n),
                (mid - delta, n, mid, n),
            )

        below_js = run_js(rows(70710), "RR", "PM")
        below_r = run_r(rows(70710), "RR", "PM")
        self.assertLess(below_r["Q"], 2)
        self.assertEqual(below_js["tau2"], 0)
        self.assertEqual(below_r["tau2"], 0)
        compare_results(below_js, below_r)

        above_js = run_js(rows(70711), "RR", "PM")
        above_r = run_r(rows(70711), "RR", "PM")
        self.assertGreater(above_r["Q"], 2)
        self.assertGreater(above_r["tau2"], 0)
        self.assertLess(above_r["tau2"], 1e-13)
        # The default oracle comparison's 1e-8 absolute tolerance would
        # miss this defect: an explicit small-scale check is required.
        self.assertLess(abs(above_js["tau2"] - above_r["tau2"]), 2e-16)
        compare_results(above_js, above_r)
        # Failure injection: the old prematurely terminated JS root must
        # remain distinguishable from the independently computed R root.
        old_premature_root = 4.547473508864641e-13
        self.assertGreater(abs(old_premature_root - above_r["tau2"]), 1e-13)

    def test_high_df_oracle_fails_on_tampered_prediction_interval(self):
        k = 32
        rows = tuple(
            (7 + (i * 11) % 36, 140 + i % 9,
             11 + (i * 13) % 34, 145 + i % 11)
            for i in range(k)
        )
        shipped = run_js(rows, "RR", "DL")
        independent_r = run_r(rows, "RR", "DL")
        # Deliberately change a numerical endpoint; no silent false PASS.
        forged = dict(shipped, pi_hi=shipped["pi_hi"] * 1.0001)
        with self.assertRaisesRegex(AssertionError, "pi_hi differs"):
            compare_results(forged, independent_r, endpoint_tolerance=1e-7)

    def test_oracle_refuses_unmatched_zero_cell_correction(self):
        # JS applies the configured continuity correction. This oracle does
        # not implement that correction: it must refuse, never fake parity.
        rows = ((0, 100, 3, 100),) + CASESETS["near_homogeneous"]
        for measure in ("RR", "OR"):
            cp = subprocess.run(
                ["Rscript", str(R_SCRIPT), measure, "PM"],
                input="tE\ttN\tcE\tcN\n" +
                      "".join("%d\t%d\t%d\t%d\n" % row for row in rows),
                cwd=ROOT, capture_output=True, text=True,
                check=False, timeout=30,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("interior-only", cp.stderr)

    def test_oracle_rejects_unsupported_estimator(self):
        cp = subprocess.run(
            ["Rscript", str(R_SCRIPT), "HR", "REML"],
            input="tE\ttN\tcE\tcN\n",
            cwd=ROOT, capture_output=True, text=True,
            check=False, timeout=30,
        )
        self.assertNotEqual(cp.returncode, 0)
        self.assertIn("usage:", cp.stderr)

    def test_r_output_integrity_checks_refuse_missing_duplicate_nonfinite(self):
        sample = "\n".join(key + "\t1" for key in sorted(EXPECTED_KEYS))
        self.assertEqual(len(parse_reference(sample)), len(EXPECTED_KEYS))
        for tampered in (
            sample.replace("mu_log\t1\n", ""),
            sample + "\nmu_log\t2",
            sample.replace("mu_log\t1", "mu_log\tNaN"),
            sample + "\nunexpected\t3",
        ):
            with self.subTest(payload=tampered[-45:]):
                with self.assertRaises(ValueError):
                    parse_reference(tampered)

    def test_comparison_refuses_tampered_statistic(self):
        rows = CASESETS["heterogeneous"]
        js = run_js(rows, "RR", "PM")
        truth = run_r(rows, "RR", "PM")
        tampered = dict(js, tau2=js["tau2"] + 0.1)
        with self.assertRaisesRegex(AssertionError, "tau2 differs"):
            compare_results(tampered, truth)


if __name__ == "__main__":
    unittest.main()
