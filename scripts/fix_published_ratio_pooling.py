#!/usr/bin/env python
"""Codemod: add published-ratio (rate/risk/hazard ratio) pooling for count-less
outcomes to RapidMeta single-file dashboards.

Root bug: an outcome that reports a published RELATIVE effect (e.g. an annualized
exacerbation RATE RATIO) but no 2x2 event counts falls into the OR/RR count branch,
which computes log((a/b)/(c/d)) from null counts -> NaN -> the forest renders with no
whiskers/diamond, the cumulative MA is empty, and the fragility index falsely reads 0
("robust"). There is a published-HR branch but no published-RR/IRR branch.

Fix (idempotent, anchored on the generated template text):
  T1  add trialPublishedRatio / trialHasPublishedRatio helpers
  T2  normalization (def path): preserve published ratio from pubHR|publishedHR|effect
  T3  normalization (oc  path): same
  T4  main pooling: add _countPoolable() guard
  T5  main pooling: published-ratio fallback in the filter+map
  T6  cumulative MA: published-ratio fallback
  T7  secondary forest: published-ratio else-if branch
  T8  fragility index: N/A (leave 0) when 2x2 counts are absent

Each transform is skipped if its sentinel is already present (idempotent) or if its
anchor is not found (drifted clone -> logged, not an error).

Usage:
  python fix_published_ratio_pooling.py --dry-run FILE [FILE ...]
  python fix_published_ratio_pooling.py --apply   FILE [FILE ...]
  python fix_published_ratio_pooling.py --self-test   # validate vs git original
"""
import argparse, io, os, sys, hashlib

# ---- transformations: (name, sentinel, old, new) ---------------------------
B = "\n\n\n"  # the generated template separates code lines with two blank lines

T = []

# T1 -------------------------------------------------------------------------
T.append((
 "T1-helpers", "trialHasPublishedRatio(trial) {",
 "                    String(d?.estimandType ?? 'HR').toUpperCase() !== 'RR'"+B+
 "                );"+B+
 "            },",
 "                    String(d?.estimandType ?? 'HR').toUpperCase() !== 'RR'"+B+
 "                );"+B+
 "            },\n\n"
 "            // Published RELATIVE effect (rate ratio / risk ratio / hazard ratio /\n"
 "            // incidence-rate ratio) + 95% CI, regardless of estimandType. Unlike\n"
 "            // trialHasPublishedHR this does NOT exclude estimandType 'RR' — it is the\n"
 "            // source for log-ratio pooling when a trial reports a published effect but\n"
 "            // no 2x2 event counts (e.g. annualized exacerbation rate ratios).\n"
 "            trialPublishedRatio(trial) {\n"
 "                const d = trial?.data;\n"
 "                if (!d) return null;\n"
 "                const est = d.pubHR ?? d.publishedHR ?? d.effect ?? null;\n"
 "                const lci = d.pubHR_LCI ?? d.hrLCI ?? d.lci ?? null;\n"
 "                const uci = d.pubHR_UCI ?? d.hrUCI ?? d.uci ?? null;\n"
 "                if (est > 0 && lci > 0 && uci > 0 && uci >= lci) return { est, lci, uci };\n"
 "                return null;\n"
 "            },\n\n"
 "            trialHasPublishedRatio(trial) {\n"
 "                return this.trialPublishedRatio(trial) != null;\n"
 "            },",
))

# T2 -------------------------------------------------------------------------
T.append((
 "T2-norm-def", "def.publishedHR ?? def.effect",
 "                            t.data.pubHR = def.pubHR ?? null;"+B+
 "                            t.data.pubHR_LCI = def.pubHR_LCI ?? null;"+B+
 "                            t.data.pubHR_UCI = def.pubHR_UCI ?? null;"+B+
 "                            t.data.publishedHR = def.pubHR ?? null;"+B+
 "                            t.data.hrLCI = def.pubHR_LCI ?? null;"+B+
 "                            t.data.hrUCI = def.pubHR_UCI ?? null;",
 "                            t.data.pubHR = def.pubHR ?? def.publishedHR ?? def.effect ?? null;\n"
 "                            t.data.pubHR_LCI = def.pubHR_LCI ?? def.hrLCI ?? def.lci ?? null;\n"
 "                            t.data.pubHR_UCI = def.pubHR_UCI ?? def.hrUCI ?? def.uci ?? null;\n"
 "                            t.data.publishedHR = t.data.pubHR;\n"
 "                            t.data.hrLCI = t.data.pubHR_LCI;\n"
 "                            t.data.hrUCI = t.data.pubHR_UCI;",
))

