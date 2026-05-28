# rapidmeta-kit

Spin up the **full interactive RapidMeta dashboard** for any topic by editing
a small JSON file and running one command. You get the complete workbench —
protocol, search, screening, risk-of-bias, editable extraction, live
re-pooling, a 28-panel statistics tab, GRADE Summary of Findings, WebR
R-validation, PRISMA flow — all running in the browser, offline.

The heavy engine (~1 MB) and its stat-panel scripts are **pre-built and
bundled**. The only thing that changes per review is a ~20-line config, so an
AI CLI (Gemini, Claude, etc.) on a free / rate-limited key can produce many
dashboards without burning quota.

> Want a *lightweight* static one-page meta-analysis instead (tiny output, no
> interactive engine)? See the sister project
> **[meta-starter-kit](https://github.com/mahmood726-cyber/meta-starter-kit)**.
> This repo is the *full* interactive version.

---

## ⬇️ Download (one click)

**[Download the whole kit as a ZIP »](https://github.com/mahmood726-cyber/rapidmeta-kit/archive/refs/heads/main.zip)**

Unzip it. Or grab a versioned copy from the
[Releases page](https://github.com/mahmood726-cyber/rapidmeta-kit/releases).

## ▶️ Use it in 3 steps

1. **Install Python** (once): <https://www.python.org/downloads/> — on
   Windows tick **"Add Python to PATH"** during install.
2. **Run the example.**
   - **Windows:** double-click **`RUN_EXAMPLE.bat`**.
   - **Mac/Linux:** `bash run_example.sh`.
   - **Any terminal:** `python clone.py configs/example_finerenone_ckd.json`
3. **Open** `output/finerenone_ckd.html` in a browser. That is a complete,
   interactive RapidMeta dashboard for finerenone — click through Screening,
   Extraction, and the Analysis Suite tabs.

## Make your own

1. Copy an example config:
   ```
   copy configs\example_finerenone_ckd.json configs\my_review.json   (Windows)
   cp   configs/example_finerenone_ckd.json configs/my_review.json   (Mac/Linux)
   ```
2. Edit `configs/my_review.json` — set the drug, condition, and trials
   (see [Config](#config)).
3. Build:
   ```
   python clone.py configs/my_review.json
   ```
4. Open `output/<your_slug>.html`.

## Config

Minimum:
```json
{
  "drug": "Finerenone",
  "slug": "finerenone_ckd",
  "condition": "CKD in type 2 diabetes",
  "title": "Finerenone for CKD — Living Meta-Analysis",
  "trials": [
    { "nct": "NCT02540993", "name": "FIDELIO-DKD", "year": 2020,
      "tE": 367, "tN": 2833, "cE": 420, "cN": 2841 },
    { "nct": "NCT02545049", "name": "FIGARO-DKD", "year": 2021,
      "tE": 458, "tN": 3686, "cE": 519, "cN": 3666 }
  ]
}
```
- `tE`/`tN` = events/total in the intervention arm; `cE`/`cN` = comparator arm.
- Or give a published effect instead: `"publishedHR": 0.86, "hrLCI": 0.75, "hrUCI": 0.99`.
- Optional extras: `comparator`, `hero_h2`, `nyt_headline`, `pico`,
  `acronyms`, per-trial `pmid` / `phase` / `group` / `allOutcomes`.
- See `configs/example_finerenone_ckd.json` for a fully-populated example.

The build prints a `[CONFIG ERROR]` naming exactly what to fix if a field is
missing or malformed.

## How it works

`clone.py` stamps your config onto `template/base_dupilumab_copd.html` (the
validated RapidMeta base, unminified) — it swaps the drug/condition tokens
and replaces the trial dataset — then copies the shared `assets/` folder
(stylesheet, plotly, and the 28 stat-panel scripts) next to your output so it
runs offline. No statistics are recomputed by an LLM; the dashboard does all
analysis in the browser.

## Offline notes

- Everything runs client-side and works offline **once downloaded**, except:
  - **Icons** use a Font Awesome CDN (cosmetic; the page is fully usable
    without them).
  - The live **CT.gov / PubMed lookups** inside the Search tab need internet
    (optional — you can paste/extract data manually).
- Network-meta-analysis plots use the bundled Plotly (`assets/plotly.min.js`)
  — no internet needed.

## What NOT to edit

Only ever create/edit files in `configs/`. `template/` (engine + `assets/`)
and `clone.py` are finished. `output/` is regenerable.

## Honesty

Each dashboard is an **auto-generated draft**. The kit wires your trial data
into a working analysis app; it cannot judge whether the trials are
clinically combinable or whether the extracted numbers are correct. Verify
inputs against source publications before using or citing any result.
