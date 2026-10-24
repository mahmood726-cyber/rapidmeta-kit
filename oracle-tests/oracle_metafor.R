#!/usr/bin/env Rscript
# External, version-pinned metafor oracle: NOT base-R self-reference.
# Scope: independent interior 2x2 studies, RR/OR, DL/PM, 95% floored HKSJ.
# Synthetic inputs only. No rare-event correction, REML, or trial validation.
options(warn = 2)
if (as.character(getRversion()) != "4.4.3") {
  stop("requires exactly R 4.4.3", call. = FALSE)
}
if (!requireNamespace("metafor", quietly = TRUE) ||
    as.character(utils::packageVersion("metafor")) != "4.8-0") {
  stop("requires exactly metafor 4.8-0 (never skip)", call. = FALSE)
}
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L || !args[1L] %in% c("RR", "OR") ||
    !args[2L] %in% c("DL", "PM")) {
  stop("usage: Rscript oracle_metafor.R RR|OR DL|PM", call. = FALSE)
}
d <- read.table(file("stdin"), header = TRUE, sep = "\t",
                check.names = FALSE, stringsAsFactors = FALSE)
if (!identical(names(d), c("tE", "tN", "cE", "cN")) ||
    nrow(d) < 3L || anyNA(d) ||
    !all(vapply(d, is.numeric, logical(1L))) ||
    any(!is.finite(as.matrix(d)))) {
  stop("requires >=3 complete finite 2x2 rows", call. = FALSE)
}
# No unspecified or mismatched continuity correction is ever allowed.
if (any(d$tE <= 0 | d$tE >= d$tN |
        d$cE <= 0 | d$cE >= d$cN)) {
  stop("interior-only: correction convention not matched", call. = FALSE)
}
es <- metafor::escalc(
  measure = args[1L],
  ai = d$tE, bi = d$tN - d$tE,
  ci = d$cE, di = d$cN - d$cE,
  add = 0, to = "none", drop00 = FALSE
)
if (any(!is.finite(es$yi)) || any(!is.finite(es$vi)) ||
    any(es$vi <= 0)) {
  stop("non-finite effect/variance", call. = FALSE)
}
# test="adhoc" in metafor enforces the same non-shrinking HKSJ SE
# (floor at the unadjusted SE) as PairwisePool's max(1,qstar).
fit <- metafor::rma.uni(yi = es$yi, vi = es$vi,
                        method = args[2L], test = "adhoc", level = 95)
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