# T3 -------------------------------------------------------------------------
T.append((
 "T3-norm-oc", "oc.publishedHR ?? oc.effect",
 "                            t.data.pubHR = oc.pubHR ?? null;"+B+
 "                            t.data.pubHR_LCI = oc.pubHR_LCI ?? null;"+B+
 "                            t.data.pubHR_UCI = oc.pubHR_UCI ?? null;"+B+
 "                            t.data.publishedHR = oc.pubHR ?? null;"+B+
 "                            t.data.hrLCI = oc.pubHR_LCI ?? null;"+B+
 "                            t.data.hrUCI = oc.pubHR_UCI ?? null;",
 "                            t.data.pubHR = oc.pubHR ?? oc.publishedHR ?? oc.effect ?? null;\n"
 "                            t.data.pubHR_LCI = oc.pubHR_LCI ?? oc.hrLCI ?? oc.lci ?? null;\n"
 "                            t.data.pubHR_UCI = oc.pubHR_UCI ?? oc.hrUCI ?? oc.uci ?? null;\n"
 "                            t.data.publishedHR = t.data.pubHR;\n"
 "                            t.data.hrLCI = t.data.pubHR_LCI;\n"
 "                            t.data.hrUCI = t.data.pubHR_UCI;",
))

# T4 -------------------------------------------------------------------------
T.append((
 "T4-countPoolable", "const _countPoolable = t => {",
 "                    /* OR / RR mode: compute from 2x2 event counts */",
 "                    /* OR / RR mode: compute from 2x2 event counts, with a published-ratio\n"
 "                       fallback (relative effect + 95% CI) for trials that report a ratio\n"
 "                       but no 2x2 event table (e.g. annualized exacerbation rate ratios). */\n"
 "                    const _countPoolable = t => {\n"
 "                        const e = t.data;\n"
 "                        if (![e.tE, e.cE, e.tN, e.cN].every(v => typeof v === 'number' && isFinite(v))) return false;\n"
 "                        if (e.tN <= 0 || e.cN <= 0) return false;\n"
 "                        if (e.tE === 0 && e.cE === 0) return false;\n"
 "                        if (e.tE === e.tN && e.cE === e.cN) return false;\n"
 "                        return true;\n"
 "                    };",
))

# T5 (main forest filter + map published branch) -----------------------------
PUB_MAIN = (
 "                        if (!_countPoolable(t)) {\n"
 "                            /* Published relative effect, no usable 2x2 counts: pool on the\n"
 "                               log scale (null = 1). A published ratio CI is essentially\n"
 "                               always 95%, so se = (log UCI - log LCI) / (2 * 1.96)\n"
 "                               regardless of the dashboard's chosen output confidence level. */\n"
 "                            const _p = RapidMeta.trialPublishedRatio(t);\n"
 "                            const _se = (Math.log(_p.uci) - Math.log(_p.lci)) / (2 * Z95_HR);\n"
 "                            const _vi = _se * _se;\n"
 "                            return { logOR: Math.log(_p.est), vi: _vi, se: _se, w_fixed: 1 / _vi, id: RapidMeta.nctAcronyms[t.id] ?? t.data?.name ?? t.id, group: t.data?.group || 'Other', year: t.data.year ?? 2020, cer: NaN, ter: NaN, rob: safeRob(t.data.rob), tN: t.data.tN, cN: t.data.cN, tE: t.data.tE, cE: t.data.cE, phase: t.data?.phase ?? '', fromPublishedEffect: true };\n"
 "                        }\n"
)
T.append((
 "T5-main-fallback", "fromPublishedEffect: true };\n                        }\n                        const hasZero = (t.data.tE",
 "                    plotData = trials.filter(t => {"+B+
 "                        if (t.data.tE === 0 && t.data.cE === 0) return false;"+B+
 "                        if (t.data.tE === t.data.tN && t.data.cE === t.data.cN) return false;"+B+
 "                        return true;"+B+
 "                    }).map(t => {"+B+
 "                        const hasZero = (t.data.tE === 0 || t.data.cE === 0 || t.data.tE === t.data.tN || t.data.cE === t.data.cN);",
 "                    plotData = trials.filter(t => _countPoolable(t) || RapidMeta.trialHasPublishedRatio(t)).map(t => {"+B+
 PUB_MAIN +
 "                        const hasZero = (t.data.tE === 0 || t.data.cE === 0 || t.data.tE === t.data.tN || t.data.cE === t.data.cN);",
))

