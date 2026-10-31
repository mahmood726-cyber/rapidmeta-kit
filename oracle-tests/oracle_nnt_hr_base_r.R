#!/usr/bin/env Rscript
# Genuine independent base-R 4.4.3 numerical comparator for the
# fixed-time Altman-Andersen HR-to-NNT transform (BMJ 1999;319:1492).
# Synthetic S_control(t) values ONLY. This does not validate the crude
# event-rate proxy in the panel or any original clinical source.
options(warn=2)
if (as.character(getRversion()) != "4.4.3")
  stop("requires R 4.4.3", call.=FALSE)
lines <- readLines(file("stdin"), warn=FALSE)
if (length(lines)<2L || !identical(lines[[1L]],"case\thr\tcontrol_risk"))
  stop("invalid NNT source table",call.=FALSE)
valid_decimal <- function(x) grepl(
  "^[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?$",
  x, perl=TRUE)
cat("case\tnnt\tarr\ttx_risk\tdirection\n")
seen <- character()
for (line in lines[-1L]) {
  fields <- strsplit(line,"\t",fixed=TRUE)[[1L]]
  if (length(fields)!=3L || !nzchar(fields[[1L]]) ||
      fields[[1L]] %in% seen || !all(vapply(fields[-1L],valid_decimal,logical(1L))))
    stop("invalid NNT source fields",call.=FALSE)
  seen <- c(seen,fields[[1L]])
  h <- as.numeric(fields[[2L]])
  risk <- as.numeric(fields[[3L]])
  if (!is.finite(h) || !is.finite(risk) || h<=0 || risk<=0 || risk>=1)
    stop("invalid NNT source values",call.=FALSE)
  logSc <- log1p(-risk)
  # Calculate the treatment event probability and ARR without subtracting
  # two nearly identical probabilities when HR is near one.
  treatment <- -expm1(h*logSc)
  arr <- (1-risk)*expm1((h-1)*logSc)
  if (!is.finite(treatment) || treatment<0 || treatment>1 || !is.finite(arr))
    stop("unrepresentable NNT result",call.=FALSE)
  reciprocal <- if (arr==0) Inf else 1/abs(arr)
  nnt <- if (is.finite(reciprocal)) sprintf("%.17g",reciprocal) else "NA"
  direction <- if (!is.finite(reciprocal)) "null" else
    if (arr>0) "NNTB" else "NNTH"
  cat(paste(fields[[1L]],nnt,sprintf("%.17g",arr),
            sprintf("%.17g",treatment),direction,sep="\t"),"\n",sep="")
}
