# Finerenone for cardiorenal outcomes in CKD — Living Meta-Analysis — review + toolkit

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
The app says the pooled RR is **0.8722**.
`reproduce` re-derives that from the raw trial data through an independent engine
and confirms it matches. **If our number were wrong, this command would say so.**

## Change it and see what happens
```
# add a trial we missed (paste its 2x2), re-pool, watch the estimate move:
python -m rmharness add    bundle.json --name "MY-TRIAL" --tE 12 --tN 400 --cE 20 --cN 402
# or add one reported as a hazard ratio + CI:
python -m rmharness add    bundle.json --name "MY-TRIAL" --hr 0.80 --lo 0.66 --hi 0.97
# remove a trial and see the estimate move:
python -m rmharness remove bundle.json --name FINEARTS-HF
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

_Harness v1.0.0 · git 7ef7be4381_
