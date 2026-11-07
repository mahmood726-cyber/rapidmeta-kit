# W07 — Serious adverse events, acute kidney injury, urinary infection, pneumonia

**Checkpoint 2026-11-07 (UTC); status: PARTIAL, numerical display-precision match for four outcomes under independently computed REML; not independently validated or Kit-reproduced.** Working branch: `benchmark/finerenone-open-meta-2026`. Scope restricted to Worker 7 safety endpoints. This note contains only public numerical evidence, calculation methods and open questions. Do not merge to main. No outreach.

## Benchmark identity and source/rights
Rivera-Martinez JC et al., *Cardiovascular Drugs and Therapy*, online 2025-01-04, DOI [10.1007/s10557-024-07666-x](https://doi.org/10.1007/s10557-024-07666-x). Original three-trial set: FIDELIO-DKD NCT02540993 (2020, DOI 10.1056/NEJMoa2025845), FIGARO-DKD NCT02545049 (2021, DOI 10.1056/NEJMoa2110956), FINEARTS-HF NCT04435626 (2024, DOI 10.1056/NEJMoa2407107). PubMed/Embase search cutoff 2024-09-01. Publisher article is available open access under CC BY-NC-ND 4.0; numerical results below are attributed, not extensive reproductions of copyrighted text or adapted figures.
- [Publisher PDF](https://link.springer.com/content/pdf/10.1007/s10557-024-07666-x.pdf), **printed p.176 Table 4 / p.177 Fig. 3**. This run independently inspected the PDF pages and transcribed all four relevant rows, checked the Fig. 3 forest denominators and reported statistics.
- [FIDELIO original Table 3](https://www.nejm.org/doi/full/10.1056/nejmoa2025845) includes safety population 2827/2831 and AE definitions.
- [FIGARO EU trial results](https://www.clinicaltrialsregister.eu/ctr-search/trial/2015-000950-39/results) confirms serious AE counts 1158/3683 versus 1215/3658; [CT.gov NCT02545049](https://clinicaltrials.gov/study/NCT02545049), registry posted 2022-04-15.
- [FINEARTS related safety by kidney function](https://www.jacc.org/doi/10.1016/j.jacc.2024.10.091) reports all-serious-AE counts 1157/2993 versus 1213/2993 and alternative investigator-reported AKI numbers 111 versus 64 (2025 issue, hence **cross-check only, not automatically a historical benchmark input**).
- [FIDELITY prespecified pooled CKD safety table](https://doi.org/10.1093/eurheartj/ehab777) provides an independent FIDELIO+FIGARO reasonableness check; pooled reports should never be added as a fourth trial.
- No prohibited JAMA material used. The source article is OA, but extraction provenance and source usage must continue to respect publisher license/terms.

## Frozen published extraction: events / denominator (finerenone ; placebo)

| Endpoint | FIDELIO NCT02540993 | FIGARO NCT02545049 | FINEARTS NCT04435626 | Published pooled RR (95% CI); I² |
| --- | --- | --- | --- | --- |
| Any serious adverse event | 902/2833 ; 971/2841 | 1158/3686 ; 1215/3666 | 1157/2993 ; 1213/2993 | 0.95 (0.91–0.98); 0% |
| Acute kidney injury | 129/2833 ; 136/2841 | 91/3686 ; 98/3666 | 57/2897 ; 34/2888 | 1.10 (0.78–1.53); 67% |
| Urinary tract infection | 179/2833 ; 192/2841 | 252/3686 ; 240/3666 | 29/3003 ; 26/2998 | 1.00 (0.88–1.14); 0% |
| Pneumonia | 128/2833 ; 181/2841 | 143/3686 ; 206/3666 | 87/3003 ; 110/2998 | 0.72 (0.63–0.82); 0% |

Table 4 uses headline randomized denominators (FIDELIO 2833/2841; FIGARO 3686/3666; FINEARTS 3003/2998) even though trial AE/safety denominators are typically smaller. Its FINEARTS serious AE and AKI entries explicitly give distinct denominators. Fig. 3 numerically matches the denominators above (with FINEARTS serious AE 2993/2993 and AKI 2897/2888). Note p.177 Fig. 3 reports AKI tau²=0.0629 and no other W07 harm outcome has tau²>0.

## Independently computed, using published inputs above
Method: per trial `y = ln((a/n_t)/(c/n_c))`, `v = 1/a - 1/n_t + 1/c - 1/n_c`; inverse-variance random-effects on log RR, conventional normal 95% CI, `Q = sum((y-y_FE)^2/v)`, `I²=max(0,(Q-(k-1))/Q)*100`, classical DerSimonian–Laird tau² = `max(0,(Q-(k-1))/(sum(w)-sum(w²)/sum(w)))`, random weights `1/(v+tau²)`. Three independent trial records per endpoint; no continuity correction because no zero cells. Computed offline in Python using math/NumPy only; **not** a RapidMeta browser run nor independent R oracle. Decimal results are reproducible via the formulas provided.

| Endpoint | Calculated IV-DL RR [95% CI] | Calculated I² | Calculated tau² | Gate versus published (two decimals) |
| --- | --- | --- | --- | --- |
| Serious AE | **0.945675 [0.909692, 0.983081]** | 0% | 0 | matches 0.95 [0.91,0.98] |
| AKI | **1.088416 [0.801784, 1.477515]** | 67.10% | 0.048133 | **does not match** 1.10 [0.78,1.53] under THIS tau estimator |
| UTI | **1.002167 [0.884143, 1.135946]** | 0% | 0 | matches 1.00 [0.88,1.14] |
| Pneumonia | **0.719077 [0.629654, 0.821199]** | 0% | 0 | matches 0.72 [0.63,0.82] |

**AKI model reconciliation, not independent reproduction:** the published Fig.3 tau²=0.0629 (versus 0.048133 under our IV-DL formula). Substituting *published* 0.0629 into the inverse-variance weights gives RR **1.095442 [0.782977,1.532605]**, which rounds exactly to **1.10 [0.78,1.53]** (z p=0.595). This supports a random-effects variance implementation difference as an explanation, but reuse of published tau² is **circular** and cannot validate its derivation. Independently reproduce the original random-effects `metabin`/RevMan weighting/tau² method (likely MH-versus-IV differences) before PASS. Do not label a numerical error at this stage. The paper's Fig.3 shows tau²=0.0629, and I²=67%.

### Endpoint identity and denominator safeguards
1. **Numerator/denominator mismatch:** the original FIDELIO safety denominator is 2827 finerenone / 2831 placebo, FIGARO safety denom 3683/3658, versus 2833/2841 and 3686/3666 inserted in the review forest. Using true safety denominators for serious AEs yields 0.944863 [0.908921,0.982225] vs 0.945675 [0.909692,0.983081] from forest denominators, still the same two-decimal pooled RR/CI. This is a verifiable population-label mismatch, not proven substantive error.
2. **FINEARTS AKI non-equivalence:** review Table 4/Fig.3 uses 57/2897 vs 34/2888; another publicly available FINEARTS safety analysis reports 111/2993 vs 64/2993. Possible different timing, diagnostic definitions, monitoring subsets or source cutoffs; abstain from assuming interchangeable endpoints. Using the latter gives independent IV-DL 1.141013 [0.780627,1.667775], I²=82.83%, **not** a comparable replication of the review's AKI data. Source-definition matching and author-independent registry/protocol adjudication needed.
3. **UTI definition:** FINEARTS 29 vs 26 occurs in a *serious-event preferred-term* source; CKD trial UTI counts 179/192 and 252/240 appear under all AE. Verify original FINEARTS main-trial safety table and common seriousness/ascertainment windows before treating these as one harmonised endpoint. It may instead be that identical small count appears in both definitions; do not assume either way.
4. **Pneumonia:** review Fig.3/p.177 actually labels the RR **0.72 [0.63,0.82] as pneumonia**. In narrative results, the last sentence calls this `risk of heart failure`; do not use that narrative label for pooled harm evidence. Numerically reproduced against the *pneumonia* row; a textual label difference is flagged for editorial verification, not yet confirmed as publication error.
5. **Trial-family de-dup:** FIDELITY (NCT02540993+NCT02545049) must not be included as an extra independent trial; same for secondary FINEARTS papers.
6. **Confidence in comparison:** double extraction, official AE definitions/populations and an independent checked statistical oracle are still pending. No outcomes here can yet be marked `REPRODUCED` by RapidMeta Kit.

## Work remaining / acceptance
- Have independent second extractor verify Table 4 and Fig.3 exact input values, especially FINEARTS AKI 57/2897 vs34/2888.
- Confirm exact MH/random-effects tau² method leading independently to 0.0629 (no use of published tau²) and run separate outcome-specific validated configs through actual RapidMeta Kit/browser; compare browser and independently checked R or statistical software output.
- Source-authoritative trial AE definition/revision and denominator reconciliation, including 29/26 UTI semantics, renal SAE versus AKI, and pneumonia. Freeze published three-trial analysis before any new search/revision.
- Gate statuses: serious AE / UTI / pneumonia: `PARTIAL — independently calculated at reported precision; no Kit/R cross-validation`. AKI: `MISMATCH_UNRESOLVED — tau² model implementation not recovered`. No claimed improvement, correction, email or merge.


## 2026-11-07 13:32 UTC — AKI REML numerical reconciliation

**New independent Chat-only arithmetic check, no local shell and no RapidMeta Kit run.** Same three trials and frozen source inputs on printed Table 4 / Figure 3 of the [open-access Rivera-Martinez review](https://link.springer.com/article/10.1007/s10557-024-07666-x), DOI 10.1007/s10557-024-07666-x. For AKI: FIDELIO-DKD NCT02540993 **129/2833 vs 136/2841**; FIGARO-DKD NCT02545049 **91/3686 vs 98/3666**; FINEARTS-HF NCT04435626 **57/2897 vs 34/2888** (finerenone versus placebo). All other endpoints and DOI-level provenance remain in the frozen extraction above. No JAMA data, no contact or outreach.

**New resolution of the previously unexplained AKI tau²**: derive between-study variance independently using **restricted maximum likelihood (REML)**, not the published figure's tau² as input. For each trial: `y_i = log((a_i/nT_i)/(c_i/nC_i))`, `v_i = 1/a_i-1/nT_i+1/c_i-1/nC_i`; `w_i(t)=1/(v_i+t)`, `mu(t)=sum(w_i*y_i)/sum(w_i)`. Solve the REML score `sum(w_i²*(y_i-mu)²)-sum(w_i)+sum(w_i²)/sum(w_i)=0` for `t>=0`. A second computational route directly maximized `L_REML(t)=-0.5*[sum(log(v_i+t))+log(sum(w_i))+sum(w_i*(y_i-mu)²)]` by golden-section optimization (same data, independent numerical route; **not independent data extraction or separate statistical software**).

- **Score-equation REML:** AKI tau² **0.0628960925**, RR **1.0954405868**, normal 95% CI **0.7829813431–1.5325908974**. Baseline fixed-weight Q **6.0793222309**, I² **67.1015958%**. Rounds to **1.10 (0.78–1.53), tau² 0.0629, I² 67%** exactly as the published Fig. 3. Crucially, published tau² was **not used** in computing these.
- **Restricted-likelihood optimization cross-check:** tau² **0.0628960946**, RR **1.0954405876**, CI **0.7829813405–1.5325909046**, agreeing with score-equation root within numerical tolerance.
- **Predeclared estimator sensitivity:** IV DerSimonian–Laird tau² **0.0481326033** => RR **1.0884157212 (0.8017844663–1.4775152573)**; Paule–Mandel tau² **0.0749236371** => RR **1.0998081596 (0.7685522792–1.5738395692)**. The earlier DL mismatch therefore need not imply a transcription or publication error. The paper states a dichotomous random-effects RR model in RevMan but **does not specify a tau² estimator in the accessible prose**; REML's precise match is strong **method-inference evidence, not documentary proof** of the software setting.
- **Same REML procedure, all W07 endpoints:** serious AE RR **0.9456749921 (0.9096920263–0.9830812680)**, tau² 0; UTI RR **1.0021665786 (0.8841425109–1.1359456637)**, tau² 0; pneumonia RR **0.7190767110 (0.6296537189–0.8211994955)**, tau² 0. Thus all four **independent numerical calculations** agree with reported pooled values at 2-decimal display precision, including AKI. No zero cells or continuity correction; all 3 trial families represented once each.
- Source-method references: [Cochrane RevMan 5 statistical algorithms](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/statistical-methods-revman5) describe a DL implementation; [CRAN meta package methods](https://search.r-project.org/CRAN/refmans/meta/html/meta-package.html) describe REML and alternative tau² estimators and version-specific defaults. The term "RevMan" alone does not prove which estimator/version the authors selected.

**Gate update:** AKI prior `MISMATCH_UNRESOLVED` is **numerically reconciled under an independently computed REML model**, but endpoint definitions, data extraction population, second-extractor check, method identity/version and actual Kit/browser validation are **still unresolved**. Overall W07 status remains **PARTIAL**, **not Kit-REPRODUCED**, not fully validated and not a publication-error determination. The safe next check is independent ascertainment of authors' exact model settings plus original-trial safety denominators and endpoint semantics, particularly FINEARTS AKI/UTI. A GitHub-connected read found no benchmark-specific validated config in `configs/`; the generic `example_finerenone_ckd.json` is ineligible. No CI/Kit run was claimed or triggered, no other lane's files touched, no main merge.
