# Independent base-R pairwise numerical oracle (experimental)

This directory addresses the **absence of a genuinely executed R reference in CI**. The pre-existing `tests/r_parity_harness.cjs` is ported dashboard JavaScript, **not R**. Its baseline and published numerical anchors are valuable but must not be relabelled as live R parity.

The new isolated CI job runs **R 4.4.3** (base `stats`, no CRAN packages), Python 3.11.9 and Node 20.19.5 on Ubuntu 24.04. GitHub Actions themselves are pinned to immutable action commits in `.github/workflows/ci.yml`. The job fails if R is missing or the version is not exactly 4.4.3. It does not silently skip the test. Run locally with these three runtimes installed:

```sh
python -m unittest discover -s oracle-tests -p 'test_*.py' -v
```

**What it actually compares:** the shipped `assets/vendor/pairwise-pool.js` output versus a separately implemented base-R calculation of inverse-variance log-RR/log-OR, Q, I², PM/DL between-study variance, random-effects mean, floored Hartung–Knapp–Sidik–Jonkman 95% CI and a Cochrane `t(k-1)` prediction interval. Two clearly synthetic, independent-comparison input sets are crossed with RR/OR and PM/DL (eight live R executions). There are also failure-injection assertions for rejected unsupported methods, intentionally unmatched zero-cell corrections, corrupted R output and numerical tampering.

**Method/tolerance contract:** raw binomial tables with strictly positive counts in every cell, at least three studies, 95% intervals, inverse-variance random effects. For the raw log-scale estimators, tolerance is 1e-8 absolute/relative. On the exponentiated CI/PI endpoints, the tolerance is 1e-3 absolute or 5e-4 relative, explicitly allowing the JS module's three-decimal t critical-value lookup. Those tolerances are not a claim of bitwise equality. PM uses generalized-Q inversion in independently implemented base R; DL uses the moment formula. When `tau2=0`, the convention makes the PI match the floored HKSJ CI.

**Not yet tested by this suite:** real trial extraction; numerical accuracy of continuity corrections and unequal-arm rare events; REML; direct `metafor::rma.uni` or RevMan execution; multi-arm covariance; Meta-Harness end-to-end interoperability; external clinical validation; Windows/macOS. The fixed R version does not pin the operating-system image to a digest; the Ubuntu runner image may change. Report these as **NOT TESTED**. Do not compare these cases to `metafor` results obtained with `test="knha"` without first matching the floor convention.

Methods: [Cochrane Handbook Chapter 10, §10.10.4.3](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-10); [metafor discussion of PM and HKSJ](https://wviechtb.github.io/metafor/reference/misc-recs.html); [R `stats::qt` documentation](https://search.r-project.org/R/refmans/stats/help/qt.html). This is **independent base R**, not a `metafor` parity claim.
