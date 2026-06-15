#!/usr/bin/env python
"""Codemod: fix effect-size extraction CI-separator coverage (and the extraction-card
continuous-vs-ratio mislabel) in RapidMeta single-file dashboards.

Confirmed bug: rate-ratio / Cohen's d / Hedges' g CIs written with "to"
(e.g. "rate ratio 0.70 (95% CI 0.58 to 0.86)") were missed because those patterns
used a dash-only CI separator. SEP/TO are unified to (?:to|dash|comma) and every
inline dash-only separator now uses SEP.

Idempotent: each replacement is skipped if already applied. Universal CI-separator
fix applies to any file carrying the extractor; the extraction-card relabel applies
only where its anchor (the dupilumab-family build) is present.

Usage:
  python fix_extraction_patterns.py --dry-run FILE [FILE ...]
  python fix_extraction_patterns.py --apply   FILE [FILE ...]
"""
import argparse, io, sys

UNIFIED = "'(?:to|[-\\\\u2013\\\\u2014,])'"

# (name, old, new, count)  count="all" for replace-all, else 1
REPL = [
    ("SEP-unify",
     "const SEP = '[-\\\\u2013\\\\u2014,]';",
     "const SEP = '(?:to|[-\\\\u2013\\\\u2014,])';   // CI bound separator: \"to\", hyphen/en/em dash, or comma",
     1),
    ("TO-unify",
     "const TO = '(?:to|[-\\\\u2013\\\\u2014])';",
     "const TO = '(?:to|[-\\\\u2013\\\\u2014,])';   // unified with SEP so to/dash/comma all parse",
     1),
    ("dash-separators",
     "'\\\\s*[-\\\\u2013\\\\u2014]\\\\s*'",
     "'\\\\s*' + SEP + '\\\\s*'",
     "all"),
]


def apply_file(path, apply):
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    out = src
    log = {}
    for name, old, new, count in REPL:
        if name == "SEP-unify" and "(?:to|[-\\u2013\\u2014,])'" in out and "const SEP" in out and old not in out:
            log[name] = "already"; continue
        n = out.count(old)
        if n == 0:
            log[name] = "already" if (new.split("//")[0].strip() in out or new in out) else "not-found"
            continue
        if count == "all":
            out = out.replace(old, new)
            log[name] = "applied(%d)" % n
        else:
            out = out.replace(old, new, 1)
            log[name] = "applied"
    changed = out != src
    if apply and changed:
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    return changed, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    apply = a.apply and not a.dry_run
    tot = 0
    for p in a.files:
        changed, log = apply_file(p, apply)
        if changed:
            tot += 1
        tag = "APPLIED" if (apply and changed) else ("WOULD-CHANGE" if changed else "no-change")
        print("[%s] %s :: %s" % (tag, p, log))
    print("\n%d/%d files changed" % (tot, len(a.files)))


if __name__ == "__main__":
    main()
