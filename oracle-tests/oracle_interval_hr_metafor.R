#!/usr/bin/env Rscript
# Genuine external, explicitly method-matched R oracle for synthetic interval HR.
# k=1: normal single-study interval, no meta-analysis; k>=2:
# metafor 4.8-0 (REML + test="adhoc" floor) under R 4.4.3.
# NOT a published-study validation, NMA, original-data audit or survival IPD fit.
options(warn = 2)
if (as.character(getRversion()) != "4.4.3" ||
    !requireNamespace("metafor", quietly = TRUE) ||
    utils::packageDescription("metafor", fields = "Version") != "4.8-0") {
  stop("requires exactly R 4.4.3 and metafor 4.8-0", call. = FALSE)
}
if (length(commandArgs(trailingOnly = TRUE)) != 0L)
  stop("no command-line model overrides permitted", call. = FALSE)

# Require a literal decimal or scientific-notation number in each source
# numeric field BEFORE read.table() can type-convert R hexadecimal literals.
# A non-decimal source token is not an independently verified ratio or month.
raw_lines <- readLines(file("stdin"), warn = FALSE)
decimal_pattern <- "^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
fields <- if (length(raw_lines) > 1L) {
  strsplit(raw_lines[-1L], "\t", fixed = TRUE)
} else list()
valid_fields <- length(fields) > 0L && all(vapply(fields, function(x) {
  length(x) == 6L && all(grepl(decimal_pattern, trimws(x[2:6]), perl = TRUE))
}, logical(1L)))
if (!valid_fields)
  stop("invalid or incomplete interval-HR source table", call. = FALSE)
d <- read.table(text = paste(raw_lines, collapse = "\n"), header = TRUE,
                sep = "\t", quote = "", check.names = FALSE,
                stringsAsFactors = FALSE)
required <- c("trial", "t0", "t1", "HR", "lo", "hi")
if (!identical(names(d), required) || nrow(d) < 1L ||
    anyNA(d) || any(!nzchar(trimws(d$trial))) ||
    !all(vapply(d[-1L], is.numeric, logical(1L))) ||
    any(!is.finite(as.matrix(d[-1L]))) ||
    any(d$t0 < 0 | d$t1 <= d$t0 | d$HR <= 0 | d$lo <= 0 |
        d$hi <= d$lo | d$HR < d$lo | d$HR > d$hi)) {
  stop("invalid or incomplete interval-HR source table", call. = FALSE)
}
# Preserve distinct follow-up windows; never count one study twice per window.
# Match the shipped JS stable-ID gate: outer whitespace and letter case
# cannot turn one canonical study into multiple independent observations.
id <- paste(tolower(trimws(d$trial)), d$t0, d$t1, sep = "\t")
if (anyDuplicated(id) > 0L)
  stop("duplicate trial/time-window evidence: refusing pool", call. = FALSE)
# Treat the union of all reported source boundaries as the candidate
# analysis partition, as the shipped browser panel does.  A trial's [0,6]
# summary HR cannot be redistributed across [0,3] and [3,6] merely because
# other trials report those shorter periods. Reject incompatible windows
# BEFORE printing any apparently valid pooled results.
boundaries <- sort(unique(c(d$t0, d$t1)))
start_index <- match(d$t0, boundaries)
end_index <- match(d$t1, boundaries)
if (any(end_index != start_index + 1L))
  stop("non-aligned interval-HR source windows: refusing partial pooled evidence",
       call. = FALSE)
d <- d[order(d$t0, d$t1, d$trial), , drop = FALSE]
key <- paste(d$t0, d$t1, sep = "-")
windows <- unique(key)
cat("t0\tt1\tk\tHR\tci_lo\tci_hi\ttau2\n")
for (w in windows) {
  sub <- d[key == w, , drop = FALSE]
  if (nrow(sub) < 1L)
    stop("empty source window", call. = FALSE)
  yi <- log(sub$HR)
  # Exactly the shipped JS logHRfromCI convention for a two-sided 95% CI.
  se <- (log(sub$hi) - log(sub$lo)) / (2 * 1.959963984540054)
  vi <- se^2
  if (any(!is.finite(yi) | !is.finite(vi) | vi <= 0))
    stop("invalid log-HR or within-study variance", call. = FALSE)
  if (nrow(sub) == 1L) {
    # Independent base-R normal interval. Deliberately does not invoke
    # metafor::rma.uni at k=1 or pretend that heterogeneity was estimated.
    z <- stats::qnorm(0.975)
    values <- c(sub$t0[1], sub$t1[1], 1L, exp(yi[1]),
                exp(yi[1] - z * sqrt(vi[1])),
                exp(yi[1] + z * sqrt(vi[1])), 0)
  } else {
    # k=2 is a genuine two-study REML + floored HKSJ/t(1) comparison;
    # it must not be silently treated as single-study normal inference.
    fit <- metafor::rma.uni(yi = yi, vi = vi, method = "REML",
                            test = "adhoc", level = 95,
                            control = list(tol = 1e-12, maxiter = 500))
    values <- c(sub$t0[1], sub$t1[1], nrow(sub), exp(as.numeric(fit$beta)),
                exp(fit$ci.lb), exp(fit$ci.ub), fit$tau2)
  }
  if (any(!is.finite(values)))
    stop("nonfinite external interval-HR estimate", call. = FALSE)
  # Exponentiation can underflow to zero while remaining finite. A zero
  # HR/CI endpoint is not a representable positive ratio: fail closed.
  if (any(values[c(4L, 5L, 6L)] <= 0) ||
      values[5L] > values[4L] || values[4L] > values[6L] ||
      values[7L] < 0)
    stop("unrepresentable external interval-HR ratio or confidence limits",
         call. = FALSE)
  cat(paste(sprintf("%.17g", values), collapse = "\t"), "\n", sep = "")
}
