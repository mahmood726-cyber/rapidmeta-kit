# RapidMeta Kit — finerenone open-access meta-analysis benchmark

Status: **PROTOCOL REGISTERED / NOT YET REPRODUCED**  
Initiated: 7 November 2026  
Owner: Mahmood Ahmad; nine hourly work lanes and one hourly coordinator.

## Objective

Independently reconstruct a recent open-access cardiovascular meta-analysis of finerenone using the `rapidmeta-kit` repository, then assess improvements in reproducibility, evidence coverage, endpoint integrity, statistical robustness and clinical interpretability. Do **not** report reproduction, superiority, discrepancies or publication readiness until independently verified.

## Preselected benchmark

- Rivera-Martinez JC et al. **Effect of Finerenone in Cardiovascular and Renal Outcomes: A Systematic Review and Meta-analysis.** *Cardiovascular Drugs and Therapy*, published online 4 January 2025; 2026 volume 40, pages 167–179. DOI: https://doi.org/10.1007/s10557-024-07666-x. Publisher's full text: https://link.springer.com/article/10.1007/s10557-024-07666-x (open access).
- Finerenone's post-2005 development is grounded in Bärfacker et al., **Discovery of BAY 94-8862**, *ChemMedChem*, 2012. DOI: https://doi.org/10.1002/cmdc.201200081. The precise date of first chemical synthesis has not been independently established; the 2008 patent family and 2012 discovery report meet the project’s practical *post-2005 drug* criterion.
- Published search cutoff: **1 September 2024**. Included trials: FIDELIO-DKD (NCT02540993; n=5,674); FIGARO-DKD (NCT02545049; n=7,352); FINEARTS-HF (NCT04435626; n=6,001). Total **19,027 randomized participants**.
- Published analysis: generic inverse-variance random-effects meta-analysis of log HR for CV death and HF hospitalization; dichotomous random-effects RRs for all-cause mortality, renal failure and adverse events. The exact random-effects variance/CI implementation must be established before numerical equivalence claims.

### Published rounded targets, not RapidMeta output

| Outcome | Published model/measure | Estimate (95% CI) | Caveat |
| --- | --- | --- | --- |
| HF hospitalization | HR, random effects | 0.80 (0.72–0.90) | Main-text Results also label 0.80 as RR; resolve source tables and first-event vs recurrent definitions before evaluating a discrepancy. |
| CV death | HR, random effects | 0.91 (0.82–1.01) | Three trials. |
| All-cause death | RR, random effects | 0.86 (0.77–0.97) | Verify event counts and denominators. |
| Renal failure | RR, random effects | 1.05 (0.65–1.68) | Reported I²=83%; definitions may differ across trials. |
| Treatment-related hyperkalemia | RR, random effects | 2.31 (1.98–2.69) | Separate from investigator-reported hyperkalemia, published RR 2.09 (1.90–2.30). |
| Any serious adverse event | RR, random effects | 0.95 (0.91–0.98) | Verify definitions, counts and analysis populations. |
| Acute kidney injury | RR, random effects | 1.10 (0.78–1.53) | Reported I²=67%. |
| Urinary tract infection | RR, random effects | 1.00 (0.88–1.14) | Verify available trial data. |

Source for all published values: https://link.springer.com/article/10.1007/s10557-024-07666-x. The abstract reports HR for HF hospitalization; one Results sentence mislabels it RR. Do not treat the label difference as a proved numerical error.

## Required reconstruction sequence

