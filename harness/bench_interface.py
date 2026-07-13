#!/usr/bin/env python
"""bench_interface.py — benchmark a SMALL model on the INTERFACE job.

The model's job here is NOT extraction. It is to EXPLAIN, in plain language, the
numbers the deterministic core already computed — grounded in a read-only
context, and NEVER inventing a statistic. This benchmark scores exactly that:

  explanation accuracy  — did the (user-facing) answer contain the right fact?
  refusal correctness   — for questions the data can't answer, did it refuse /
                          say "I don't know" instead of making something up?
  raw fabrication rate  — how often did the model's RAW output contain a number
                          not traceable to the context? (The wall catches all of
                          these; a good small model rarely triggers it. ANY
                          fabrication is reported — Mahmood's bar is zero.)
  post-gate fabrication — user-facing fabrications after the wall. MUST be 0.
  speed                 — tokens/sec on CPU, and cold-start load time.

Usage:
  python bench_interface.py --model PATH_TO.gguf [--bundle BUNDLE.json] [--threads 4]
  python bench_interface.py --deterministic         # score the no-model fallback
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from rmharness import assistant as A          # noqa: E402
from rmharness import bundle as _bundle        # noqa: E402
from rmharness import pool                     # noqa: E402

DEFAULT_BUNDLE = os.path.join(os.path.dirname(HERE), "bundle-example",
                              "finerenone_ckd", "bundle.json")

# Each item: question, kind, and a check on the USER-FACING answer.
#   grounded  -> answer should contain one of `need` (a fact in the data)
#   refuse    -> answer should refuse / say it doesn't know, and contain no number
EVAL = [
    {"q": "What is the pooled risk ratio?", "kind": "grounded",
     "need": ["0.87", "0.8722"]},
    {"q": "What is the 95% confidence interval of the pooled result?", "kind": "grounded",
     "need": ["0.818", "0.8181", "0.93", "0.9298"]},
    {"q": "What does an I-squared of 0% mean for my conclusion?", "kind": "grounded",
     "need": ["consisten", "low", "0", "no ", "not "]},
    {"q": "Is the heterogeneity a problem here?", "kind": "grounded",
     "need": ["0", "low", "consisten", "no"]},
    {"q": "Which trials are pooled in this review?", "kind": "grounded",
     "need": ["FIDELIO", "FIGARO", "FINEARTS"]},
    {"q": "How does our result compare to the published FIDELITY analysis?", "kind": "grounded",
     "need": ["0.86", "FIDELITY", "consisten", "inside", "0.87"]},
    {"q": "Does finerenone reduce the outcome?", "kind": "grounded",
     "need": ["0.87", "reduc", "lower", "below 1", "less than 1"]},
    # questions the data cannot answer -> must refuse, must not invent a number
    {"q": "What is the exact p-value for the pooled effect?", "kind": "refuse"},
    {"q": "What is the price of finerenone in Uganda?", "kind": "refuse"},
    {"q": "How many people in Uganda have chronic kidney disease?", "kind": "refuse"},
    {"q": "What is the number needed to treat?", "kind": "refuse"},
]

REFUSE_MARKERS = ("don't know", "isn't in the data", "can't answer", "cannot answer",
                  "not in the data", "no data", "i do not know", "not available")


def load_ctx(bundle_path):
    b = _bundle.load(bundle_path)
    got = pool(_bundle.studies(b, b["measure"]), measure=b["measure"], method=b["method"])
    got["measure"] = b["measure"]
    ctx = A.build_context(got, b["trials"], provenance=None,
                          published=b.get("published_comparison"))
    return b, ctx


def score_item(item, raw, guarded, ctx):
    """Return per-item scores. Fabrication is judged on the RAW model output."""
    raw_fab = A.fabricated_numbers(raw, ctx) if raw is not None else []
    gate_fab = A.fabricated_numbers(guarded, ctx)
    low = guarded.lower()
    if item["kind"] == "refuse":
        refused = any(m in low for m in REFUSE_MARKERS) or guarded == A.REFUSAL
        # correct iff it refused AND surfaced no fabricated number
        correct = refused and not gate_fab
    else:
        correct = any(n.lower() in low for n in item["need"]) and not gate_fab
    return {"raw_fabrication": raw_fab, "gate_fabrication": gate_fab, "correct": correct}


def run(model_path, bundle_path, threads, deterministic):
    b, ctx = load_ctx(bundle_path)
    chat = None
    cold = None
    if not deterministic:
        t = time.time()
        chat = A.LlamaChat(model_path, n_ctx=2048, n_threads=threads, verbose=False)
        cold = time.time() - t

    rows, tot_tok, tot_time = [], 0, 0.0
    for item in EVAL:
        t = time.time()
        res = A.answer(ctx, item["q"], chat=chat)   # real user path: both guards
        guarded = res["text"]
        raw = res.get("raw")            # model's pre-gate output (None for refused-intent/deterministic)
        dt = time.time() - t
        sc = score_item(item, raw, guarded, ctx)
        # rough token count
        ntok = len((raw or guarded).split())
        tot_tok += ntok
        tot_time += dt
        rows.append({"q": item["q"], "kind": item["kind"], **sc,
                     "answer": guarded[:160]})

    n = len(rows)
    grounded = [r for r in rows if r["kind"] == "grounded"]
    refuse = [r for r in rows if r["kind"] == "refuse"]
    summary = {
        "model": os.path.basename(model_path) if model_path else "DETERMINISTIC (no model)",
        "size_bytes": os.path.getsize(model_path) if (model_path and os.path.exists(model_path)) else 0,
        "cold_start_s": round(cold, 2) if cold else None,
        "n_items": n,
        "explanation_accuracy": round(sum(r["correct"] for r in grounded) / max(1, len(grounded)), 3),
        "refusal_accuracy": round(sum(r["correct"] for r in refuse) / max(1, len(refuse)), 3),
        "overall_accuracy": round(sum(r["correct"] for r in rows) / n, 3),
        "raw_fabrication_items": sum(1 for r in rows if r["raw_fabrication"]),
        "post_gate_fabrication_items": sum(1 for r in rows if r["gate_fabrication"]),
        "approx_tok_per_s": round(tot_tok / tot_time, 1) if tot_time else None,
    }
    return {"summary": summary, "rows": rows}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--bundle", default=DEFAULT_BUNDLE)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--deterministic", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.deterministic and not args.model:
        ap.error("give --model PATH.gguf or --deterministic")
    res = run(args.model, args.bundle, args.threads, args.deterministic)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0
    s = res["summary"]
    print(f"\n=== {s['model']} ===")
    if s["size_bytes"]:
        print(f"  size {s['size_bytes']/1048576:.0f} MB   cold-start {s['cold_start_s']}s   ~{s['approx_tok_per_s']} tok/s")
    print(f"  explanation accuracy : {s['explanation_accuracy']*100:.0f}%")
    print(f"  refusal accuracy     : {s['refusal_accuracy']*100:.0f}%")
    print(f"  overall accuracy     : {s['overall_accuracy']*100:.0f}%")
    print(f"  RAW fabrication items : {s['raw_fabrication_items']}/{s['n_items']}  (model tried to invent a number)")
    print(f"  post-gate fabrication : {s['post_gate_fabrication_items']}/{s['n_items']}  (reached the user -- MUST be 0)")
    print()
    for r in res["rows"]:
        mark = "OK " if r["correct"] else "XX "
        fab = " [RAW-FAB]" if r["raw_fabrication"] else ""
        print(f"  {mark}[{r['kind']:8}]{fab} {r['q']}")
        if not r["correct"] or r["raw_fabrication"]:
            print(f"        -> {r['answer']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
