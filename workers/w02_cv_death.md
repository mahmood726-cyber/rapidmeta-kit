# Worker 02 — cardiovascular death (CV mortality) HR reconstruction
Date: 2026-11-07 UTC. Branch: `benchmark/finerenone-open-meta-2026`. Project: Rivera-Martinez et al., `10.1007/s10557-024-07666-x`. Status: **PARTIAL / MISMATCH_UNRESOLVED**. No emails. This is the only Worker 02 GitHub path.

## Prespecified estimand and rights
Death from any cardiovascular cause (each RCT's time-to-event component), finerenone versus placebo; three distinct trials, N=19,027, generic inverse-variance random-effects log hazard ratio, two-sided 95% normal CI. NOT the CV composite or total/recurrent HF events. Search frozen at 2024-09-01. Primary trials: FIDELIO-DKD `NCT02540993` / `10.1056/NEJMoa2025845`; FIGARO-DKD `NCT02545049` / `10.1056/NEJMoa2110956`; FINEARTS-HF `NCT04435626` / `10.1056/NEJMoa2407107`.

The benchmark publisher page is openly readable but displays **CC BY-NC-ND 4.0**, so do not redistribute or adapt its figure or article text. This note records numerical facts, methods, links and original computations only. Primary source confirmation relies on publicly displayed original-article abstract, FDA prescribing-information tables and independent government HTA; NEJM full texts are not mined. No JAMA Network sources used.

## Source-level extraction: one row per trial
| Trial/registry | Original paper DOI | CV deaths finerenone/placebo (N randomized) | Source HR (95% CI) | log(HR) | SE from displayed CI | Provenance and endpoint |
|---|---|---|---|---:|---:|---|
| FIDELIO-DKD, NCT02540993 | 10.1056/NEJMoa2025845 | 128/150 (2833/2841) | 0.86 (0.68, 1.08) | -0.15082289 | 0.11801620 | FDA 2021 initial label, page 9, Table 4, CV-death component; time-to-first-event Cox analysis |
| FIGARO-DKD, NCT02545049 | 10.1056/NEJMoa2110956 | 194/214 (3686/3666) | 0.90 (0.74, 1.09) | -0.10536052 | 0.09879663 | 2021 original trial value reproduced in Canadian public HTA `SR0737r`, CV-death component; differs in CI from later FDA label |
| FINEARTS-HF, NCT04435626 | 10.1056/NEJMoa2407107 | 242/260 (3003/2998) | 0.93 (0.78, 1.11) | -0.07257069 | 0.09000545 | NEJM original article public abstract, published 2024-09-01; exact event counts independently corroborated by FDA 2025 label p.16, Table 6; CV death component, NOT composite RR |

Primary provenance links:
- FIDELIO-DKD FDA 2021 label, PDF p.9 (zero-based screenshot index 8): https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/215341s000lbl.pdf
- FIGARO-DKD Canadian HTA (source table shows 194/214, HR 0.90 [0.74,1.09]): https://www.canjhealthtechnol.ca/index.php/cjht/article/download/SR0737r/1387?inline=1
- FIGARO-DKD FDA 2025 later label Table 5, p.12 (zero-based 11), independently shows **0.90 [0.73,1.08]** rather than the original 0.90 [0.74,1.09]. Version/method difference unresolved; do **not** merge intervals or call a confirmed error: https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/215341s009lbl.pdf
- FINEARTS-HF primary original public abstract: https://www.nejm.org/doi/10.1056/NEJMoa2407107 (2024-09-01; 0.93 [0.78,1.11]); FDA 2025 label Table 6 p.16 (zero-based 15) has 242/260 and same HR/CI: https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/215341s009lbl.pdf
- Original trial registry records: https://clinicaltrials.gov/study/NCT02540993 ; https://clinicaltrials.gov/study/NCT02545049 ; https://clinicaltrials.gov/study/NCT04435626 . Registry pages opened but results JSON / version-history extraction was not accessible in this environment; do not treat registry as independently extracted results.
- Benchmark's main results and Fig. 2: https://link.springer.com/article/10.1007/s10557-024-07666-x and https://link.springer.com/article/10.1007/s10557-024-07666-x/figures/2 (published online 2025-01-04).
- Benchmark publicly reports CV-death HR 0.91 (0.82–1.01), I²=0. Its main-text p=0.08, while figure p=0.06; figure's pooled CI reads 0.91 [0.82,1.00], not the abstract's 1.01. Preserve both source representations.

## Numerical comparison, independently executed 2026-11-07
Algorithm: `y_i=ln(HR_i)`; `se_i=[ln(U_i)-ln(L_i)]/(2*1.96)` from displayed two-decimal trial CIs; fixed weights `w_i=1/se_i²`; `Q=sum(w_i*(y_i-ybar)²)`; DerSimonian–Laird `tau²=max(0,(Q-(k-1))/(sum(w)-sum(w²)/sum(w)))`; random weights `1/(se²+tau²)`; normal CI `exp(ybar ± 1.96/sqrt(sum(weights)))`; I² truncated at 0%. These input CIs are rounded, so underlying unpublished log-HR precisions remain uncertain. Independent Python/scipy result was cross-checked by a separate Python standard-library implementation (NormalDist) and returned exactly the numbers below.

**Using primary-source trial HR/CI values (preselected replication input):**
- Pooled HR **0.90237183**, 95% CI **0.80547172–1.01092926** -> to 2 decimals **0.90 (0.81–1.01)**; Q=0.27905475, tau²=0, I²=0%, two-sided z p=0.07631948.
- Relative IV weights FIDELIO 24.119%, FIGARO 34.415%, FINEARTS 41.466%.
- Does **not** reproduce the benchmark 0.91 (0.82–1.01) at two-decimal precision. NOT a confirmed publication error: could reflect undocumented input version, underlying HR precision, RevMan CI implementation or model settings.

**Exact logHR/SE printed by the benchmark's Figure 2 (diagnostic *figure-only replay*, NOT independently extracted original-trial inputs):**
- FIDELIO: logHR -0.1508, SE 0.1180; FIGARO: -0.1054, 0.0988; FINEARTS: -0.0726, **0.0710**.
- Replayed pooled HR **0.90783844**, 95% CI **0.82018661–1.00485747** -> **0.91 (0.82–1.00)**; Q=0.33317009, tau²=0, I²=0%, z p=0.06197710. Weights: 19.273%, 27.492%, **53.235%**.
- This replay explains the forest plot's rounded `0.91 [0.82,1.00]` and p~0.06, but is *circular verification of the figure's numbers*, not original-trial replication.
- **Critical source-identity discrepancy:** FINEARTS Fig. 2 records HR 0.93 with apparent CI **0.81–1.07** (logHR -0.0726, SE **0.0710**), whereas the contemporaneous original trial and FDA label give HR **0.93 (0.78–1.11)**, SE reconstructed **0.09000545**. This reduces its apparent variance and elevates the benchmark figure weight from expected ~41.5% to ~53.2%. No alternative FINEARTS estimand explaining this has yet been verified.
- Replacing only FINEARTS' figure SE with the original-trial CI-derived SE, retaining figure logHRs, gives HR ~0.90235, CI ~0.80545–1.01090, p~0.07625.

## False-positive and endpoint safeguards
1. Do **not** use the kit's `configs/example_finerenone_ckd.json`: its composite events `367/420, 458/519, 624/719` and published composite HR/rate ratios do not represent CV death. HR cannot be recomputed from crude event-count RR.
2. Keep FINEARTS original CV-death HR separate from the study's total HF events plus CV-death rate ratio; secondary endpoints, population and statistical model differ.
3. Explicitly preserve version-specific FIGARO CI difference: trial-era `0.74–1.09` versus later FDA 2025 `0.73–1.08`. Change in label does not prove primary value erroneous.
4. Underlying exact trial logHR and logSE were not obtained, nor was a second extractor available. Two-decimal CI inversion is approximate. Treat figure error as **SOURCE_DISCREPANCY_UNRESOLVED**, not a confirmed scientific error or changed conclusion.
5. The post-2024 FDA FINEARTS label is used only as corroboration of originally published trial results, NOT as a post-cutoff trial added to the frozen three-study benchmark. No updated analysis has begun.

## Kit / independent oracle execution gate
The repo's `clone.py` code and README show that `publishedHR/hrLCI/hrUCI` are accepted as trial fields, but the default `allOutcomes` is **binary** and the dashboard's HR-specific generic inverse-variance path was not separately verified. The only existing project Drive checkpoint reports a successful **example smoke build** (with a composite input), not CV-death reproduction. In this worker run no outcome-specific RapidMeta dashboard was executed: checkout by `git` in this isolated runtime failed DNS resolution for github.com, and the full template/assets were not present. Thus **Kit validation remains NOT_DONE**, not PASS. This lane has only the independent computational oracle and figure diagnostics. A fully validated CV-death config must use compatible HR data without fictional 2×2 events; its browser output must be independently checked before comparing to the target.

## Required next actions / abstentions
- Read second independent extraction of the 3 original trial HRs, adjudicate FIGARO source-version difference, check FINEARTS forest input and whether any alternative originally available analysis yields SE 0.0710.
- Reconstruct the documented RevMan version, tau estimator, CI variant and unrounded inputs; compare against the published abstract, Figure 2 and main text separately.
- Execute the actual RapidMeta Kit's outcome-specific HR representation and compare output to independent R or validated Python oracle; DO NOT mix with an RR input.
- Do not edit main, merge, email anyone, or claim a full reproduction until both correct endpoint and numerical gate pass. Status remains **PARTIAL / MISMATCH_UNRESOLVED / NOT_ENOUGH_INFO**.

## Worker 02 recheck — 2026-11-07 13:14 UTC (Chat-only sources and numerical JS oracle)

Re-read frozen PROTOCOL.md and the latest worker checkpoint before this update. No Kit build, R/metafor execution, updated analysis, author contact or main-branch modification occurred. The following is a new *sensitivity and false-positive boundary check*, not a claim that the paper contains a proved error.

### Source-specific re-verification
- FIDELIO-DKD (`NCT02540993`, `10.1056/NEJMoa2025845`): FDA 2021 prescribing information p.9, Table 4, shows CV-death first-event component 128/2833 versus 150/2841; Cox HR **0.86 [0.68,1.08]**. Public PDF: https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/215341s000lbl.pdf
- FIGARO-DKD (`NCT02545049`, `10.1056/NEJMoa2110956`): the trial-era Canadian HTA source preserved in this worker record reports CV-death HR **0.90 [0.74,1.09]**, 194/3686 versus 214/3666; a later FDA July 2025 prescribing-information Table 5, p.12, independently shows **0.90 [0.73,1.08]**. The trial-era source and its exact version still require a second extractor; do not silently substitute the 2025 label for the original. FDA: https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/215341s009lbl.pdf
- FINEARTS-HF (`NCT04435626`, `10.1056/NEJMoa2407107`): FDA July 2025 prescribing-information Table 6, p.16, CV-death time-to-event component **242/3003 versus 260/2998, HR 0.93 [0.78,1.11]**, explicitly distinguished from composite/recurrent HF event **RR 0.84**. Public ACC original-trial synopsis repeats CV-death **0.93 [0.78,1.11]**; https://www.acc.org/latest-in-cardiology/clinical-trials/2024/08/29/20/16/finearts-hf ; FDA PDF as above. These sources are independent of the benchmark figure, but do not replace second-person source verification.
- Independently re-inspected the original benchmark Figure 2 (primary publisher figure URL: https://link.springer.com/article/10.1007/s10557-024-07666-x/figures/2). The FINEARTS row directly displays **log HR -0.0726, SE(logHR) 0.0710, HR 0.93 [0.81,1.07]**, weight **53.2%**. Its total is **0.91 [0.82,1.00], p=0.06**. Abstract and main text instead state **0.91 [0.82,1.01]**, and main text p=0.08. The source version/date and exact model remain unadjudicated.

### NEW independent rounding-bound test (plain JS IEEE-754 arithmetic; no local files/shell)
For the FDA/HTA trial HRs, `ln(HR)` is `[-0.15082289,-0.10536052,-0.07257069]`; corresponding `SE=[ln(U)-ln(L)]/3.92` is `[0.1180162046,0.0987966299,0.0900054527]`. DL random-effects has Q=0.279054745, tau²=0, I²=0 and pooled **HR 0.902371834 [0.805471717,1.010929259]**; normalized IV weights **[24.119%,34.415%,41.466%]**. This is a direct cross-check of the previously documented independent oracle.

When the FIGARO 2025 FDA CI `0.73–1.08` is used *instead* of trial-era `0.74–1.09` as an explicit nonbenchmark sensitivity, its SE is **0.0999162719** and pooled DL HR **0.902390190 [0.805135248,1.011392878]**, I²=0. Consequently FIGARO CI-version drift alone cannot explain the figure's lower CI 0.82 or its higher FINEARTS weight.

For FINEARTS original **rounded** 0.78–1.11, if the underlying CI endpoints round to hundredths in conventional nearest rounding, the broad possible SE interval is **[ln(1.105/0.785)/3.92, ln(1.115/0.775)/3.92] = [0.087223698,0.092792514]**. The figure's **0.0710 lies outside that whole range**. Its value would imply approximately **0.8092–1.0689** around HR 0.93, agreeing with the figure's displayed 0.81–1.07 instead. Thus **rounding of the original displayed CI cannot by itself produce the figure SE**; an alternate result version, estimand, computation or source error remains possible.

To avoid claiming the rounded pooled point mismatch is necessarily real, an independent `2^9=512` corner stress test varied each displayed HR and 95% CI bound independently within **±0.004999** of its printed value, re-estimating ordinary inverse-variance normal-CI DL (tau²=0 in tested cases). Across these deliberately overinclusive corner combinations, pooled HR spanned **0.89610–0.90868**, and its lower 95% bound **0.79826–0.81272**. **92/512** corners rounded the pooled *point* to 0.91, so 0.90-versus-0.91 alone is **not strong discrepancy evidence**. But none reached a lower CI of 0.815 required to round to **0.82**; this sensitivity supports investigating the precision change. These are corner checks, **not an exhaustive optimization of every possible continuous unrounded source value**, and do not rule out another method or trial-estimand variant.

**Acceptance status remains PARTIAL / MISMATCH_UNRESOLVED / NOT_ENOUGH_INFO.** Primary endpoint identity and original input version need adjudication, and outcome-specific RapidMeta HR dashboard has **not** been executed. Current repository `.github/workflows/ci.yml` offers workflow_dispatch and a composite *example* smoke build, but no independently demonstrated CV-death benchmark job; no dispatch action was available through the connected Chat GitHub tools. Do not treat generic CI or the above numerical oracle as a Kit run. No JAMA materials, no outreach, no merge.
