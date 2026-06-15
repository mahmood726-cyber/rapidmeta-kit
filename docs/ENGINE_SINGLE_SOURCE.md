# One engine, one source of truth

This repo (`rapidmeta-kit`) is the **single canonical source** of the RapidMeta
analytic engine. This document records how the engine is distributed, why three
on-disk versions exist today, how drift is detected and gated, and the convergence
plan toward a single shared dependency.

## Canonical artifact

- **`template/base_dupilumab_copd.html`** — the engine (inline JS) + `assets/` (the
  offline runtime: stats vendor modules, Paper Studio, figures).
- `docs/index.html` is the deployed copy of the same build; the two are kept in lock-step.
- Every shipped correctness fix lands here **first**, with a regression test, and is
  propagated outward — never the reverse.

## The three versions that exist today (and why)

The engine is distributed by **copy / inline**, not as a shared runtime dependency.
That makes each dashboard self-contained and fully offline — the design goal — but it
means copies can drift behind the canonical engine:

| Version | Where | How it drifts |
|---|---|---|
| **A — canonical** | `rapidmeta-kit` (this repo) | source of truth; never drifts |
| **B — clones** | finerenone `e156-submission/*`, etc. | same logic, different whitespace; patched by codemod |
| **C — deployed fleet** | ~935 minified single-file dashboards | inline-minified engine; only regen/transplant updates it |

This is classic copy-paste distribution debt. The mitigations below make it *managed*
rather than silent.

## Propagation (how a fix reaches every dashboard)

1. **Fix + test in the kit** (this repo). CI must stay green.
2. **Codemod** for same-version clones — `scripts/fix_published_ratio_pooling.py`,
   `scripts/fix_extraction_patterns.py`: idempotent, anchored, with a self-test that
   proves byte-identical reproduction of the hand-edit, and a safety-abort that refuses
   to write a file that would call a helper it did not define.
3. **Regenerate** the deployed/clone dashboards from the kit via the
   `livingmeta-upgrade` transplant pipeline (lifts each dashboard's verbatim data layer
   and stamps it onto the current kit engine). This is the *only* reliable path for the
   minified fleet. (Done 2026-06-15 for all 41 LivingMeta dashboards.)
4. **External-asset shortcut** where available: dashboards that load an asset
   externally (e.g. `assets/js/paper-studio.js`) inherit updates from a *single file* —
   this is the convergence end-state in miniature (one update → whole fleet).

## Drift detection + CI gating

- **`scripts/check_engine_drift.py`** — scans dashboards for method-name markers
  (`trialHasPublishedRatio`, `isContinuousOutcome`) that survive minification and each
  represent a shipped correctness fix. `--self-check` asserts the kit base carries them
  all; audit mode flags drifted copies and exits non-zero.
- **`.github/workflows/ci.yml`** gates every push/PR with:
  - `pytest` (full suite, incl. the R-parity, paper-studio length-preset, continuous-
    routing, and forest regression tests) on Python 3.9/3.11/3.13 + Node 20;
  - **engine-integrity** job: drift self-check + inline-JS `node --check` on the
    canonical engine and the deployed copy + the R-parity harness vs the metafor anchors;
  - the deterministic example-dashboard smoke build.

## Validation anchors (so "correct" is testable, not asserted)

- **`docs/VALIDATION_DOSSIER.md`** + `tests/baselines/ma_core_baseline.json` +
  `tests/test_r_parity.py`: the random-effects REML pool of the BCG dataset agrees with
  the published metafor anchors to ~1e-4 and with an independent scipy re-derivation to
  <1e-9; a fixed-effect case is exact by hand. Quantities without an external anchor are
  labelled "baseline-only" — no parity is claimed that wasn't checked.

## Convergence plan (toward one shared dependency)

The end-state is **one engine loaded as a shared, versioned asset** rather than inlined
per dashboard — the Paper Studio asset already proves the model works at fleet scale.
Order of work, lowest-risk first:

1. **Done** — single source of truth + codemod/transplant propagation + drift detector +
   CI gating + validation baseline.
2. **In progress** — move the Paper Studio / figures / supplementary suite to external
   assets fleet-wide (already true for ~557 deployed dashboards).
3. **Next** — extract the core stats engine (pooling, τ², HKSJ, PI, NMA, DTA) into a
   single versioned module the base `<script src>`-loads, shrinking the inline surface.
4. **Then** — regenerate the remaining minified fleet from the kit so every dashboard
   loads the shared engine; the drift detector goes from "report" to "block on regen".

Until step 3 lands, the inline engine remains the reality; the detector + transplant +
CI keep it *managed and converging* rather than silently diverging.
