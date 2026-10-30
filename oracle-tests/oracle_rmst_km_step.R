#!/usr/bin/env Rscript
# Independent base-R 4.4.3 comparator: integrate synthetic KM step points.
# This does not fit censoring data, reconstruct original trial curves, or
# estimate any RMST sampling variance. It is NOT full survRM2 parity.
options(warn=2)
if (as.character(getRversion()) != "4.4.3")
  stop("requires exactly R 4.4.3",call.=FALSE)
args <- commandArgs(trailingOnly=TRUE)
if (length(args)!=1L ||
    !grepl("^[0-9]+(?:\\.[0-9]+)?$",args[[1L]],perl=TRUE))
  stop("one positive decimal RMST horizon required",call.=FALSE)
tau <- as.numeric(args[[1L]])
if (!is.finite(tau) || tau<=0)
  stop("invalid RMST horizon",call.=FALSE)
d <- tryCatch(read.table(file("stdin"),header=TRUE,sep="\t",
                         quote="",check.names=FALSE,stringsAsFactors=FALSE),
              error=function(e)stop("invalid curve table",call.=FALSE))
if (!identical(names(d),c("trial","t","surv_trt","surv_ctl")) ||
    nrow(d)<2L || anyNA(d) || any(!nzchar(trimws(d$trial))) ||
    !all(vapply(d[-1L],is.numeric,logical(1L))) ||
    any(!is.finite(as.matrix(d[-1L]))) ||
    any(d$t<0 | d$surv_trt<0 | d$surv_trt>1 |
        d$surv_ctl<0 | d$surv_ctl>1))
  stop("invalid KM source table",call.=FALSE)
cat("trial\trmst_trt\trmst_ctl\trmst_diff\n")
for (id in unique(d$trial)) {
  sub <- d[d$trial==id,,drop=FALSE]
  times <- sub$t
  if (nrow(sub)<2L || any(diff(times)<0) || tail(times,1)<tau ||
      any(diff(sub$surv_trt)>0) || any(diff(sub$surv_ctl)>0))
    stop("invalid chronology, survival monotonicity or support",call.=FALSE)
  # The ordinate at event time t is the KM value AFTER the event. The area
  # on [prev_t,t) therefore uses the previous ordinate, not its average
  # with the value at t. Independently coded on the R side.
  cut <- pmin(times,tau)
  widths <- diff(c(0,cut))
  if (any(widths<0)) stop("invalid step intervals",call.=FALSE)
  integrate <- function(s) sum(widths*c(1,head(s,-1L)))
  treatment <- integrate(sub$surv_trt)
  control <- integrate(sub$surv_ctl)
  values <- c(treatment,control,treatment-control)
  if (any(!is.finite(values))) stop("nonfinite area",call.=FALSE)
  cat(id,paste(sprintf("%.17g",values),collapse="\t"),sep="\t")
  cat("\n")
}
