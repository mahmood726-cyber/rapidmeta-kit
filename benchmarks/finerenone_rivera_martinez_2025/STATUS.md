# Finerenone RapidMeta benchmark — controller reconciliation

**As-of:** 2026-11-07, 13:01 UTC (Chat-only GitHub + Drive + public publisher HTML).  
**Protocol:** [PROTOCOL.md](PROTOCOL.md), Rivera-Martinez et al. DOI [10.1007/s10557-024-07666-x](https://link.springer.com/article/10.1007/s10557-024-07666-x), online 2025-01-04, cutoff 2024-09-01.  
**Working branch:** `benchmark/finerenone-open-meta-2026` only; main unaffected.  
**Overall scientific status:** **PARTIAL / NOT_ENOUGH_INFO; zero fully reproduced outcomes using RapidMeta Kit.**

## Frozen benchmark

Three independent randomized trial families, total randomized **19,027**:
- FIDELIO-DKD, **NCT02540993**, n=5,674, original DOI **10.1056/NEJMoa2025845**.
- FIGARO-DKD, **NCT02545049**, n=7,352, original DOI **10.1056/NEJMoa2110956**.
- FINEARTS-HF, **NCT04435626**, n=6,001, original DOI **10.1056/NEJMoa2407107**.

The original review's full HTML is openly readable under CC BY-NC-ND 4.0: non-commercial factual extraction/analysis, no distribution of adapted figure or protected extracts. Trial sources independently need rights checks. The review specifies generic IV random-effects log HR for CV death and HF hospitalization, and random-effects dichotomous RR for death, renal and harms, without enough algorithm/precision detail to declare a complete model match. No JAMA material or outreach.

## Read-back reconciliation and evidence

Connected GitHub branch head inspected before these controller writes: `0ba59660fe104c2009ce09b4f5d108285b948111`. Worker reports actually fetched:
- W01 sources: **MISSING** from working branch and named project Drive folder as of this read; clearance/second-extractor gate unresolved.
- W02 CV death: [private Drive document](https://docs.google.com/document/d/1nRGO7REX4mR09tlarxPxQb0GKdeboGicU_c6w45foa8/edit) read. GitHub `workers/w02_cv_death.md` **not present** as of fetch/tree; no invented blob or commit.
- W03 [HF hospitalization](workers/w03_hf_hosp.md), blob `be39b659f961d85863fb9520561769c049213574`.
- W04 [all cause](workers/w04_all_cause.md), blob `f2d612579758dbad4126aaf4ba94fc42d0b4c97a`.
- W05 [renal](workers/w05_renal.md), blob `c59735e647e00d91d8fd8d2c187302abc0e37457`.
- W06 [hyperkalemia](workers/w06_hyperkalemia.md), blob `32c83507d39af1c98ed3576d623cd59933ccb17b`.
- W07 [other safety](workers/w07_adverse_events.md), blob `d749f8c00a8a55470e10a4cd646d57aef22a558a`.
- W08 [statistical oracle](workers/w08_statistics.md), blob `385124ef5aee37e394e3d327ff9258e0f477c11e`; [machine-readable oracle log](workers/w08_statistics_oracle_log_20261107.json) blob `32590269b6a32eabd797fa2c566612703f39c80a`, read and parsed.
- W09 [post-cutoff evidence map](workers/w09_update_grade.md), blob `59643c6af91d772e25625cc04e0e953061b960bd`.

The dedicated [private project Drive folder](https://drive.google.com/drive/folders/1BMNyCBu2Y2Al9AZMMVE8nwj8J7fJ5cZ2) was listed and W02/W08/W09 checkpoints read; folder presence alone is not proof of controller mirror write. This controller file and [comparison.csv](comparison.csv) are public numerical summaries, not private development notes.

## Counts and acceptance gates

- **10 distinct prespecified outcomes**: CV death, HF hospitalization, all-cause mortality, renal failure, regimen-related hyperkalemia, investigator-reported hyperkalemia, serious adverse events, AKI, UTI, pneumonia.
- **30 trial × outcome slots** (3 NCTs × 10). **29** slots have per-trial numerical inputs (published figure HR/logSE or reported 2×2 values; definitions/popu­lations not all adjudicated); **1** slot, FINEARTS renal failure, has **only rounded forest RR/CI**, no independently confirmed 2×2. Complete second-extractor source adjudication: **0 outcomes**.
- **13 independent oracle scenarios**, including variants/negative controls, in W08 numeric log. **9/10** outcomes show at least one conditional two-decimal *published-figure arithmetic* match under an explicitly labelled model and the printed input set; renal is approximate from rounded RRs only. These are **NOT** 9 independently reproduced scientific endpoints: figure replay may be circular, definitions may differ, and original Kit/CI parity is untested.
- **RapidMeta outcome-specific HTML/browser runs:** 0 verified. **Statistical-oracle-to-Kit crosschecks:** 0. **Strict `REPRODUCED` endpoints:** **0/10**. **Complete updated pooled analyses:** 0. An earlier generic Kit *example composite* generator smoke build does **not** count for this benchmark.
- W08 ran NumPy/SciPy/statsmodels (not R) with DL, REML, PM, HKSJ/floor sensitivity; Python cross-checks and reverse-arm controls reported. No independent source double extraction yet.

## Key unresolved differences (not error allegations)

1. **CV death (W02):** primary-trial CI-derived FINEARTS logSE ≈0.090005 vs review Fig.2 0.0710; original-trial IV HR 0.902372 [0.805472,1.010929] versus Fig.2 replay 0.907838 [0.820187,1.004857]. Why FINEARTS is overweighted remains unresolved.
2. **HF hospitalization (W03):** forest 0.82 [0.71,0.94] for FINEARTS appears to be a recurrent worsening-HF *rate ratio*, not first-hospitalization HR. Figure-only pooled 0.804429 [0.722759,0.895327] is not an estimand-integrity pass.
3. **All-cause mortality (W04):** FINEARTS review Table3 **70/3003 vs 97/2998** printed as all-cause deaths, yet same table reports **242 vs 260 CV deaths**. The figure replays to 0.874591 [0.788886,0.969608] vs paper text 0.86 [0.77,0.97]; separate original pooled source gives **491/3003 vs 522/2998**, leading to RR 0.917310 [0.848071,0.992201] in a differently sourced sensitivity. Verify follow-up, endpoint label, population.
4. **Renal failure (W05):** no FINEARTS 2×2 data aligned to RR 1.93 [1.22,3.03]; I²≈83% and published main text 1.05 [.65,1.68] vs Fig2 1.06 [.61,1.82]. Approximate REML fit of *rounded forest RRs* is not replication.
5. **Regimen-related hyperkalemia (W06):** FINEARTS **16/2993 vs 6/2993** appears *hyperkalemia hospitalization*, potentially incompatible with CKD trial treatment-attributed AEs. Although REML .00175593 gives 2.305049 [1.976315,2.688464], endpoint harmonization remains blocked.
6. **AKI (W07):** FINEARTS review 57/2897 vs 34/2888 may differ from another source's 111/2993 vs 64/2993. Important **RESOLVED statistical false-positive**: independent W08 REML (tau²=.06289609) *exactly* reproduces printed Fig3 1.10 [.78,1.53] without inserting tau; the DL difference is not a publication discrepancy.
7. **UTI (W07):** FINEARTS 29/3003 vs 26/2998 may represent a different adverse-event seriousness category than CKD studies. Confirm sources before pooling.

Across outcomes, study safety denominators, rounded inputs, RevMan/metabin/random-effects estimator and unmodified versus protected small-k CIs still require adjudication; do not switch models post hoc to force matches.

## Separately labelled post-cutoff evidence scan (W09, NOT a revised meta-analysis)

Targeted, **not exhaustive** search identifies three additional independent families *after* 2024-09-01:
- **CONFIDENCE** NCT05254002, DOI 10.1056/NEJMoa2410659, pub 2025-06-05: 3-arm combination/active comparator, short-term UACR, not direct placebocontrolled HF/CV target.
- **FINE-ONE** NCT05901831, DOI 10.1056/NEJMoa2512854, pub 2026-03-05: CKD with T1D, short-term UACR, not a clinical CV-death outcome.
- **FIND-CKD** NCT05047263, DOI 10.1056/NEJMoa2604625, pub 2026-06-04: CKD without diabetes, eGFR slope and separate composites. Unadjusted *single-study* hyperkalemia 135/793 vs105/791 RR 1.282472 [1.013633,1.622613]; not comparable to benchmark treatment-related RR.
No extra trial was inserted into frozen n=19,027; FINE-HEART pools the same three families (negative-control duplicate). Formal comprehensive search, RoB2 and GRADE remain pending.

## Decision / next verification order

1. W01 rights/supplements and original trial source map; W02 upload CV report to its owned GitHub path. Independent second extractor checks source version and each end­point/case definition and denominator.
2. W08 crosschecks trial-level original-source data and RevMan model estimator, particularly CV death FINEARTS SE, all-cause FINEARTS numerator and FINEARTS HFH rate ratio.
3. Only with validated inputs create distinct **outcome-specific configs**, have GitHub CI or available already-verified Kit build execute them, then independently check browser results vs oracle; an HTML generator success alone is insufficient.
4. Do not promote new results, change public main, claim superiority, merge, or contact authors/editors.

**No author/editor emails sent.** Source discrepancy is `NOT_ENOUGH_INFO` until each alternative is resolved.