1. **Freeze benchmark:** DOI, publisher version, publication date, trial set and prespecified endpoints. Confirm source rights and supplementary files. Do not use any prohibited JAMA content.
2. **Extract independently:** for each outcome × each trial, record source URL/DOI, trial/registry, version/date, table/figure/page, endpoint definition, follow-up, effect measure, point estimate, CI, numerator, denominator and analysis population. A second extractor must check every data item. `NOT_ENOUGH_INFO` is valid and must include a retrieval path and stop point.
3. **Reproduce published estimand:** same three trial families, same outcome definitions, same model, same effect measure (HR vs RR), same treatment of continuity corrections and heterogeneity. For HR use log(HR) and SE = [ln(upper CI)−ln(lower CI)]/(2×1.96) when only a symmetric 95% CI is available. For RR use verified 2×2 counts. Never convert HR to RR or estimate recurrent-event HR from first-event counts.
4. **Run RapidMeta Kit:** start from https://github.com/mahmood726-cyber/rapidmeta-kit (`python clone.py configs/<verified_config>.json`). The bundled finerenone example is **not** the benchmark input: its composite endpoint and example counts must not be silently reused for different outcomes. Use separate outcome-specific validated configs or an explicitly tested outcome representation. Validate browser output and independently compare with R or another checked statistical implementation.
5. **Compare:** table of published vs independently computed estimate, CI, I², model, trials and exact input provenance. Numeric agreement requires compatible endpoints and reproduction at the published two-decimal precision; record stronger precision internally. Explain any mismatch before calling it an error. Run model sensitivity (DL/REML and appropriate CI variants) without switching a benchmark model post hoc.
6. **Exceed the review only if supported:** update the search beyond 1 Sep 2024 in a separate analysis; audit RoB 2, GRADE, protocol/registry alignment; keep CKD/T2D and symptomatic HF populations distinguishable; distinguish first-event, recurrent event, and composite estimands; evaluate prediction intervals when estimable; report uncertainty/abstentions. Keep original three-trial replication frozen alongside any update.
7. **Conclude honestly:** `NOT_STARTED`, `EXTRACTION_PENDING`, `REPRODUCED`, `PARTIAL`, `MISMATCH_UNRESOLVED`, or `NOT_REPRODUCIBLE`, with links to evidence and actual outputs. Do not email authors/editors or claim scientific validation automatically.

## Lane assignments (hourly, staggered)

| Lane | Exclusive responsibility | Output |
| --- | --- | --- |
| Worker 1 | Source rights, full text/supplements, trial-family identity, eligibility and published methods | `workers/w01_sources.md` |
| Worker 2 | Cardiovascular mortality HR/CI reconstruction | `workers/w02_cv_death.md` |
| Worker 3 | HF hospitalization HR/CI; first vs recurrent event check | `workers/w03_hf_hosp.md` |
| Worker 4 | All-cause mortality RR, events and denominators | `workers/w04_all_cause.md` |
| Worker 5 | Renal failure RR, outcome identity, high I² | `workers/w05_renal.md` |
| Worker 6 | Both hyperkalemia definitions, safety populations | `workers/w06_hyperkalemia.md` |
| Worker 7 | Serious adverse events, AKI, UTI and remaining reported harms | `workers/w07_adverse_events.md` |
| Worker 8 | Independent statistical oracle, heterogeneity, model and CI sensitivity, RapidMeta build checks | `workers/w08_statistics.md` |
| Worker 9 | Updated search, population/indirectness, RoB 2/GRADE and clinical value beyond benchmark | `workers/w09_update_grade.md` |
| Controller | Read verified worker evidence, deduplicate, enforce QC, issue an honest comparison table and integrate checked outputs | `STATUS.md`, `comparison.csv` |

## Coordination and storage

- Public, non-confidential code/protocol and checked benchmark results: working branch in `mahmood726-cyber/rapidmeta-kit`, **never auto-merge unfinished work**.
- Private run checkpoint and duplicate protocol: connected Google Drive project folder; verify each upload/read-back and do not assert shared coordination before it works. Do not place private development notes, unpublished correspondence or confidential data on public GitHub.
- Workers should edit only their own paths. Controller is the sole writer to shared summaries and may update the status after verification. Before writing, read the existing artifact and retain previous evidence; never overwrite another lane's work.
- If a task's attached execution environment is unavailable, report the blocker. Do not claim a Kit run occurred merely because a plan or config was written.
- Existing safety restrictions remain: no automated JAMA Network processing, respect source rights/terms, no contact with Marco Zuin or coauthors about the excluded publications and all other opt-outs, and no unsolicited scientific outreach within this benchmark.

## Initial checkpoint

- Benchmark and published target estimates: **identified from open-access publisher article**.
- RapidMeta Kit repository/README and example finerenone config: **inspected**.
- Outcome-level trial extraction: **not yet completed**.
- RapidMeta Kit benchmark execution: **not yet run**.
- Independent numerical reproduction: **not yet established**.