# T6 (cumulative MA) ---------------------------------------------------------
T.append((
 "T6-cumulative", "// Published relative effect with no usable 2x2 counts (e.g. rate ratio):\n                        // pool the log-ratio",
 "                            return { logOR: logEff, vi: se * se, se, id: RapidMeta.nctAcronyms[t.id] ?? t.data?.name ?? t.id, year: t.data.year ?? 2020 };"+B+
 "                        }"+B+
 "                        const hasZero = (t.data.tE === 0 || t.data.cE === 0 || t.data.tE === t.data.tN || t.data.cE === t.data.cN);",
 "                            return { logOR: logEff, vi: se * se, se, id: RapidMeta.nctAcronyms[t.id] ?? t.data?.name ?? t.id, year: t.data.year ?? 2020 };"+B+
 "                        }\n\n"
 "                        // Published relative effect with no usable 2x2 counts (e.g. rate ratio):\n"
 "                        // pool the log-ratio (published CIs are 95%, so se = (logU-logL)/(2*1.96)).\n"
 "                        if (RapidMeta.trialHasPublishedRatio(t) && ![t.data.tE, t.data.cE, t.data.tN, t.data.cN].every(v => typeof v === 'number' && isFinite(v))) {\n"
 "                            const _p = RapidMeta.trialPublishedRatio(t);\n"
 "                            const _se = (Math.log(_p.uci) - Math.log(_p.lci)) / (2 * 1.959963985);\n"
 "                            return { logOR: Math.log(_p.est), vi: _se * _se, se: _se, id: RapidMeta.nctAcronyms[t.id] ?? t.data?.name ?? t.id, year: t.data.year ?? 2020 };\n"
 "                        }\n\n"
 "                        const hasZero = (t.data.tE === 0 || t.data.cE === 0 || t.data.tE === t.data.tN || t.data.cE === t.data.cN);",
))

# T7 (secondary forest else-if) ----------------------------------------------
T.append((
 "T7-secondary-forest", "} else if (RapidMeta.trialHasPublishedRatio(t) && ![d.tE",
 "                    } else {"+B+
 "                        const hasZero = (d.tE === 0 || d.cE === 0 || d.tE === d.tN || d.cE === d.cN);"+B+
 "                        const adj = hasZero ? 0.5 : 0;"+B+
 "                        const a = d.tE + adj, b = d.tN - d.tE + adj, c = d.cE + adj, dd = d.cN - d.cE + adj;",
 "                    } else if (RapidMeta.trialHasPublishedRatio(t) && ![d.tE, d.cE, d.tN, d.cN].every(v => typeof v === 'number' && isFinite(v))) {\n\n"
 "                        // Published relative effect with no usable 2x2 counts (e.g. rate ratio).\n"
 "                        const _p = RapidMeta.trialPublishedRatio(t);\n"
 "                        logOR = Math.log(_p.est);\n"
 "                        se = (Math.log(_p.uci) - Math.log(_p.lci)) / (2 * 1.959963985);\n\n"
 "                    } else {"+B+
 "                        const hasZero = (d.tE === 0 || d.cE === 0 || d.tE === d.tN || d.cE === d.cN);"+B+
 "                        const adj = hasZero ? 0.5 : 0;"+B+
 "                        const a = d.tE + adj, b = d.tN - d.tE + adj, c = d.cE + adj, dd = d.cN - d.cE + adj;",
))

# T8 (fragility N/A without counts) ------------------------------------------
T.append((
 "T8-fragility-na", "const _fiHasCounts = plotData.every",
 "                if (useHR) { /* FI is N/A in HR mode; leave fragIdx = 0 */ }",
 "                const _fiHasCounts = plotData.every(d => [d.tE, d.cE, d.tN, d.cN].every(v => typeof v === 'number' && isFinite(v)));\n\n"
 "                if (useHR || !_fiHasCounts) { /* FI is N/A in HR mode or without 2x2 counts (e.g. rate ratios); leave fragIdx = 0 */ }",
))


def _variants(old):
    """The kit template is triple-spaced (two blank lines between statements);
    drifted clones (e.g. the finerenone e156 fleet) are single/zero-spaced. Try the
    canonical triple-spaced anchor first, then the collapsed single-newline form."""
    yield old
    collapsed = old.replace("\n\n\n", "\n")
    if collapsed != old:
        yield collapsed


