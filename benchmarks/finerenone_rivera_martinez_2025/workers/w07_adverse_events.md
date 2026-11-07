# W07 — Serious adverse events, acute kidney injury, urinary infection, pneumonia

**Checkpoint 2026-11-07 (UTC); status: PARTIAL, not independently validated or Kit-reproduced.** Working branch: `benchmark/finerenone-open-meta-2026`. Scope restricted to Worker 7 safety endpoints. This note contains only public numerical evidence, calculation methods and open questions. Do not merge to main. No outreach.

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
