# Worker 09 — post-cutoff finerenone evidence, RoB 2/GRADE, population applicability

**Checkpoint:** 2026-11-07 (UTC) | **Status:** TARGETED UPDATE SCREENED; FORMAL UPDATE SEARCH AND RoB2/GRADE NOT YET COMPLETED.  
**Scope:** `benchmarks/finerenone_rivera_martinez_2025/workers/w09_update_grade.md` only; no changes to frozen three-trial inputs.  
**Benchmark:** Rivera-Martinez et al., DOI [10.1007/s10557-024-07666-x](https://doi.org/10.1007/s10557-024-07666-x), search through 2024-09-01; FIDELIO-DKD [NCT02540993] (5,674), FIGARO-DKD [NCT02545049] (7,352), FINEARTS-HF [NCT04435626] (6,001), n=19,027. The manuscript uses log-HR random effects for CV death and HF hospitalization, and RRs for other outcomes. The benchmark is **not** independently reproduced yet. This lane does not run the RapidMeta engine or claim benchmark-level numeric matching.

## Rights and search path

Sources inspected on 2026-11-07: publisher metadata for benchmark; publicly indexed PubMed abstracts/DOIs, open-access trial-design abstracts, ClinicalTrials.gov identifiers, and Cochrane methodology. The original review's licence is **CC BY-NC-ND 4.0** (non-commercial; no dissemination of adaptations): do not republish adapted figure/text, and separately confirm rights of each supplement. New NEJM trials below are indexed from **PubMed public abstracts**, not mined publisher full text; NEJM copyright is retained. JAMA Network documents excluded entirely; no emails.

Targeted discovery searches used `finerenone randomized trial 2025 2026 FIND-CKD FINE-ONE CONFIDENCE`, `site:pubmed.ncbi.nlm.nih.gov Finerenone randomized 2025 2026`, DOI/NCT follow-up, and review of [PubMed](https://pubmed.ncbi.nlm.nih.gov/) and trial design abstracts. This is a **targeted updated search, not an exhaustively documented PRISMA search**: Embase/registry comprehensive dedup, exact query strings and counts, unpublished studies, and second-person screening remain pending. No claim of exhaustive trial capture.

## New, independent families found AFTER the 2024-09-01 cutoff

| Family, DOI / registration | Actual study and evidence (not new members of frozen benchmark) | Eligibility / interpretation |
|---|---|---|
| **CONFIDENCE**, [10.1056/NEJMoa2410659](https://doi.org/10.1056/NEJMoa2410659), [PMID 40470996](https://pubmed.ncbi.nlm.nih.gov/40470996/), [NCT05254002](https://clinicaltrials.gov/study/NCT05254002); published **2025-06-05** | CKD **with T2D**; 3 arms finerenone, empagliflozin, or both, all with RAS blockade. 180-day **UACR change**, combination vs fin alone ratio **0.71 (0.61–0.82)**; combination vs empagliflozin ratio **0.68 (0.59–0.79)**. [Baseline open-access publication 10.1093/ndt/gfaf022](https://doi.org/10.1093/ndt/gfaf022) says **818 randomized**; a secondary summary describes **800 patients**: reconcile study/analysis denominators; do not invent 2x2 data. | **Separate active-comparator/combination, surrogate-endpoint synthesis**. Not a finerenone–placebo HF-hospitalization/CV-death estimate and no valid direct addition to the frozen meta. |
| **FINE-ONE**, [10.1056/NEJMoa2512854](https://doi.org/10.1056/NEJMoa2512854), [PMID 41780000](https://pubmed.ncbi.nlm.nih.gov/41780000/), [NCT05901831](https://clinicaltrials.gov/study/NCT05901831); published **2026-03-05** | CKD **with type 1 diabetes**, RAS blockade; **242 randomized**. Six-month UACR finerenone/placebo geometric ratio **0.75 (0.65–0.87)**; hyperkalemia **12 (10.1%) vs 4 (3.3%)**; exact safety denominators not confirmed from abstract. | **Separate T1D CKD UACR analysis**; biomarker not proof of fewer CV events/kidney failures, and not comparable to long-term clinical endpoints. |
| **FIND-CKD**, [10.1056/NEJMoa2604625](https://doi.org/10.1056/NEJMoa2604625), [PMID 42246672](https://pubmed.ncbi.nlm.nih.gov/42246672/), [NCT05047263](https://clinicaltrials.gov/study/NCT05047263); published **2026-06-04** (publisher update 2026-06-29) | CKD **without diabetes**, RAS blockade; **1,584 randomized, 793 finerenone and 791 placebo**. Primary total eGFR slope through month 32: **−3.3 vs −4.0 mL/min/1.73m²/year; difference +0.7 (0.3 to 1.1)**. Kidney-or-CV composite **HR 0.77 (0.60–0.99)**, kidney-only composite **0.78 (0.60–1.01)**, CV-only composite **0.60 (0.27–1.33)**. Hyperkalemia **135/793 vs 105/791**. Baseline design paper [PubMed/PMC11852274](https://pubmed.ncbi.nlm.nih.gov/PMC11852274) reports SGLT2 inhibitor use **16.9%**. | **Separate non-diabetic CKD synthesis** (eGFR slope and precisely specified composites); do **not** equate this composite with single HF hospitalization or CV-death HR. CV-only estimate broad CI, no stand-alone proven CV benefit. |

**Not independent additions / false-positive checks:** FINE-HEART [2024 participant-level pooled analysis](https://pubmed.ncbi.nlm.nih.gov/39218030/) reuses FIDELIO-DKD, FIGARO-DKD and FINEARTS-HF, so cannot count as an extra RCT. FINEARTS-HF subgroup analyses published in 2025–26 are the same [NCT04435626](https://clinicaltrials.gov/study/NCT04435626) family. A trial-design/baseline article is not another randomized outcome dataset. Other studies may exist: **NOT_ENOUGH_INFO** until comprehensive registry/Embase search.

## Independent computation (a stand-alone post-cutoff CHECK, NOT a pooled estimate)

Only **FIND-CKD investigator-reported hyperkalemia** uses source-confirmed event counts and randomization denominators [PMID 42246672](https://pubmed.ncbi.nlm.nih.gov/42246672/). Calculated ordinary crude risk ratio and log-Wald CI, **not** hazard ratio, adjusted RR, or RapidMeta output:

```text
a=135, n_t=793; c=105, n_c=791
RR=(135/793)/(105/791)=1.2824716267
SE[log(RR)]=sqrt(1/135 - 1/793 + 1/105 - 1/791)=0.1200248323
95% CI=exp(log(RR) +/- 1.96*SE)=(1.01363259, 1.62261305)
```

Result **RR 1.28 (95% CI 1.01–1.62)** is an **unadjusted, single-study** illustrative calculation. Trial report safety denominators, handling of post-randomization exclusions, events vs participants, and exact safety population still require independent verification before any inferential meta-analysis. It must **NOT** be compared as if matching the benchmark's treatment-related hyperkalemia **RR 2.31**; definitions and trial family differ. From published CIs only, approximate log-HR SE for FIND-CKD composite **[ln(0.99)−ln(0.60)]/3.92=0.12775**, a descriptive consistency calculation; endpoints do not match frozen benchmark.

## Population/endpoint/background-treatment matrix

- **FIDELIO/FIGARO**: CKD + T2D, kidney/CV prevention; **FINEARTS**: symptomatic HF with LVEF ≥40%, mix of CKD and diabetes status. The benchmark's three-trial mean is *not* directly a homogeneous HFpEF treatment effect. Trial entry criteria, 20/40-mg FINEARTS dosing versus 10/20-mg CKD trials, follow-up and event definitions differ ([benchmark publisher methods](https://link.springer.com/article/10.1007/s10557-024-07666-x)).
- **FINEARTS** primary recurrent HF-events-plus-CV-death is not interchangeable with **first** HF hospitalization, nor with a composite of kidney failure, ≥57% eGFR decline, HF hospitalization or CV death (FIND-CKD). No pooling of rate ratios, time-to-first HRs, 2×2 RRs or mean eGFR slope under one label.
- **SGLT2 background treatment** evolves across eras: FINEARTS-HF reported baseline SGLT2 inhibitor use **817/6001 (13.6%)**, [PMID 39340828](https://pubmed.ncbi.nlm.nih.gov/39340828/); FIND-CKD design baseline **16.9%**. CONFIDENCE randomizes simultaneous empagliflozin. Neither an across-trial interaction nor finerenone incremental effectiveness on contemporary quadruple therapy follows automatically.
- **Analysis strata for separate updates:** CKD+T2D; CKD+T1D; CKD without diabetes; symptomatic HF LVEF ≥40%. Additional exact endpoint, follow-up, comparator, and baseline SGLT2/RAAS categories before contemplating any across-stratum model.

## RoB 2 and GRADE — evidence **triage**, not adjudicated ratings

[Cochrane RoB 2](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-08) requires **result-level** assessments of randomization, deviations from assigned intervention, missing outcome data, outcome measurement and selective reporting. For each of CONFIDENCE UACR, FINE-ONE UACR, and FIND-CKD slope/composite/hyperkalemia: **ALL FIVE DOMAIN JUDGEMENTS = NOT_ENOUGH_INFO / assessment not conducted**. Double-blind randomized methods alone do not establish low risk; registered protocol/SAP history, ITT population, dropout, estimand and independent adjudication need a second assessor.

[Cochrane GRADE chapter 14](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-14): evaluate certainty **for each clinical question, comparison and outcome**, not globally by molecule. All final certainty ratings = **PENDING**. Candidate, *not applied*, downgrade rationales: (1) population indirectness for extrapolating CKD+T2D results to HFpEF, T1D or non-diabetic CKD; (2) endpoint indirectness of short-term UACR for CV death/kidney failure; (3) imprecision of FIND-CKD CV-only HR 0.60 (0.27–1.33); (4) inconsistency/heterogeneity should be examined on commensurate endpoints, not inferred just from differing populations. Selective-reporting check against time-stamped protocols/registries, missing data and publicity bias pending.

## Recommended next actions for controller, not claims of superiority

1. **Keep the frozen benchmark fixed** until workers 2–8 reproduce same three trials/outcomes/models. Do not append CONFIDENCE, FINE-ONE, FIND-CKD to its 19,027 denominator.
2. Commission second independent extractor and rights review for all three post-cutoff RCTs; collect registry revision histories and trial reports; verify 818 vs 800 for CONFIDENCE, safety populations in FIND/FINE-ONE and first-vs-recurrent-event definitions.
3. Conduct date-bounded, reproducible PubMed+Embase+ClinicalTrials.gov trial-family search, dedup by NCT and full exclusion log. Separate updated evidence maps/analyses by population, comparator and endpoint.
4. Perform outcome-specific RoB2 judgements and GRADE Summary-of-Findings, with positive and negative controls (FINE-HEART overlap; UACR ≠ CV mortality; first event ≠ recurrent).
5. **Unresolved:** no outcome-specific RapidMeta config/result for lane 9; no audited adverse-event denominator for other new families; no exhaustive search; no completed GRADE rating; no pooled updated effect. Neither superiority nor original-paper error established.

**No outreach, no public-main edits/merges.** This worker file consists of public-source bibliographic facts and our original analysis only.