# Safety invariants enforced BEFORE writing: a transform whose NEW code calls a
# helper must not be applied unless the helper-defining transform is also present.
# present(X) = X applied this run OR its sentinel already in the file.
#   T5 main fallback uses _countPoolable (T4) and trialHasPublishedRatio (T1)
#   T6 cumulative / T7 secondary use trialHasPublishedRatio (T1)
INVARIANTS = [
    ("T5-main-fallback", ["T1-helpers", "T4-countPoolable"]),
    ("T6-cumulative", ["T1-helpers"]),
    ("T7-secondary-forest", ["T1-helpers"]),
]
# Transforms that actually fix a bug (vs T4 which is an inert helper def on its own).
CORE_FIXES = {"T5-main-fallback", "T6-cumulative", "T7-secondary-forest",
              "T2-norm-def", "T3-norm-oc", "T8-fragility-na"}


def apply_file(path, apply):
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    out = src
    log = []
    status = {}
    for name, sentinel, old, new in T:
        if sentinel in out:
            status[name] = "already"; log.append((name, "already")); continue
        matched = None
        for cand in _variants(old):
            if out.count(cand) == 1:
                matched = cand; break
            if out.count(cand) > 1:
                status[name] = "ambiguous"; log.append((name, "ambiguous(%d)" % out.count(cand))); matched = False; break
        if matched is False:
            continue
        if matched is None:
            status[name] = "anchor-not-found"; log.append((name, "anchor-not-found")); continue
        out = out.replace(matched, new, 1)
        status[name] = "applied"; log.append((name, "applied"))

    def present(n):
        return status.get(n) in ("applied", "already")

    # enforce safety invariants
    violations = []
    for dep, needs in INVARIANTS:
        if present(dep) and not all(present(n) for n in needs):
            violations.append("%s needs %s" % (dep, ",".join(n for n in needs if not present(n))))
    changed = out != src
    has_core = any(present(n) for n in CORE_FIXES)
    if violations:
        return False, log + [("ABORT-INCONSISTENT", ";".join(violations))], src
    if changed and not has_core:
        # only inert/no-op changes (e.g. lone T4) — don't churn the file
        return False, log + [("SKIP-no-core-fix", "")], src
    if apply and changed:
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    return changed, log, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        here = os.path.dirname(os.path.abspath(__file__))
        repo = os.path.dirname(here)
        orig = os.path.join(repo, "..", "..", "..", "tmp", "orig_base.html")
        # fall back to git
        import subprocess
        cur = os.path.join(repo, "template", "base_dupilumab_copd.html")
        o = subprocess.run(["git", "-C", repo, "show", "HEAD:template/base_dupilumab_copd.html"],
                           capture_output=True)
        if o.returncode != 0:
            print("self-test: cannot read git original"); sys.exit(2)
        src = o.stdout.decode("utf-8")
        out = src
        for name, sentinel, old, new in T:
            if sentinel in out:
                continue
            if old not in out or out.count(old) > 1:
                print("self-test FAIL: %s anchor missing/ambiguous in original" % name); sys.exit(1)
            out = out.replace(old, new, 1)
        with io.open(cur, encoding="utf-8") as f:
            handfix = f.read()
        h1 = hashlib.md5(out.encode("utf-8")).hexdigest()
        h2 = hashlib.md5(handfix.encode("utf-8")).hexdigest()
        print("codemod-result md5:", h1)
        print("hand-fixed   md5:", h2)
        print("SELF-TEST:", "PASS (byte-identical)" if h1 == h2 else "FAIL (differs)")
        sys.exit(0 if h1 == h2 else 1)

    apply = a.apply and not a.dry_run
    tot = {"applied": 0, "already": 0, "anchor-not-found": 0}
    nfiles = 0
    for path in a.files:
        changed, log, _ = apply_file(path, apply)
        nfiles += 1
        counts = {}
        for _, st in log:
            counts[st] = counts.get(st, 0) + 1
            tot[st] = tot.get(st, 0) + 1
        tag = "APPLIED" if (apply and changed) else ("WOULD-CHANGE" if changed else "no-change")
        print("[%s] %s :: %s" % (tag, path, counts))
    print("\nTOTAL files=%d  %s" % (nfiles, tot))


if __name__ == "__main__":
    main()
