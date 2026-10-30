#!/usr/bin/env Rscript
# Synthesis | Statistical Parity: independent R 4.4.3 / metafor 4.8-0
# comparator for synthetic KM-step RMST differences and pooled REML/adhoc CI.
# No censoring-aware SE estimation or clinical-source inference is asserted.
options(warn=2)
if (as.character(getRversion()) != "4.4.3" ||
    as.character(utils::packageVersion("metafor")) != "4.8.0")
  stop("requires R 4.4.3 and metafor 4.8-0",call.=FALSE)
args <- commandArgs(trailingOnly=TRUE)
if (length(args)!=1L || !grepl("^[0-9]+(?:\\.[0-9]+)?$",args[[1]],perl=TRUE))
  stop("one decimal restriction horizon required",call.=FALSE)
tau <- as.numeric(args[[1]])
if (!is.finite(tau) || tau<=0) stop("invalid RMST horizon",call.=FALSE)

d <- tryCatch(read.delim(file("stdin"),sep="\t",quote="",check.names=FALSE,
                         stringsAsFactors=FALSE),
              error=function(e)stop("invalid RMST source table",call.=FALSE))
needed <- c("trial","t","surv_trt","surv_ctl","rmst_diff_se")
if (!identical(names(d),needed) || nrow(d)<4L || anyNA(d) ||
    !is.character(d$trial) || any(!nzchar(trimws(d$trial))) ||
    !all(vapply(d[-1L],is.numeric,logical(1))) ||
    any(!is.finite(as.matrix(d[-1L]))) ||
    any(d$t<0 | d$surv_trt<0 | d$surv_trt>1 |
        d$surv_ctl<0 | d$surv_ctl>1))
  stop("invalid RMST source table",call.=FALSE)

ids <- unique(d$trial)
if (length(ids)<2L) stop("need two independent trials",call.=FALSE)
yi <- numeric(length(ids)); se <- numeric(length(ids))
cat("TYPE\tID_OR_K\tRMST_T_OR_POOLED\tRMST_C_OR_CI_LO\tDIFF_OR_CI_HI\tSE_OR_TAU2\n")
for (j in seq_along(ids)) {
  sub <- d[d$trial==ids[[j]],,drop=FALSE]
  times <- sub$t
  if (nrow(sub)<2L || any(diff(times)<0) ||
      tail(times,1)<tau ||
      any(diff(sub$surv_trt)>0) || any(diff(sub$surv_ctl)>0))
    stop("invalid RMST curve or support",call.=FALSE)
  if (any(sub$rmst_diff_se<=0) ||
      length(unique(sub$rmst_diff_se))!=1L)
    stop("invalid RMST standard error",call.=FALSE)
  se[[j]] <- sub$rmst_diff_se[[1L]]
  # KM ordinate at t is the value AFTER that event time.  Integrate each
  # preceding interval at the previous ordinate (no interpolation).
  widths <- diff(c(0,pmin(times,tau)))
  if (any(widths<0)) stop("invalid KM widths",call.=FALSE)
  integrate <- function(s) sum(widths*c(1,head(s,-1L)))
  rt <- integrate(sub$surv_trt)
  rc <- integrate(sub$surv_ctl)
  yi[[j]] <- rt-rc
  cat(sprintf("STUDY\t%s\t%.17g\t%.17g\t%.17g\t%.17g\n",
              ids[[j]],rt,rc,yi[[j]],se[[j]]))
}
vi <- se^2
if (any(!is.finite(vi)) || any(vi<=0) || any(!is.finite(1/vi)))
  stop("invalid RMST sampling variances",call.=FALSE)
fit <- metafor::rma.uni(yi=yi,vi=vi,method="REML",test="adhoc",level=95)
values <- c(as.numeric(fit$b[1L,1L]),as.numeric(fit$ci.lb),
            as.numeric(fit$ci.ub),as.numeric(fit$tau2))
if (fit$k!=length(ids) || any(!is.finite(values)) ||
    values[[2]]>values[[1]] || values[[1]]>values[[3]])
  stop("invalid external REML/HKSJ result",call.=FALSE)
cat(sprintf("POOL\t%d\t%.17g\t%.17g\t%.17g\t%.17g\n",
            fit$k,values[[1]],values[[2]],values[[3]],values[[4]]))
