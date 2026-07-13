# RapidMeta harness — bundle a review with the machinery that made it

This turns every RapidMeta review from a **dead end** (a page you read and leave)
into a **seed**: the researcher downloads the finished review *and* the
deterministic machinery that produced it, so they can add a trial we missed,
change the PICO, re-pool, and **check our numbers themselves** — offline, on a
field laptop, in seconds.

## The three tiers

| Tier | What | Size (measured, finerenone example) | Needed for |
|---|---|---|---|
| **1 — the app** | the RapidMeta dashboard, one HTML file, offline | **1.20 MB** (+2.83 MB shared assets, downloaded once) | reading + in-browser re-pool |
| **2 — the harness** | `rmharness/` — pure-Python, **no model, no network** | **20.6 KB zipped** / 50 KB unzipped | reproduce & check our number, add/remove trials, re-run gates |
| **3 — the model** | optional GGUF LLM | **1.0 GB** (Qwen2.5-1.5B Q4) – 4.7 GB (7B Q4) | extracting from *new* papers you bring |

The whole **review + toolkit is a single 0.27 MB download** (Tier 1 + Tier 2,
zipped). Tier 3 is optional and most users never need it.

## Tier 2 is the honesty guarantee
`rmharness` re-pools the trial data through an **independent code path** and
confirms it matches the number the app displays. Two engines — the app's browser
JavaScript and this Python — agree to the last bit (`tests/test_reproduce.py`).
**If our number were wrong, `reproduce` would say so.**

```
python -m rmharness reproduce bundle.json   # match the app's pooled number
python -m rmharness gates       bundle.json   # counts-imply-effect, triangulation, plausibility, pre-reg hash
python -m rmharness compare     bundle.json   # vs the published (e.g. Cochrane) meta-analysis
python -m rmharness add    bundle.json --name NEW --tE 12 --tN 400 --cE 20 --cN 402
python -m rmharness remove bundle.json --name FIGARO
python -m rmharness measure bundle.json --to OR
```

## Building a bundle from a kit config
```
python clone.py configs/my_review.json                       # build the Tier-1 app
python harness/make_bundle.py configs/my_review.json \        # assemble the bundle
    --app output/my_review.html --out bundle-example/my_review \
    --measure RR --method REML --meta configs/my_review_meta.json
```
The reference number is computed by the app's **own** engine
(`harness/js_engine.js`, extracted verbatim from the dashboard) so "our number"
is genuinely what the app shows.

## Files
- `rmharness/` — the versioned Tier-2 package (one source, shared by every bundle).
  - `pooling.py` — the deterministic pooler (DL/PM/REML/FE, log-scale, conditional 0.5 CC). Bit-identical to the app's REML headline.
  - `gates.py` — counts-imply-effect, triangulation, SE-triangulation, plausibility.
  - `bundle.py` / `verify.py` / `__main__.py` — bundle loader, checks, CLI.
  - `plausibility_table.json` — offline sanity bounds.
- `js_engine.js` — the app's pooling functions, extracted verbatim (the reproduction target).
- `make_bundle.py` — assembles a downloadable review+toolkit bundle.
- `tests/` — reproduction proof, tamper-detection, gate, and CLI tests.

## Licence
Everything **bundled** is MIT-redistributable: the kit (MIT, © 2026 Mahmood
Ahmad), Plotly.js v2.35.2 (MIT, inlined), and `rmharness` (MIT, pure stdlib).
Font Awesome / Google Fonts are CDN-only cosmetics (not redistributed; the app
degrades gracefully offline). Tier-3: ship only the **Apache-2.0** Qwen variants
(1.5B / 7B) — **never the 3B** (non-commercial Qwen Research licence).
