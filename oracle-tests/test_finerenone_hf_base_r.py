"""Native pinned-R numerical cross-check, separate from scientific validation.

CI's native-R job pins R 4.4.3. This test calls Rscript directly with no
third-party R packages to reimplement rounded-input generic inverse-variance
arithmetic. It does not validate RevMan random-effects settings, independent
data extraction, or clinical combinability. Ordinary mixed-estimand pooling
remains forbidden in the RapidMeta clinical path.
"""

from __future__ import annotations

import json
import math
import subprocess
import unittest
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / "research_pilots" / "finerenone_hf_2026_10_26" / "reference.json"

R_CODE = r"""
a <- as.numeric(commandArgs(trailingOnly=TRUE))
if (length(a) < 6 || length(a) %% 3 != 0 || any(!is.finite(a))) stop("Bad R fixture")
point <- a[seq(1,length(a),by=3)]
lower <- a[seq(2,length(a),by=3)]
upper <- a[seq(3,length(a),by=3)]
if (any(lower <= 0 | point <= lower | upper <= point)) stop("Bad R log confidence interval")
yi <- log(point)
vi <- ((log(upper) - log(lower)) / (2 * 1.96))^2
wi <- 1 / vi
mu0 <- sum(wi * yi) / sum(wi)
q <- sum(wi * (yi - mu0)^2)
cval <- sum(wi) - sum(wi * wi) / sum(wi)
tau2 <- if (length(yi) > 1 && cval > 0) max(0, (q - (length(yi)-1)) / cval) else 0
wr <- 1 / (vi + tau2)
mu <- sum(wr * yi) / sum(wr)
se <- sqrt(1 / sum(wr))
finearts_weight <- 100 * wr[length(wr)] / sum(wr)
out <- c(exp(mu), exp(mu - 1.96*se), exp(mu + 1.96*se), tau2, finearts_weight)
cat(paste(format(out, digits=17, scientific=FALSE, trim=TRUE), collapse=","))
"""


def independent_base_r(trials: list[dict]) -> tuple[float, ...]:
    if not trials:
        raise ValueError("Missing R inputs")
    params = [str(t[field]) for t in trials for field in ("effect", "ci_lower", "ci_upper")]
    p = subprocess.run(["Rscript", "--vanilla", "-e", R_CODE, *params],
                       check=True, capture_output=True, text=True, timeout=45)
    values = tuple(float(v) for v in p.stdout.strip().split(","))
    if len(values) != 5 or not all(math.isfinite(v) for v in values):
        raise RuntimeError(f"Bad R output: {p.stdout}")
    return values


class HumanFinerenoneExternalArithmeticOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = json.loads(REFERENCE.read_text(encoding="utf-8"))

    def test_declared_native_R_version_is_pinned_in_job(self):
        p = subprocess.run(["Rscript", "--version"], capture_output=True, text=True, check=True, timeout=10)
        self.assertIn("4.4.3", p.stdout + p.stderr)

    def test_mixed_hf_arithmetic_is_replay_only(self):
        e, lo, hi, tau, finearts_weight = independent_base_r(self.ref["trials"])
        self.assertAlmostEqual(e, .804461750164, delta=1e-9)
        self.assertAlmostEqual(lo, .722790562037, delta=1e-9)
        self.assertAlmostEqual(hi, .895361314145, delta=1e-9)
        self.assertAlmostEqual(tau, 0, delta=1e-12)
        self.assertGreater(finearts_weight, 50)
        self.assertEqual(self.ref["evidence_gates"]["clinically_combinable_primary_endpoint"], "BLOCKED")
        self.assertEqual(self.ref["evidence_gates"]["method_matched_version_pinned_R_oracle"], "NOT_RUN")

    def test_cv_death_reported_vs_original_CI_are_numerically_distinct(self):
        s = self.ref["cv_death_interval_sensitivity"]
        forest = independent_base_r(s["forest_based_approx"]["effects"])
        trial = independent_base_r(s["source_primary_trial_approx"]["effects"])
        self.assertAlmostEqual(forest[0], .907855917311, delta=1e-9)
        self.assertAlmostEqual(forest[1], .820191467681, delta=1e-9)
        self.assertAlmostEqual(forest[2], 1.004890198293, delta=1e-9)
        self.assertAlmostEqual(trial[0], .902371833898, delta=1e-9)
        self.assertAlmostEqual(trial[1], .805471717271, delta=1e-9)
        self.assertAlmostEqual(trial[2], 1.010929259406, delta=1e-9)
        self.assertAlmostEqual(forest[3], 0, delta=1e-12)
        self.assertAlmostEqual(trial[3], 0, delta=1e-12)
        self.assertGreater(forest[4] - trial[4], 11)
        self.assertEqual(s["version_pinned_external_oracle"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
