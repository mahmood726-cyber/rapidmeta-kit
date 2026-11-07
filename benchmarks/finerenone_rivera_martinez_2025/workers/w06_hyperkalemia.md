# W06 — Hyperkalemia endpoint reproduction (Rivera-Martinez et al.)
**Checkpoint 2026-11-07 | Scope: only NCT02540993 / NCT02545049 / NCT04435626 | Status: PARTIAL (numerical estimates reproduced; independent primary-trial endpoint validation still pending).**

## Frozen source and rights
- Benchmark: Rivera-Martinez et al., *Cardiovascular Drugs and Therapy*, published online 2025-01-04, DOI [10.1007/s10557-024-07666-x](https://doi.org/10.1007/s10557-024-07666-x). Open publisher [HTML](https://link.springer.com/article/10.1007/s10557-024-07666-x), [PDF](https://link.springer.com/content/pdf/10.1007/s10557-024-07666-x.pdf), **Table 4 (p.176), Figure 3 (p.177)**. Article states CC BY-NC-ND 4.0. This checkpoint reports factual event numbers and original analytical calculations, not reproduced figure/table artworks or adapted content.
- Prespecified pooled trial set: FIDELIO-DKD [NCT02540993](https://clinicaltrials.gov/study/NCT02540993), [original DOI 10.1056/NEJMoa2025845](https://doi.org/10.1056/NEJMoa2025845); FIGARO-DKD [NCT02545049](https://clinicaltrials.gov/study/NCT02545049), [10.1056/NEJMoa2110956](https://doi.org/10.1056/NEJMoa2110956); FINEARTS-HF [NCT04435626](https://clinicaltrials.gov/study/NCT04435626), [10.1056/NEJMoa2407107](https://doi.org/10.1056/NEJMoa2407107). Do not substitute FIDELITY pooled trial subgroup data for one trial or double-count trials.
- Benchmark method: dichotomous log RR random-effects pooling of **three trial-specific 2×2 tables**. Reported two outcomes: regimen-related hyperkalemia RR **2.31 (1.98–2.69)**, I²=0, tau²=0.0018; investigator-reported hyperkalemia RR **2.09 (1.90–2.30)**, I²=0, tau²=0. Neither is potassium >5.5 or >6 mmol/L, discontinuation, or generic severe hyperkalemia.

## Trial-level extraction — exactly the benchmark Table 4 / Figure 3 populations
Values are **finerenone events/total | placebo events/total**, NOT derived from the review's 19,027 randomized aggregate or the kit's generic composite example.

| Trial, registry | Investigator-reported hyperkalemia | Hyperkalemia labelled related to trial regimen | Source |
|---|---|---|---|
| FIDELIO-DKD, NCT02540993 | 516/2833 \| 255/2841 | 333/2833 \| 135/2841 | Benchmark Table 4, Figure 3 |
| FIGARO-DKD, NCT02545049 | 396/3686 \| 193/3666 | 240/3686 \| 114/3666 | Benchmark Table 4, Figure 3 |
| FINEARTS-HF, NCT04435626 | 289/2993 \| 125/2993 | 16/2993 \| 6/2993 | Benchmark Table 4, Figure 3 |

**Ascertainment / denominator warnings.** Published review Table 4 uses FIDELIO 2833/2841 and FIGARO 3686/3666 (their analysis-set/randomization denominators), whereas independent trial safety material identifies FIDELIO **2827/2831** [open FIDELIO hyperkalemia analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC8763180/) and FIGARO **3683/3658** (original FIGARO safety table; *provisional pending direct rights-cleared table verification*). FINEARTS uses 2993/2993 safety-exposed rather than randomized 3003/2998, independently corroborated by [Bayer FINEARTS safety report](https://www.bayer.com/en-us/united-states/news-and-stories/2025/kerendiar-finerenone-in-patients-with-heart-failure). This denominator contrast **must not** be erased when matching rounded RRs.

Most importantly, FINEARTS **16/2993 versus 6/2993 is specifically hospitalization due to hyperkalemia** in the separate publicly accessible sponsor report, whereas FIDELIO **333/135** and FIGARO **240/114** are presented as drug-related hyperkalemia AEs in trial materials. This raises **endpoint comparability / clinical-severity** questions for the first meta-analysis, not a confirmed paper error: confirm directly against contemporaneous FINEARTS trial safety definitions and the review's source mappings. Conversely, FINEARTS **289/125** are investigator-reported AEs, as in the sponsor report. Avoid treating the 16/6 hospitalizations as all hyperkalemia events.

Separately, FIDELIO central laboratory K+ >5.5 mmol/L (597/2785 vs 256/2775) and K+ >6 mmol/L (126/2802 vs 38/2796) in [PMID 34732509](https://pubmed.ncbi.nlm.nih.gov/34732509/) are **distinct** from investigator-reported AEs (516/255), and must never be substituted. Figures/grades, safety-exposed participants, and grade thresholds should be recorded separately.

## Independent numerical oracle (computed 2026-11-07)
For trial i, define y_i=log((a_i/n1_i)/(c_i/n0_i)), v_i=1/a_i - 1/n1_i + 1/c_i - 1/n0_i, w_i=1/(v_i+tau²). Use restricted maximum likelihood (REML), constrained tau²≥0; find positive root of
`sum(w_i²(y_i-mu)²) - sum(w_i) + sum(w_i²)/sum(w_i)=0` with `mu=sum(w_i*y_i)/sum(w_i)`, else tau²=0. Pooled RR=`exp(mu)`; normal 95% CI=`exp(mu +/- 1.96/sqrt(sum(w_i)))`. Cochran Q and I² use standard inverse-variance fixed-effect weights, truncated I²≥0. Independent implementation: Python 3, NumPy, SciPy Brent root solver. **This is an independent mathematical reconstruction, not a RapidMeta browser/Kit run or a second extraction.**

| Endpoint | Per-trial RR, same order | Q (df=2) / I² | Independent REML tau² | RR, unrounded (95% CI) | 2-decimal reproduction |
|---|---|---|---|---|---|
| Regimen-labelled | 2.473632; 2.093840; 2.666667 | 1.351301 / 0% | **0.0017559316** | **2.305049 (1.976315–2.688464)**, z=10.6377 | **2.31 (1.98–2.69), matches** |
| Investigator-reported | 2.029244; 2.040680; 2.312000 | 1.192539 / 0% | **0** | **2.091455 (1.902044–2.299729)**, z=15.2342 | **2.09 (1.90–2.30), matches** |

Positive controls: each computed trial RR and CI at two decimals matches published Figure 3; REML tau² rounds to 0.0018 for the first endpoint, and zero for the second; overall z agrees with Figure 3 (10.64, 15.23). **Negative/model check:** DerSimonian–Laird gives tau²=0 for the first endpoint because Q<2 and yields **2.306973 (1.999758–2.661384)**, rounding **2.31 (2.00–2.66)**, **not** the published interval. The correct two-decimal fit is therefore method-specific; generic random-effects/DL matching only the point estimate is insufficient.

### Sensitivity — trial safety-exposed rather than benchmark denominators
A deliberately separate calculation (provisional FIGARO safety N values) uses FIDELIO 2827/2831, FIGARO 3683/3658, FINEARTS 2993/2993, with the *same events*. Independent REML gives:
- Regimen-labelled: RR **2.301945 (1.973712–2.684765)**; tau²=0.00175257.
- Investigator-reported: RR **2.089166 (1.899981–2.297189)**; tau²=0.
**Do not** relabel this as the published benchmark or as a confirmed corrected estimate until primary-trial safety population verification and endpoint matching are complete.

## Reproducibility / acceptance gate
- Numeric match: **YES, for the exact Table 4/Figure 3 three-trial data under logRR REML-normal pooling.**
- Outcome coherence and source traceability: **PARTIAL**; secondary verification corroborates FIDELIO 516/255 and FINEARTS 289/125, 16/6 but primary Figure 3 traces for all inputs need independent second extractor and direct original safety source check. The 16/6 FINEARTS endpoint likely differs materially in severity from the other two trial labels.
- RapidMeta Kit run: **NOT RUN.** Do not use `configs/example_finerenone_ckd.json`, which is a *different composite endpoint*. An isolated potassium-specific config and browser run with matched REML semantics and independent JS/R comparison remain necessary before reporting Kit reproduction.
- Updated search or revised synthesis: **NOT STARTED**; must be separately labelled after the outcome/source acceptance gate. No authors contacted. No public main-branch merge.

## Required controller/second-extractor follow-up
1. Independently verify all 24 arm-level data fields against original trial safety reports or ClinicalTrials.gov; stamp source version, page/table, actual treated denominator and ascertainment/coding for each trial.
2. Specifically resolve whether FINEARTS 16/6 represents **hospitalization** versus treatment-attributed hyperkalemia, while 333/135 and 240/114 represent attribution. Record severity and attribution as separate axes, and abstain on a clinically harmonized pooled RR until resolved.
3. Establish whether the review's original method actually used REML (matching its printed tau² and z) rather than assume the default for all endpoints. Retain both published-data reproduction and safety-denominator sensitivity; do not call difference an error without matched models.
4. Build an **outcome-specific** RapidMeta config for each of the two definitions and test its exact RR method and heterogeneity estimator against this oracle, recording run output and logs. No generic composite reuse.
5. Set status `PARTIAL` until independent extraction and Kit execution; separately perform updated analysis only after signoff.
