#!/usr/bin/env Rscript
# Independently implemented, base-R-only reference for interior 2x2 tables.
# Tested: RR/OR, PM/DL tau^2, floored HKSJ CI, Cochrane k-1 PI.
# This is NOT an invocation of metafor and must not be reported as metafor parity.
# R 4.4.3 is enforced by CI and this entry point. No packages are installed.
options(warn = 2)
stopifnot(as.character(getRversion()) == "4.4.3")

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L || !args[1L] %in% c("RR", "OR") ||
    !args[2L] %in% c("PM", "DL")) {
  stop("usage: Rscript oracle_pairwise.R RR|OR PM|DL", call. = FALSE)
}
measure <- args[1L]
tau_method <- args[2L]
d <- read.table(file("stdin"), header = TRUE, sep = "\t",
                check.names = FALSE, stringsAsFactors = FALSE)
if (!identical(names(d), c("tE", "tN", "cE", "cN")) ||
    nrow(d) < 3L || anyNA(d) || !all(vapply(d, is.numeric, logical(1L))) ||
    any(!is.finite(as.matrix(d)))) {
  stop("oracle requires >=3 complete finite 2x2 rows", call. = FALSE)
}
# The source-domain contract is discrete binomial counts. Refuse fractional
# and IEEE-754-unsafe values before effect or variance calculations; otherwise
# a malformed source could look like a valid interior 2x2 table.
counts <- as.matrix(d)
if (any(counts != floor(counts)) || any(counts < 0) ||
    any(counts > 9007199254740991)) {
  stop("invalid binomial count integrity: require safe integers", call. = FALSE)
}
if (any(d$tE <= 0 | d$tE >= d$tN |
        d$cE <= 0 | d$cE >= d$cN)) {
  stop("interior-only oracle: reject zero/all event cells (no matched correction)", call. = FALSE)
}

a <- d$tE
b <- d$tN - d$tE
cc <- d$cE
dd <- d$cN - d$cE
if (measure == "RR") {
  yi <- log((a / d$tN) / (cc / d$cN))
  vi <- 1 / a - 1 / d$tN + 1 / cc - 1 / d$cN
} else {
  yi <- log(a * dd / (b * cc))
  vi <- 1 / a + 1 / b + 1 / cc + 1 / dd
}
if (any(!is.finite(yi)) || any(!is.finite(vi)) || any(vi <= 0)) {
  stop("invalid study-level log effects or variances", call. = FALSE)
}
k <- length(yi)
df <- k - 1L
w_fe <- 1 / vi
mu_fe <- sum(w_fe * yi) / sum(w_fe)
Q <- sum(w_fe * (yi - mu_fe)^2)

q_general <- function(t2) {
  w <- 1 / (vi + t2)
  m <- sum(w * yi) / sum(w)
  sum(w * (yi - m)^2)
}
if (tau_method == "DL") {
  # Independent base-R implementation of the algebraically equivalent
  # cross-weight DL denominator, avoiding subtraction of almost equal values.
  products <- outer(w_fe, w_fe, "*")
  C <- 2 * sum(products[upper.tri(products)]) / sum(w_fe)
  tau2 <- max(0, (Q - df) / C)
} else if (Q <= df) {
  tau2 <- 0
} else {
  hi <- 1
  while (q_general(hi) > df && hi < 2^100) hi <- 2 * hi
  if (q_general(hi) > df) stop("PM failed to bracket tau2", call. = FALSE)
  tau2 <- uniroot(function(x) q_general(x) - df,
                  interval = c(0, hi), tol = 1e-20)$root
}
w_re <- 1 / (vi + tau2)
mu_log <- sum(w_re * yi) / sum(w_re)
se_mu <- sqrt(1 / sum(w_re))
q_star <- sum(w_re * (yi - mu_log)^2) / df
hksj_factor <- max(1, q_star)
t_crit <- stats::qt(0.975, df)
ci_half <- t_crit * se_mu * sqrt(hksj_factor)
pi_half <- t_crit * sqrt(tau2 + se_mu^2)
I2 <- if (Q <= 0) 0 else max(0, (Q - df) / Q) * 100
result <- c(
  k_used = k, mu_log = mu_log, mu = exp(mu_log),
  tau2 = tau2, Q = Q, I2 = I2, hksjFactor = hksj_factor,
  ci_lo = exp(mu_log - ci_half), ci_hi = exp(mu_log + ci_half),
  pi_lo = exp(mu_log - pi_half), pi_hi = exp(mu_log + pi_half)
)
if (any(!is.finite(result))) stop("non-finite reference output", call. = FALSE)
cat(paste(names(result), sprintf("%.17g", result), sep = "\t"), sep = "\n")
