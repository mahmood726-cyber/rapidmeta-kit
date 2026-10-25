#!/usr/bin/env Rscript
# Synthesis | Live continuous MD/SMD reference, synthetic input ONLY.
# Test runner pins R 4.4.3 and SHA256-verified metafor 4.8-0.
# This independently runs metafor::escalc and metafor::rma on raw arm data.
# It does not validate study extraction, clinical combinability, or source accuracy.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L || !args[[1L]] %in% c("MD", "SMD")) {
  stop("requires explicit MD or SMD", call. = FALSE)
}
if (as.character(getRversion()) != "4.4.3" ||
    as.character(packageVersion("metafor")) != "4.8.0") {
  stop("continuous oracle requires pinned R 4.4.3 / metafor 4.8-0",
       call. = FALSE)
}
d <- read.delim(file("stdin"), sep = "\t", header = TRUE,
                check.names = FALSE, stringsAsFactors = FALSE)
expected <- c("mean1", "mean2", "sd1", "sd2", "n1", "n2")
if (!identical(names(d), expected) || nrow(d) < 2L ||
    !all(vapply(d, is.numeric, logical(1L))) ||
    !all(vapply(d, function(x) all(is.finite(x)), logical(1L))) ||
    any(d$sd1 <= 0) || any(d$sd2 <= 0) ||
    any(d$n1 <= 1) || any(d$n2 <= 1) ||
    any(d$n1 != floor(d$n1)) || any(d$n2 != floor(d$n2)) ||
    any(d$n1 > 9007199254740991) || any(d$n2 > 9007199254740991)) {
  stop("requires >=2 finite complete raw continuous rows with positive SD and safe integer N>1",
       call. = FALSE)
}
e <- metafor::escalc(
  measure = args[[1L]], vtype = "LS", correct = TRUE,
  m1i = d$mean1, m2i = d$mean2,
  sd1i = d$sd1, sd2i = d$sd2, n1i = d$n1, n2i = d$n2
)
if (any(!is.finite(e$yi)) || any(!is.finite(e$vi)) || any(e$vi <= 0)) {
  stop("metafor returned invalid continuous study effects", call. = FALSE)
}
fit <- metafor::rma(yi = e$yi, vi = e$vi, method = "REML", test = "adhoc")
emit <- function(name, value) {
  value <- as.numeric(value)
  if (length(value) != 1L || !is.finite(value)) {
    stop(paste("nonfinite oracle result", name), call. = FALSE)
  }
  cat(sprintf("%s\t%.17g\n", name, value))
}
for (i in seq_len(nrow(d))) {
  emit(paste0("study_", i - 1L, "_yi"), e$yi[[i]])
  emit(paste0("study_", i - 1L, "_vi"), e$vi[[i]])
}
pred <- predict(fit, level = 95)
emit("k", nrow(d))
emit("mu", fit$b[1, 1])
emit("tau2", fit$tau2)
emit("se", fit$se[1])
emit("ci_low", fit$ci.lb[1])
emit("ci_high", fit$ci.ub[1])
emit("pi_low", pred$pi.lb[1])
emit("pi_high", pred$pi.ub[1])
