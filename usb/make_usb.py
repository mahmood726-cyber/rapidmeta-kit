#!/usr/bin/env python
"""make_usb.py — assemble a zero-internet USB stick for the Tuesday researchers.

Bandwidth is the constraint in the field; a memory stick is not. This builds a
self-contained stick a researcher can run with the cable pulled:

    <stick>/
      START_HERE.txt         plain instructions
      run.bat / run.sh       one launcher: opens a review + prints how to ask
      harness/rmharness/      Tier-2 deterministic harness (shared, one copy)
      reviews/<slug>/         one folder per review = app + bundle.json + toolkit
      model/<model>.gguf      the small chat model (optional; assistant degrades without it)
      data/                   slot for an AACT snapshot + cached corpus (optional)

Nothing here needs the internet. If the model is absent the harness still
reproduces every number and answers with the deterministic explainer.

Usage:
    python make_usb.py --out E:\\rapidmeta-stick \\
        --reviews ../bundle-example/finerenone_ckd [more...] \\
        [--model path/to/model.gguf] [--aact path/to/aact_snapshot]
"""
from __future__ import annotations

import argparse
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)

RUN_BAT = r"""@echo off
REM RapidMeta field stick - zero internet required.
setlocal
set HERE=%~dp0
echo ============================================================
echo  RapidMeta review + toolkit  (offline)
echo ============================================================
echo.
echo Opening the review in your browser...
for /d %%D in ("%HERE%reviews\*") do (
  start "" "%%D\index.html"
  goto :opened
)
:opened
echo.
echo To CHECK or ASK about a review, open a terminal here and run:
echo   set PYTHONPATH=%HERE%harness
echo   cd reviews\<review-name>
echo   python -m rmharness reproduce bundle.json
echo   python -m rmharness ask       bundle.json "Is the heterogeneity a problem?"
if exist "%HERE%model\*.gguf" (
  for %%M in ("%HERE%model\*.gguf") do echo   ... add:  --model "%%M"   ^(fluent answers^)
) else (
  echo   ^(no chat model on this stick - the deterministic explainer is used^)
)
echo.
pause
"""

RUN_SH = r"""#!/usr/bin/env bash
# RapidMeta field stick - zero internet required.
HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$HERE/harness"
echo "============================================================"
echo " RapidMeta review + toolkit  (offline)"
echo "============================================================"
review="$(ls -d "$HERE"/reviews/*/ 2>/dev/null | head -1)"
[ -n "$review" ] && { echo "Opening $review/index.html"; (xdg-open "$review/index.html" 2>/dev/null || open "$review/index.html" 2>/dev/null || true); }
echo
echo "To CHECK or ASK about a review:"
echo "  export PYTHONPATH=$HERE/harness"
echo "  cd reviews/<review-name>"
echo "  python -m rmharness reproduce bundle.json"
model="$(ls "$HERE"/model/*.gguf 2>/dev/null | head -1)"
if [ -n "$model" ]; then
  echo "  python -m rmharness ask bundle.json \"Is the heterogeneity a problem?\" --model \"$model\""
else
  echo "  python -m rmharness ask bundle.json \"Is the heterogeneity a problem?\"   # deterministic explainer"
fi
"""

START = """RapidMeta review + toolkit -- offline USB stick
================================================

You need Python 3.8+ installed (python.org). Nothing else. No internet.

1. Double-click run.bat (Windows) or run run.sh (Mac/Linux).
   It opens a finished evidence review in your browser.

2. To CHECK OUR NUMBERS yourself, or ASK questions in plain language,
   open a terminal in this folder and follow what run.bat/run.sh prints:
     python -m rmharness reproduce bundle.json   -> re-derives our pooled number
     python -m rmharness ask       bundle.json "what does this review find?"

3. The chat assistant EXPLAINS the numbers; it never invents one. Every value
   comes from the deterministic engine. If a model is on the stick you get
   fluent answers; if not, you still get correct grounded explanations.

Everything works with the wifi off. This stick is yours to keep, copy, and share.
"""


def copy_pkg(dst_harness):
    os.makedirs(dst_harness, exist_ok=True)
    src = os.path.join(KIT, "harness", "rmharness")
    dst = os.path.join(dst_harness, "rmharness")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "tests", "*.pyc"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="stick root (e.g. E:\\rapidmeta-stick)")
    ap.add_argument("--reviews", nargs="+", required=True, help="bundle dirs to include")
    ap.add_argument("--model", default=None, help="optional GGUF chat model")
    ap.add_argument("--aact", default=None, help="optional AACT snapshot dir/file")
    args = ap.parse_args(argv)

    out = args.out
    os.makedirs(out, exist_ok=True)
    copy_pkg(os.path.join(out, "harness"))
    rev_root = os.path.join(out, "reviews")
    os.makedirs(rev_root, exist_ok=True)
    for r in args.reviews:
        slug = os.path.basename(os.path.normpath(r))
        dst = os.path.join(rev_root, slug)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(r, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if args.model and os.path.exists(args.model):
        md = os.path.join(out, "model")
        os.makedirs(md, exist_ok=True)
        shutil.copy2(args.model, os.path.join(md, os.path.basename(args.model)))
    if args.aact and os.path.exists(args.aact):
        ad = os.path.join(out, "data")
        os.makedirs(ad, exist_ok=True)
        # link/copy note only — snapshots are large; copy if a real path was given
        dst = os.path.join(ad, os.path.basename(os.path.normpath(args.aact)))
        if os.path.isdir(args.aact):
            shutil.copytree(args.aact, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(args.aact, dst)

    with open(os.path.join(out, "run.bat"), "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(RUN_BAT)
    with open(os.path.join(out, "run.sh"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(RUN_SH)
    with open(os.path.join(out, "START_HERE.txt"), "w", encoding="utf-8") as fh:
        fh.write(START)

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(out) for f in fs)
    print(f"USB stick assembled at {out}")
    print(f"  reviews: {len(args.reviews)}   model: {'yes' if args.model else 'no'}   "
          f"aact: {'yes' if args.aact else 'no'}")
    print(f"  total size: {total/1048576:.1f} MB")


if __name__ == "__main__":
    main()
