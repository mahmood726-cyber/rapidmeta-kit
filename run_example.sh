#!/usr/bin/env bash
# Run this (Mac/Linux) to build the example RapidMeta dashboard and open it.
# Needs Python 3 installed.
cd "$(dirname "$0")" || exit 1
echo "Building the example RapidMeta dashboard..."
if ! python3 clone.py configs/example_finerenone_ckd.json; then
  echo
  echo "Could not run. Is Python 3 installed?  Try:  python3 --version"
  exit 1
fi
echo
echo "Opening the dashboard..."
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open output/finerenone_ckd.html
elif command -v open >/dev/null 2>&1; then
  open output/finerenone_ckd.html
else
  echo "Open this file in a browser: output/finerenone_ckd.html"
fi
echo
echo "To make your own: copy a file in configs/, edit drug/condition/trials,"
echo "then run:  python3 clone.py configs/your_file.json"
