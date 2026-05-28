# GEMINI.md

Gemini CLI: read **[AGENTS.md](AGENTS.md)** — it is the full, authoritative
guide. Summary so you don't spend tokens re-reading:

> This is a finished, full-featured RapidMeta dashboard builder. To make a
> new review: copy `configs/example_finerenone_ckd.json`, replace the drug /
> condition / trial data with the user's numbers, and run
> `python clone.py configs/<file>.json`. The dashboard lands in `output/`.
> Do **not** edit `template/`, `assets/`, or `clone.py` — the 1 MB engine,
> the 28 statistics panels, and the styling are already built. Output only
> the small config JSON; the build is deterministic and uses no API calls,
> which conserves your quota.
