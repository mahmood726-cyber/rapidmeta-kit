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
  --self-check         assert the kit base itself carries every marker (CI gate for the kit)
  <files/globs>        audit dashboards; exit 1 if any are missing >=1 marker (drift found)
  --markers-only       just print the marker set and exit

Exit: 0 = no drift / self-check OK; 1 = drift found / self-check failed; 2 = bad usage.
"""
import sys, glob, io, os

KIT_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "template", "base_dupilumab_copd.html")

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


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}

    if "--markers-only" in flags:
        for m, label in MARKERS.items():
            print(f"  {label}: {m!r}")
        return 0

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
