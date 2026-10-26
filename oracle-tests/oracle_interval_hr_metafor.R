#!/usr/bin/env Rscript
# Genuine external, explicitly method-matched R oracle for synthetic interval HR.
# Uses metafor 4.8-0 (REML + test="adhoc" floor) under R 4.4.3.
# NOT a published-study validation, NMA, original-data audit or survival IPD fit.
options(warn = 2)
if (as.character(getRversion()) != "4.4.3" ||
    !requireNamespace("metafor", quietly = TRUE) ||
    utils::packageDescription("metafor", fields = "Version") != "4.8-0") {
  stop("requires exactly R 4.4.3 and metafor 4.8-0", call. = FALSE)
}
if (length(commandArgs(trailingOnly = TRUE)) != 0L)
  stop("no command-line model overrides permitted", call. = FALSE)

d <- read.table(file("stdin"), header = TRUE, sep = "\t", quote = "",
                check.names = FALSE, stringsAsFactors = FALSE)
required <- c("trial", "t0", "t1", "HR", "lo", "hi")
if (!identical(names(d), required) || nrow(d) < 3L ||
    anyNA(d) || any(!nzchar(d$trial)) ||
    !all(vapply(d[-1L], is.numeric, logical(1L))) ||
    any(!is.finite(as.matrix(d[-1L]))) ||
    any(d$t0 < 0 | d$t1 <= d$t0 | d$HR <= 0 | d$lo <= 0 |
        d$hi <= d$lo | d$HR < d$lo | d$HR > d$hi)) {
  stop("invalid or incomplete interval-HR source table", call. = FALSE)
}
# Preserve distinct follow-up windows; never count one study twice per window.
id <- paste(d$trial, d$t0, d$t1, sep = "\t")
if (anyDuplicated(id) > 0L)
  stop("duplicate trial/time-window evidence: refusing pool", call. = FALSE)
d <- d[order(d$t0, d$t1, d$trial), , drop = FALSE]
key <- paste(d$t0, d$t1, sep = "-")
windows <- unique(key)
cat("t0\tt1\tk\tHR\tci_lo\tci_hi\ttau2\n")
for (w in windows) {
  sub <- d[key == w, , drop = FALSE]
  if (nrow(sub) < 3L)
    stop("requires at least three independent studies per window", call. = FALSE)
  yi <- log(sub$HR)
  # Exactly the shipped JS logHRfromCI convention for a two-sided 95% CI.
  se <- (log(sub$hi) - log(sub$lo)) / (2 * 1.959963984540054)
  vi <- se^2
  if (any(!is.finite(yi) | !is.finite(vi) | vi <= 0))
    stop("invalid log-HR or within-study variance", call. = FALSE)
  fit <- metafor::rma.uni(yi = yi, vi = vi, method = "REML",
                          test = "adhoc", level = 95,
                          control = list(tol = 1e-12, maxiter = 500))
  values <- c(sub$t0[1], sub$t1[1], nrow(sub), exp(as.numeric(fit$beta)),
              exp(fit$ci.lb), exp(fit$ci.ub), fit$tau2)
  if (any(!is.finite(values)))
    stop("nonfinite external interval-HR estimate", call. = FALSE)
  cat(paste(sprintf("%.17g", values), collapse = "\t"), "\n", sep = "")
}
