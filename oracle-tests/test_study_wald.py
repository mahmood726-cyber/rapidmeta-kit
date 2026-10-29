"""Actual native-R 4.4.3 oracle for per-study 2x2 Wald 95% CIs.

Executes independent base-R RR/OR log effect, variance and stats::qnorm.
Not metafor/REML parity, rare-event correction validation or clinical data.
"""
import json
import math
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = (
    (2, 23, 8, 29),
    (5, 40, 11, 44),
    (12, 80, 6, 75),
)
NODE = """
require('./assets/vendor/pairwise-pool.js');
const rows = JSON.parse(process.argv[1]);
const result = globalThis.PairwisePool.pool2x2(rows,
    {measure: process.argv[2], tau2Method: 'PM'});
console.log(JSON.stringify({error: result.error || null,
                            perStudy: result.perStudy}));
"""
R_REFERENCE = r"""
options(warn=2)
stopifnot(as.character(getRversion()) == "4.4.3")
args <- commandArgs(trailingOnly=TRUE)
if (length(args)!=1L || !args[1L] %in% c("RR", "OR"))
    stop("unsupported measure", call.=FALSE)
d <- read.table(file("stdin"), header=TRUE, sep="\t", check.names=FALSE)
if (!identical(names(d), c("tE","tN","cE","cN")) || nrow(d)<3L ||
    anyNA(d) || any(!is.finite(as.matrix(d))) ||
    any(d$tE<=0 | d$tE>=d$tN | d$cE<=0 | d$cE>=d$cN))
    stop("interior-only 2x2 rows required", call.=FALSE)
a <- d$tE
c0 <- d$cE
b <- d$tN-a
dd <- d$cN-c0
if (args[1L]=="RR") {
    yi <- log((a/d$tN)/(c0/d$cN))
    vi <- 1/a-1/d$tN+1/c0-1/d$cN
} else {
    yi <- log((a*dd)/(b*c0))
    vi <- 1/a+1/b+1/c0+1/dd
}
if (any(!is.finite(yi)) || any(!is.finite(vi)) || any(vi<=0))
    stop("invalid log effects or variances", call.=FALSE)
z <- stats::qnorm(0.975)
lo <- exp(yi-z*sqrt(vi))
hi <- exp(yi+z*sqrt(vi))
cat(paste(sprintf("%.17g",lo),sprintf("%.17g",hi),sep="\t"),sep="\n")
"""


def run_r(rows, measure):
    tsv = "tE\ttN\tcE\tcN\n" + "".join(
        "%d\t%d\t%d\t%d\n" % row for row in rows
    )
    return subprocess.run(
        ["Rscript", "-e", R_REFERENCE, measure],
        input=tsv, cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=30,
    )


def run_node(rows, measure):
    trials = [
        {"name": "synthetic-%02d" % i, "tE": a, "tN": n1,
         "cE": c, "cN": n0}
        for i, (a, n1, c, n0) in enumerate(rows, 1)
    ]
    cp = subprocess.run(
        ["node", "-e", NODE, json.dumps(trials), measure],
        cwd=ROOT, capture_output=True, text=True,
        check=True, timeout=30,
    )
    obj = json.loads(cp.stdout)
    if obj["error"]:
        raise AssertionError("unexpected JS refusal: " + obj["error"])
    return obj["perStudy"]


class ActualRStudyWaldOracle(unittest.TestCase):
    def test_rr_or_study_wald_limits_match_native_r_qnorm(self):
        for measure in ("RR", "OR"):
            with self.subTest(measure=measure):
                r = run_r(ROWS, measure)
                self.assertEqual(r.returncode, 0, r.stderr)
                lines = r.stdout.strip().splitlines()
                self.assertEqual(len(lines), len(ROWS))
                js = run_node(ROWS, measure)
                self.assertEqual(len(js), len(ROWS))
                for rec, line in zip(js, lines):
                    parts = line.split("\t")
                    self.assertEqual(len(parts), 2)
                    low, high = map(float, parts)
                    for key, ref in (("ci_lo", low), ("ci_hi", high)):
                        self.assertTrue(math.isfinite(ref))
                        self.assertTrue(math.isclose(rec[key], ref,
                            rel_tol=2e-13, abs_tol=2e-13),
                            "%s %s JS=%s native-R=%s" %
                            (measure, key, rec[key], ref))

    def test_oracle_refuses_unmatched_boundary_or_effect(self):
        bad_rows = ((0, 23, 8, 29),) + ROWS[1:]
        for rows, measure, message in (
            (bad_rows, "RR", "interior-only"),
            (ROWS, "HR", "unsupported measure"),
        ):
            with self.subTest(measure=measure, rows=rows[0]):
                r = run_r(rows, measure)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(message, r.stderr)


if __name__ == "__main__":
    unittest.main()
