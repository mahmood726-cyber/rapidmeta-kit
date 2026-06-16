#!/usr/bin/env python
"""Engine-drift detector — enforce ONE canonical RapidMeta engine.

The RapidMeta engine is distributed by copy/inline rather than as a shared runtime
dependency, so dashboards can silently drift behind the canonical kit engine
(`template/base_dupilumab_copd.html`). This tool makes that drift VISIBLE: it scans
dashboard HTML for a set of marker strings that each correspond to a shipped
correctness fix, and reports which dashboards are missing them.

Markers are method/property names (they survive minification, unlike local consts),
each = a shipped correctness fix that defines the current engine:
  - trialHasPublishedRatio   : published rate/risk/hazard-ratio pooling (count-less forests)
  - isContinuousOutcome      : continuous-vs-ratio routing (no mean-difference mis-pooled as a ratio)

NOTE: the extractor CI-separator fix is NOT marker-detectable (the unified SEP value
collides with the pre-existing GMR pattern, and SEP minifies away) — audit it per
engine version separately. These two markers are the reliable core-correctness signal.

Modes:
  --self-check            assert the kit base itself carries every marker (CI gate for the kit)
  <files/globs>           audit dashboards; exit 1 if any are missing >=1 marker (drift found)
  --markers-only          just print the marker set and exit
  --vendor-audit <dir>    compare a repo's vendor engine dir against the canonical kit
                          copies (template/assets/vendor); exit 1 on CODE drift. This
                          catches engine fixes that never propagated to a clone repo —
                          which the marker scan above cannot see (it only reads the
                          inline dashboard engine, not the vendored *.js panels).

Exit: 0 = no drift / self-check OK; 1 = drift found / self-check failed; 2 = bad usage.
"""
import re, sys, glob, io, os

KIT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "template", "base_dupilumab_copd.html")
CANON_VENDOR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "template", "assets", "vendor")

# marker -> human label (the fix it represents)
MARKERS = {
    "trialHasPublishedRatio": "published-ratio pooling (count-less forests)",
    "isContinuousOutcome": "continuous-vs-ratio routing guard",
}


def scan(path):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError as e:
        return None, str(e)
    missing = [m for m in MARKERS if m not in src]
    return missing, None


def _read(path):
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _normalize_js(src):
    """Strip comments + collapse whitespace so two files that differ only in
    comments/labels/formatting compare equal. Heuristic (not a full JS parser):
    good enough to classify comment-only vs real CODE drift between sibling
    copies of the same engine file."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)      # block comments
    # line comments: only when '//' is preceded by start-of-line or whitespace
    # AND not part of a scheme like http:// (avoid eating string URLs).
    src = re.sub(r"(^|[^:\w])//[^\n]*", r"\1", src)
    src = re.sub(r"\s+", " ", src)                            # collapse whitespace
    return src.strip()


def vendor_audit(target_dir):
    """Compare each canonical engine .js against the target repo's copy.
    Returns (rows, code_drift_count). rows: (name, status, detail)."""
    if not os.path.isdir(CANON_VENDOR):
        return [("<canonical>", "ERROR", f"missing {CANON_VENDOR}")], 1
    if not os.path.isdir(target_dir):
        return [(target_dir, "ERROR", "target vendor dir not found")], 1
    rows, code_drift = [], 0
    for name in sorted(os.listdir(CANON_VENDOR)):
        if not name.endswith(".js"):
            continue
        canon = os.path.join(CANON_VENDOR, name)
        tgt = os.path.join(target_dir, name)
        if not os.path.exists(tgt):
            rows.append((name, "MISSING", "not present in target"))
            continue
        cs, ts = _read(canon), _read(tgt)
        if cs == ts:
            rows.append((name, "MATCH", ""))
        elif _normalize_js(cs) == _normalize_js(ts):
            rows.append((name, "comment-only", "differs in comments/format only"))
        else:
            code_drift += 1
            rows.append((name, "CODE-DRIFT", "code differs from canonical kit"))
    return rows, code_drift


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}

    if "--markers-only" in flags:
        for m, label in MARKERS.items():
            print(f"  {label}: {m!r}")
        return 0

    if "--vendor-audit" in flags:
        if not args:
            print("usage: check_engine_drift.py --vendor-audit <target-vendor-dir>",
                  file=sys.stderr)
            return 2
        rc = 0
        for target in args:
            rows, code_drift = vendor_audit(target)
            print(f"\n[vendor-audit] {target}  (canonical: template/assets/vendor)")
            shown = [r for r in rows if r[1] != "MATCH"]
            for name, status, detail in shown:
                print(f"  {status:12s} {name}" + (f"  — {detail}" if detail else ""))
            n_match = sum(1 for r in rows if r[1] == "MATCH")
            n_miss = sum(1 for r in rows if r[1] == "MISSING")
            n_cmt = sum(1 for r in rows if r[1] == "comment-only")
            print(f"  => {n_match} match, {n_cmt} comment-only, {n_miss} missing, "
                  f"{code_drift} CODE-DRIFT")
            if code_drift:
                rc = 1
        return rc

    if "--self-check" in flags:
        missing, err = scan(KIT_BASE)
        if err:
            print(f"[drift] cannot read kit base: {err}"); return 1
        if missing:
            print("[drift] SELF-CHECK FAILED — kit base is missing markers:")
            for m in missing:
                print(f"        - {MARKERS[m]} ({m!r})")
            return 1
        print(f"[drift] self-check OK — kit base carries all {len(MARKERS)} engine markers")
        return 0

    # audit mode: expand globs
    files = []
    for a in args:
        files.extend(glob.glob(a, recursive=True))
    files = [f for f in files if f.lower().endswith(".html")]
    if not files:
        print("usage: check_engine_drift.py [--self-check] [--markers-only] <file-or-glob> ...",
              file=sys.stderr)
        return 2

    drifted = 0
    current = 0
    for f in sorted(files):
        missing, err = scan(f)
        if err:
            print(f"  ERROR  {f}: {err}"); drifted += 1; continue
        if missing:
            drifted += 1
            print(f"  DRIFT  {f}  missing: {', '.join(MARKERS[m] for m in missing)}")
        else:
            current += 1
    print(f"\n{current}/{len(files)} current, {drifted} drifted "
          f"(canonical engine: template/base_dupilumab_copd.html)")
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
