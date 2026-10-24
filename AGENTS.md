# AGENTS.md — instructions for AI CLIs (Gemini CLI, Claude Code, etc.)

You are helping someone create a **full interactive RapidMeta dashboard** —
the complete workbench: protocol, search, screening, risk-of-bias,
editable extraction, live re-pooling, a 28-panel statistics tab, GRADE
Summary of Findings, WebR R-validation, PRISMA flow. The whole engine is
already built and bundled. Your job is **small and cheap**: write one short
JSON config, then run one command.

## The only workflow

1. Copy `configs/example_finerenone_ckd.json` to `configs/<your_topic>.json`.
2. Replace the drug / condition / trial data with the user's numbers.
3. Run: `python clone.py configs/<your_topic>.json`
4. The finished dashboard appears at `output/<slug>.html`. Open it in a browser.

That's the normal **new-topic** workflow. Do not edit `template/` (the 1 MB
engine + assets) or `clone.py` when only creating a topic; these files may be
changed for explicit generator/engine maintenance, with regression tests.

## Token discipline (important on free / low-quota API keys)

- The config is the ONLY thing you generate. Keep it tight.
- Never read, paste, or rewrite the template, the assets, or the built HTML
  — they are large and unchanging.
- `clone.py` makes zero API calls; pin `date` for byte-for-byte deterministic
  metadata. You can build dashboards without spending API quota.
- On a `[CONFIG ERROR]`, fix only the field it names.

## Config format

```json
{
  "drug": "Finerenone",
  "slug": "finerenone_ckd",
  "condition": "CKD in type 2 diabetes",
  "comparator": "Placebo",
  "title": "Finerenone CKD — illustrative two-trial dashboard",
  "hero_h2": "Finerenone for cardiorenal outcomes in type 2 diabetes with CKD",
  "nyt_headline": "Two trials of finerenone in diabetic kidney disease",
  "pico": {
    "pop": "Adults with type 2 diabetes and CKD",
    "int": "Finerenone",
    "comp": "Placebo",
    "out": "CV death, nonfatal MI, nonfatal stroke, or HF hospitalisation",
    "subgroup": "By baseline eGFR"
  },
  "acronyms": { "NCT02540993": "FIDELIO-DKD" },
  "trials": [
    { "nct": "NCT02540993", "name": "FIDELIO-DKD", "pmid": "33264825",
      "phase": "III", "year": 2020,
      "tE": 367, "tN": 2833, "cE": 420, "cN": 2841,
      "group": "Finerenone vs placebo",
      "publishedHR": 0.86, "hrLCI": 0.75, "hrUCI": 0.99,
      "reportedEffectType": "HR",
      "allOutcomes": [{ "shortLabel": "CV composite",
                        "title": "CV death, nonfatal MI/stroke, or HF hospitalisation",
                        "type": "binary" }] }
  ]
}
```

### Required fields
- `drug` — display name (e.g. "Finerenone")
- `slug` — lowercase id, letters/digits/underscores only (e.g. `finerenone_ckd`)
- `condition` — the population/disease (e.g. "CKD in type 2 diabetes")
- `title` — the page `<title>`
- `trials` — at least 1 (use 2+ to get a pooled meta-analysis)

### Each trial needs at minimum
- `nct` (registry id, or other safe unique id with a verified `sourceUrl`)
  and `name`.
Strongly recommended for a real analysis:
- Event counts `tE`/`tN` (intervention events/total) and `cE`/`cN`
  (comparator events/total) — these drive the live pooling; OR
- A published **hazard ratio** `publishedHR` with `hrLCI` / `hrUCI` and
  `reportedEffectType: "HR"` (verified from the publication). This field
  cannot carry odds ratios, risk ratios, or recurrent-event rate ratios.
- `pmid`, `phase`, `year`, `group`, and an `allOutcomes` entry are optional
  but make the dashboard richer.

### Optional top-level fields
`comparator` (default "Placebo"), `drug_lower` (default = drug lowercased),
`hero_h2`, `nyt_headline`, `pico`, `acronyms`.

## Rules

- Use real numbers from the source the user gives you. Never invent trial data.
- Confirm the outcome definition, follow-up, unit of analysis, and effect
  measure *across every trial*; a green build cannot validate clinical pooling.
- One config = one topic. The dashboard handles multiple outcomes internally.
- The page is an auto-generated **draft**, not an independently screened,
  RoB-2-adjudicated, GRADE-verified, or regulatory-ready systematic review.

## Don't

- Don't `pip install` anything — `clone.py` is standard-library Python 3.8+.
- Don't edit `template/` or `assets/` or `clone.py`.
- Don't delete `output/assets/` — it holds the styles and stat-panel scripts
  the dashboards load (offline).
