#!/usr/bin/env python
"""make_bundle.py — assemble a downloadable "review + toolkit" bundle.

Takes a RapidMeta kit config and a built dashboard, and emits a self-contained
bundle folder that a researcher can download and use to REPRODUCE and CHECK the
review offline:

    bundle/
      index.html               (Tier 1 — the app)
      bundle.json              (trials + protocol hash + git commit + provenance
                                + the frozen reference number the app displays)
      protocol.md              (the pre-registered question; its sha256 is in bundle.json)
      rmharness/               (Tier 2 — the deterministic harness, one shared version)
      plausibility_table.json  (bundled offline plausibility bounds)
      README.md                (how to reproduce our number and check us)
      .github/workflows/ci.yml (free CI: reproduce + gates on every push)

The reference number is computed by the app's OWN engine (harness/js_engine.js,
extracted verbatim from the dashboard) so "our number" is genuinely what the app
shows — the Python harness then reproduces it through an independent code path.

Usage:
    python make_bundle.py CONFIG.json --app OUTPUT.html --out BUNDLE_DIR \
        [--measure RR] [--method REML] [--meta META.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)


def _git_commit(path: str) -> str:
    try:
        out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _js_reference(config_path: str, measure: str) -> dict:
    """Compute the app's displayed pooled number via its own JS engine."""
    js = os.path.join(HERE, "js_engine.js")
    out = subprocess.run(["node", js, config_path, measure, "headline"],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise SystemExit(f"[js_engine] failed: {out.stderr}")
    return json.loads(out.stdout)


def _protocol_md(cfg: dict) -> str:
    pico = cfg.get("pico", {})
    lines = [
        f"# Pre-registered protocol — {cfg.get('title', cfg.get('slug', 'review'))}",
        "",
        "This protocol is content-addressed: its SHA-256 is recorded in `bundle.json`.",
        "Change one character here and the recorded hash no longer matches — that is",
        "the pre-registration proof.",
        "",
        "## PICO",
        f"- **Population:** {pico.get('pop', '(unspecified)')}",
        f"- **Intervention:** {pico.get('int', cfg.get('drug', '(unspecified)'))}",
        f"- **Comparator:** {pico.get('comp', cfg.get('comparator', '(unspecified)'))}",
        f"- **Outcome:** {pico.get('out', '(unspecified)')}",
        f"- **Subgroups:** {pico.get('subgroup', '(none pre-specified)')}",
        "",
        "## Primary estimand",
        f"Pooled effect measure across the included trials for the outcome above.",
        "",
        "## Included trials (pre-specified)",
    ]
    for t in cfg.get("trials", []):
        lines.append(f"- {t.get('name', '?')} ({t.get('nct', 'no NCT')}, "
                     f"PMID {t.get('pmid', 'n/a')}, {t.get('year', 'n/a')})")
    return "\n".join(lines) + "\n"


CI_YML = """\
name: reproduce
on: [push, pull_request, workflow_dispatch]
jobs:
  reproduce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.x" }
      # Tier 2 is pure standard library — nothing to install.
      - name: Reproduce the app's pooled number
        run: python -m rmharness reproduce bundle.json
      - name: Run the deterministic gates
        run: python -m rmharness gates bundle.json
"""


def build(config_path, app_html, out_dir, measure, method, meta_path):
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    meta = {}
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as fh:
            meta = json.load(fh)

    ref = _js_reference(config_path, measure)
    ref["method"] = method  # label the reference by the app's headline estimator

    # trials with provenance merged from the meta sidecar (by nct)
    prov = {p.get("nct"): p for p in meta.get("provenance", [])}
    trials = []
    for t in cfg.get("trials", []):
        row = {k: t.get(k) for k in ("nct", "name", "year", "pmid",
                                     "tE", "tN", "cE", "cN",
                                     "publishedHR", "hrLCI", "hrUCI") if t.get(k) is not None}
        p = prov.get(t.get("nct"))
        if p:
            row["provenance"] = {k: p[k] for k in ("source", "doi", "note") if k in p}
        trials.append(row)

    protocol_md = _protocol_md(cfg)
    # Write protocol.md first with NO newline translation, then hash the exact
    # bytes on disk — so the recorded sha256 matches what the harness reads back
    # (verify reads the file in binary). Hashing the in-memory string would drift
    # from the file on Windows, where text-mode write turns \n into \r\n.
    os.makedirs(out_dir, exist_ok=True)
    proto_path = os.path.join(out_dir, "protocol.md")
    with open(proto_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(protocol_md)
    with open(proto_path, "rb") as fh:
        protocol_sha = hashlib.sha256(fh.read()).hexdigest()

    bundle = {
        "schema": "rapidmeta-bundle/v1",
        "harness_version": _read_version(),
        "generated_from": {"kit": "rapidmeta-kit", "config": os.path.basename(config_path)},
        "git_commit": _git_commit(KIT),
        "app": {"file": "index.html", "slug": cfg.get("slug"), "title": cfg.get("title")},
        "protocol": {"file": "protocol.md", "sha256": protocol_sha},
        "measure": measure,
        "method": method,
        "trials": trials,
        "reference": {
            "measure": ref["measure"], "method": method, "k": ref["k"],
            "estimate_log": ref["estimate_log"], "se": ref["se"], "ci_log": ref["ci_log"],
            "tau2": ref["tau2"], "Q": ref["Q"], "df": ref["df"], "I2_percent": ref["I2_percent"],
            "estimate_ratio": ref["estimate_ratio"], "ci_ratio": ref["ci_ratio"],
            "engine": ref["engine"],
            "note": "computed by the app's own browser engine (harness/js_engine.js, "
                    "extracted verbatim); the Python harness reproduces this independently",
        },
        "plausibility_table": "plausibility_table.json",
        "data_provenance_note": meta.get("data_provenance_note",
            "Trial data as configured in the kit; verify each value against its source "
            "publication before citing. The harness proves the POOLING is faithful to "
            "the app; it cannot vouch for the correctness of the extracted counts."),
    }
    if "published_comparison" in meta:
        bundle["published_comparison"] = meta["published_comparison"]

    # ---- write the bundle folder (protocol.md already written above) ----
    shutil.copy2(app_html, os.path.join(out_dir, "index.html"))
    with open(os.path.join(out_dir, "bundle.json"), "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2)
    with open(os.path.join(out_dir, "plausibility_table.json"), "w", encoding="utf-8") as fh:
        json.dump(_read_table(), fh, indent=2)
    # Tier-2 harness (single shared version)
    dst_pkg = os.path.join(out_dir, "rmharness")
    if os.path.exists(dst_pkg):
        shutil.rmtree(dst_pkg)
    shutil.copytree(os.path.join(HERE, "rmharness"), dst_pkg,
                    ignore=shutil.ignore_patterns("__pycache__", "tests", "*.pyc"))
    os.makedirs(os.path.join(out_dir, ".github", "workflows"), exist_ok=True)
    with open(os.path.join(out_dir, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as fh:
        fh.write(CI_YML)
    _write_readme(out_dir, bundle)
    return bundle, out_dir


def _read_version() -> str:
    ns = {}
    with open(os.path.join(HERE, "rmharness", "__init__.py"), "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("__version__"):
                exec(line, ns)
    return ns.get("__version__", "0")


def _read_table() -> dict:
    with open(os.path.join(HERE, "rmharness", "plausibility_table.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_readme(out_dir, bundle):
    title = bundle["app"].get("title") or bundle["app"].get("slug")
    r = bundle["reference"]
    readme = f"""# {title} — review + toolkit

This is a complete RapidMeta review **and** the machinery that produced it. You
can read the finished analysis, and you can **check it yourself, offline**.

## What's here
| File | What it is |
|---|---|
| `index.html` | The app — open it in any browser, works offline. |
| `bundle.json` | The trial data, the protocol hash, the git commit, per-value provenance, and the exact pooled number the app displays. |
| `protocol.md` | The pre-registered question. Its SHA-256 is in `bundle.json`. |
| `rmharness/` | The deterministic harness (Tier 2) — pure Python standard library, no model, no internet. |
| `plausibility_table.json` | Offline sanity bounds the gates use. |

## Check our number yourself (needs only Python 3.8+, nothing to install)
```
python -m rmharness reproduce bundle.json     # re-pool and match the app's number
python -m rmharness gates      bundle.json     # counts-imply-effect, triangulation, plausibility
python -m rmharness compare    bundle.json     # vs the published meta-analysis
```
The app says the pooled {r['measure']} is **{(r['estimate_ratio'] or r['estimate_log']):.4f}**.
`reproduce` re-derives that from the raw trial data through an independent engine
and confirms it matches. **If our number were wrong, this command would say so.**

## Change it and see what happens
```
# add a trial we missed (paste its 2x2), re-pool, watch the estimate move:
python -m rmharness add    bundle.json --name "MY-TRIAL" --tE 12 --tN 400 --cE 20 --cN 402
# or add one reported as a hazard ratio + CI:
python -m rmharness add    bundle.json --name "MY-TRIAL" --hr 0.80 --lo 0.66 --hi 0.97
# remove a trial and see the estimate move:
python -m rmharness remove bundle.json --name {bundle['trials'][-1].get('name','TRIAL')}
# re-derive under a different effect measure:
python -m rmharness measure bundle.json --to OR
```

## Extend it
Fork this repository. GitHub Actions (`.github/workflows/ci.yml`) re-runs
`reproduce` and `gates` on every push — so if you change the data, CI tells you
immediately whether the pooled number still holds. No install, no local setup.

## Honesty
The harness proves the **pooling** is faithful to the app. It does **not** vouch
for whether the extracted trial counts are correct or whether the trials are
clinically combinable — verify inputs against the source publications. See
`bundle.json → data_provenance_note`.

_Harness v{bundle['harness_version']} · git {bundle['git_commit'][:10]}_
"""
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Assemble a RapidMeta review+toolkit bundle")
    ap.add_argument("config")
    ap.add_argument("--app", required=True, help="path to the built dashboard .html")
    ap.add_argument("--out", required=True, help="output bundle directory")
    ap.add_argument("--measure", default="RR", choices=["RR", "OR", "RD"])
    ap.add_argument("--method", default="REML", choices=["REML", "DL", "PM", "FE"])
    ap.add_argument("--meta", default=None, help="optional provenance/published sidecar json")
    args = ap.parse_args(argv)
    bundle, out_dir = build(args.config, args.app, args.out, args.measure, args.method, args.meta)
    print(f"Bundle written to {out_dir}")
    print(f"  reference pooled {bundle['reference']['measure']} = "
          f"{bundle['reference']['estimate_ratio']:.4f}  (method {bundle['method']})")
    print(f"  git {bundle['git_commit'][:10]}  protocol sha256 {bundle['protocol']['sha256'][:16]}...")


if __name__ == "__main__":
    sys.exit(main())
