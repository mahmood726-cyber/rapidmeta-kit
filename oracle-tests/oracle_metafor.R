#!/usr/bin/env Rscript
# External, version-pinned metafor oracle: NOT base-R self-reference.
# Scope: independent interior 2x2 studies plus explicitly matched per-study
# 0.5 continuity correction, RR/OR, DL/PM, and 95% floored HKSJ.
# Synthetic inputs only; NOT REML, GLMM, multi-arm, or trial validation.
options(warn = 2)
if (as.character(getRversion()) != "4.4.3") {
  stop("requires exactly R 4.4.3", call. = FALSE)
}
if (!requireNamespace("metafor", quietly = TRUE) ||
    utils::packageDescription("metafor", fields = "Version") != "4.8-0") {
  stop("requires exactly metafor 4.8-0 (never skip)", call. = FALSE)
}
args <- commandArgs(trailingOnly = TRUE)
if (!(length(args) %in% c(2L, 3L)) || !args[1L] %in% c("RR", "OR") ||
    !args[2L] %in% c("DL", "PM") ||
    (length(args) == 3L && args[3L] != "CC05")) {
  stop("usage: Rscript oracle_metafor.R RR|OR DL|PM [CC05]", call. = FALSE)
}
# The opt-in CC05 mode matches shipped PairwisePool's per-study all-four-cell
# correction, and deliberately does NOT attempt to arbitrate which correction
# is clinically appropriate for rare events. It MUST never be implicit.
matched_cc05 <- length(args) == 3L
d <- read.table(file("stdin"), header = TRUE, sep = "\t",
                check.names = FALSE, stringsAsFactors = FALSE)
if (!identical(names(d), c("tE", "tN", "cE", "cN")) ||
    nrow(d) < 2L || anyNA(d) ||
    !all(vapply(d, is.numeric, logical(1L))) ||
    any(!is.finite(as.matrix(d)))) {
  stop("requires >=2 complete finite 2x2 rows", call. = FALSE)
}
# Match the shipped JavaScript count-domain contract *before* metafor::escalc.
# Event and participant counts are integers, not fractional observations;
# JS Number.isSafeInteger refuses numbers above 2^53-1. Without this gate
# the two oracle interfaces could disagree about whether input is eligible.
count_matrix <- as.matrix(d)
if (any(count_matrix != trunc(count_matrix)) ||
    any(abs(count_matrix) > 9007199254740991)) {
  stop("invalid binomial table: requires safe integer raw counts", call. = FALSE)
}
# Refuse malformed tables before any escalc correction can make them appear
# estimable.
if (any(d$tN <= 0 | d$cN <= 0 | d$tE < 0 | d$cE < 0 |
        d$tE > d$tN | d$cE > d$cN)) {
  stop("invalid binomial table: refusing correction", call. = FALSE)
}
# Both-zero and both-full tables are excluded in the JS module. The oracle
# cannot silently include them as if they were matched; reject whole request.
if (matched_cc05 && any((d$tE == 0 & d$cE == 0) |
                         (d$tE == d$tN & d$cE == d$cN))) {
  stop("CC05 refuses uninformative dual-arm table; JS exclusion policy not reproduced",
       call. = FALSE)
}
# Without explicit CC05, keep the original interior-only protection.
if (!matched_cc05 && any(d$tE <= 0 | d$tE >= d$tN |
                          d$cE <= 0 | d$cE >= d$cN)) {
  stop("interior-only: correction convention not matched", call. = FALSE)
}
es <- metafor::escalc(
  measure = args[1L],
  ai = d$tE, bi = d$tN - d$tE,
  ci = d$cE, di = d$cN - d$cE,
  add = if (matched_cc05) 0.5 else 0,
  to = if (matched_cc05) "only0" else "none", drop00 = FALSE
)
if (any(!is.finite(es$yi)) || any(!is.finite(es$vi)) ||
    any(es$vi <= 0)) {
  stop("non-finite effect/variance", call. = FALSE)
}
# test="adhoc" in metafor enforces the same non-shrinking HKSJ SE
# (floor at the unadjusted SE) as PairwisePool's max(1,qstar).
# metafor's default PM uniroot tol=.Machine$double.eps^0.25 is
# materially looser than the JS bisection on heterogeneous synthetic data.
# Source-documented control$tol, not a relaxed comparison threshold.
fit <- metafor::rma.uni(yi = es$yi, vi = es$vi,
                        method = args[2L], test = "adhoc", level = 95,
                        control = list(tol = 1e-12, maxiter = 500))
result <- c(
  k_used = fit$k,
  mu_log = as.numeric(fit$beta),
  tau2 = fit$tau2,
  Q = fit$QE,
  ci_lo = exp(fit$ci.lb),
  ci_hi = exp(fit$ci.ub)
)
if (any(!is.finite(result))) {
  stop("non-finite metafor reference result", call. = FALSE)
}
cat(paste(names(result), sprintf("%.17g", result), sep = "\t"), sep = "\n")
