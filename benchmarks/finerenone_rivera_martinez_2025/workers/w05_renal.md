# Worker 05 — renal failure (FIDELIO-DKD / FIGARO-DKD / FINEARTS-HF)

**Checkpoint:** 2026-11-07, preliminary independent extraction and numerical diagnostic.
**Status:** **PARTIAL / NOT_ENOUGH_INFO for full 3-trial benchmark reproduction**. No renal-specific RapidMeta Kit configuration or benchmark run has yet been accepted. This document is confined to worker 05's outcome; it makes no claim of a confirmed publication error.

## Frozen target and rights

Rivera-Martinez et al., *Cardiovascular Drugs and Therapy*, online 2025-01-04, DOI **10.1007/s10557-024-07666-x**, https://link.springer.com/article/10.1007/s10557-024-07666-x; FIDELIO-DKD **NCT02540993**, FIGARO-DKD **NCT02545049**, FINEARTS-HF **NCT04435626**, 19,027 included. The open article is CC BY-NC-ND 4.0; use sourced numerical facts only, no adapted figures or redistributed content. Its Methods specifies *dichotomous random-effects RR for renal failure*, not HR. Published **main text/Table 3 target**: RR **1.05 (0.65–1.68), I²=83%, p=0.80**. Independently inspected **Fig. 2 forest plot** instead shows RR **1.06 (0.61–1.82), I²=83%, p=0.84, tau²=0.1995**. Distinguish these two internal displays until source input and computations are independently established.

## DOI / NCT-level extraction

| Trial | Provenance | Renal endpoint | Finerenone events / n | Placebo events / n | RR from counts | Assessment |
| --- | --- | --- | --- | --- | --- | --- |
| FIDELIO-DKD / NCT02540993 | 10.1056/NEJMoa2025845; historical SmPC table 4 at https://patient-info.co.uk/kerendia-10-mg-film-coated-tablets-86459/summary-of-medicine-characteristics | Kidney failure separately from eGFR/renal-death composite: dialysis, transplantation, or sustained eGFR <15 mL/min/1.73m² | **208/2833** | **235/2841** | **0.887606** (Wald 95% CI 0.74199–1.06179) | Matches figure rounded RR 0.89 [0.74–1.06]. Check historical vs subsequently revised analysis population. |
| FIGARO-DKD / NCT02545049 | 10.1056/NEJMoa2110956; UK SmPC table 5 https://www.medicines.org.uk/emc/product/102090/smpc | Kidney failure as separate component; not 40%-decline/renal-death composite | **46/3674** | **62/3654** | **0.737897** (Wald 95% CI 0.50530–1.07756) | Matches figure rounded 0.74 [0.51–1.08], **but** current SmPC analysis population n=7,328 differs from study’s reported included 7,352 (3686/3666). With original denominators, RR=0.737910, same two-decimal rounding. Resolve original-version denominator before benchmark acceptance. |
| FINEARTS-HF / NCT04435626 | 10.1056/NEJMoa2407107; figure 2 in benchmark DOI above; prespecified kidney assessment 10.1016/j.jacc.2024.10.091 (published after 2024-09-01 cutoff) | **UNCERTAIN**: figure calls this “renal failure” and gives RR **1.93 [1.22–3.03]**. Unable to independently verify event numerators, denominators and matching endpoint definition. | **NOT_ENOUGH_INFO** | **NOT_ENOUGH_INFO** | Figure only: RR 1.93 [1.22–3.03] | Do **not** substitute later kidney-composite counts or adverse-event kidney injury. |
 
Note: the current UK SmPC also shows a **revised FIDELIO** analysis population (205/2824 vs 235/2838, RR 0.876665); this is **not** the historically aligned input. Both versions must remain explicitly version-labelled. The reported randomised/included sample sizes and analysis populations are not always the same.

### Negative controls: non-equivalent FINEARTS endpoints (NOT benchmark inputs)

The post-cutoff prespecified kidney analysis DOI **10.1016/j.jacc.2024.10.091** reports **75/3003 vs 55/2998** for a **composite** of >=50% eGFR decline or kidney failure (crude RR 1.36137); **41/3003 vs 31/2998** for >=57% decline composite (crude RR 1.32038); and **7/3003 vs 6/2998** for kidney failure requiring dialysis (crude RR 1.16472). None reproduces figure 2 FINEARTS RR 1.93. Since the kidney analysis postdates the cutoff and has a distinguishable estimand, it is for **endpoint-identity diagnosis only**, not a retrospective substitute benchmark dataset. Likewise AKI, dialysis, an eGFR composite, and adverse-event 'renal failure' must not be interchanged without source proof.

## Independent computation, forensics only — NOT the protocol's acceptance-gate replication

From Fig. 2 only, the **published rounded per-trial** RR / 95% CI are:

- FIDELIO: 0.89 [0.74, 1.06]; figure weight 37.1%
- FIGARO: 0.74 [0.51, 1.08]; figure weight 32.5%
- FINEARTS: 1.93 [1.22, 3.03]; figure weight 30.4%

Using `y=ln(RR)`, `SE=[ln(upper)-ln(lower)]/3.92`, an **independent Python/NumPy/SciPy** inverse-variance calculation on those rounded estimates gives:

- Fixed-effect Q = **11.526464** on 2 df; conventional I² = **82.6486%** (rounds to 83%, agreeing with figure).
- **DL** tau² = **0.131661**; pooled **1.051245 [0.666267, 1.658668]** (normal 95% CI), inverse-variance from already-rounded study ratios.
- **REML** tau² = **0.199092**; pooled **1.060171 [0.615780, 1.825265]**; weights **37.03%, 32.59%, 30.38%**. This numerically mirrors Fig. 2's tau² 0.1995 and RR 1.06 (0.61–1.82) within input rounding precision. This is a *forensic match from rounded forest ratios*, **not** independent reproduction from validated 2×2 outcome inputs and **not** proof of the original fitting algorithm.
- The main-text **1.05 (0.65–1.68)** is not exactly matched by this approximate DL implementation (**1.05 [0.67–1.66]**). Multiple possible explanations: different random-effects algorithms, different source counts, subgroup/analysis population, table/figure generation version, CI correction and rounding. It must not be labelled an established error.

Minimal independently runnable calculation (requires scipy and numpy; no Kit generic example):

```python
import numpy as np
from scipy.optimize import minimize_scalar
rr=np.array([.89,.74,1.93])
lo=np.array([.74,.51,1.22]); hi=np.array([1.06,1.08,3.03])
y=np.log(rr); v=((np.log(hi)-np.log(lo))/3.92)**2
w=1/v; fixed=(w@y)/sum(w); Q=sum(w*(y-fixed)**2)
C=sum(w)-sum(w*w)/sum(w)
tau_dl=max(0,(Q-2)/C)
def nll(t):
    wt=1/(v+t); m=(wt@y)/sum(wt)
    return .5*(sum(np.log(v+t))+np.log(sum(wt))+sum(wt*(y-m)**2))
tau_reml=minimize_scalar(nll,bounds=(0,2),method='bounded').x
for t in [tau_dl,tau_reml]:
    wt=1/(v+t); m=(wt@y)/sum(wt); s=np.sqrt(1/sum(wt))
    print(t,np.exp(m),np.exp(m-1.96*s),np.exp(m+1.96*s))
print('Q',Q,'I2',max(0,(Q-2)/Q)*100)
```

## Clinical/estimand compatibility gate

FIDELIO and FIGARO concern type-2 diabetes with CKD; FINEARTS concerns symptomatic HF with LVEF>=40%, generally less severe baseline kidney risk. Kidney **failure** is not the same as laboratory decline, post-treatment eGFR dip, AKI, dialysis-only, or investigator-reported adverse event. Compare kidney failure component definitions, ascertainment, follow-up time, ITT versus safety denominator, and blinding before pooling. With only 3 clinically heterogeneous studies, I² 83% strongly cautions against a single 'no renal effect' reading; the broad CI cannot establish equivalence or lack of harm.

## Acceptance gate, blockers and next steps

1. **NOT_ENOUGH_INFO:** Retrieve the **exact FINEARTS-HF 2×2 counts and matching “renal failure” endpoint** used in the 2025 review (authors' Table 3/figure source data/supplement or Sep 2024 original permissible trial tables/registry results), documenting extraction date, table/page and analysis population. Do not manufacture from 1.93 or adapt later kidney composite counts.
2. **PARTIAL:** Verify FIGARO original vs revised denominators, FIDELIO source version, and ensure treatment orientation. Second independent extraction still outstanding.
3. **NOT RUN:** Only after compatible 3-trial 2×2 inputs, create an outcome-specific verified RR config and run RapidMeta Kit; compare an independent statistical oracle and freeze exact model (MH vs inverse variance; DL vs REML; ordinary vs HKSJ CI). Do not change method post hoc to match.
4. **NO UPDATE ANALYSIS:** No separately revised/beyond-cutoff synthesis is permitted until this gate passes. No emails or public-main changes.

These are source-based methodological caveats and testable hypotheses, **not confirmed scientific errors**.

## 2026-11-07 next-run renal provenance gate: regulatory counterexamples

**Scope/status:** Public-source factual verification only, still **PARTIAL / NOT_ENOUGH_INFO**. The following is **2026 post-cutoff diagnostic evidence**, **not** a replacement for the 2024-09-01 frozen three-trial inputs. No outcome-specific RapidMeta run or validated second extraction.

**Versioned source:** UK electronic Medicines Compendium, Kerendia 20 mg SmPC, https://www.medicines.org.uk/emc/product/13438/smpc, displayed last update **2026-04-16**, sections 4.8 (worsening renal function) and 5.1 (Table 8). NCT04435626, primary trial DOI 10.1056/NEJMoa2407107. This public regulatory label is not the September 2024 trial manuscript; preserve its post-cutoff status and do not use as an exact original-input witness.

- **Investigator-/AE-type “renal failure”** under worsening renal function in FINEARTS-HF: **2.6% finerenone vs 1.6% placebo** (one-decimal published rates; *exact* 2×2 numerators and the matching adverse-event safety denominator not provided at that point). A **rate/proportion diagnostic only**, 2.6/1.6 = **1.625**. Allowing half a tenth percentage-point rounding per value gives approximate ratio range **[2.55/1.65, 2.65/1.55) = [1.5455, 1.7097)**. This is distinct from the benchmark forest **RR 1.93 [1.22, 3.03]**, but cannot prove an error because outcome coding, analysis population, dates and ascertainment may differ. **Not a valid fourth data source or a substitute FINEARTS row.**
- **Prespecified/adjudicated trial kidney composite (Table 8):** **75/3003** finerenone vs **55/2998** placebo, crude RR **1.3613659068**. Its individual components in the label are **sustained eGFR <15: 5/3003 vs 2/2998** (crude RR **2.4958374958**), **initiation of dialysis: 2/3003 vs 2/2998** (RR **0.9983349983**), **transplantation 0 vs 0**. The overall composite also incorporates a 50% sustained eGFR decline; **do not add component counts** (overlaps possible). These are distinct endpoints, not a count of original-review “renal failure”.
- Another 2025 open-access prespecified FINEARTS kidney analysis (DOI **10.1016/j.jacc.2024.10.091**, https://www.jacc.org/doi/10.1016/j.jacc.2024.10.091) reports **7 vs 6** developing kidney failure requiring dialysis, whereas the 2026 label Table 8 says initiation of dialysis **2 vs 2**. Differences may reflect definition, event ascertainment, analysis window or reporting version. **UNRESOLVED; do not infer a discrepancy from this contrast alone.**
- **Negative controls:** (1) regulatory MedDRA-type renal failure adverse event 2.6% vs 1.6% is **not** adjudicated kidney failure; (2) 75 vs 55 composite is **not** kidney failure alone; (3) five vs two sustained low-eGFR events are **not** the whole renal failure event pool; (4) 2 vs 2 dialysis initiations differ from later broad “requiring dialysis”; (5) a later safety label is **not** the pre-cutoff original dataset. Trial families remain FIDELIO NCT02540993, FIGARO NCT02545049, FINEARTS NCT04435626, not four independent studies.
- **Acceptance gate unchanged:** original FINEARTS matching renal-failure event counts/denominators **NOT_ENOUGH_INFO**, matching endpoint definition **NOT_ENOUGH_INFO**, original RevMan dichotomous model implementation **NOT_ENOUGH_INFO**, second extraction **NOT DONE**, renal-specific Kit config/CI execution **NOT RUN**. Figure-only REML replay remains 1.060171 [0.615781, 1.825265], I² 82.6486%, versus main-text target 1.05 [0.65, 1.68], I² 83%; arithmetic compatibility alone is insufficient for scientific reproduction.

**Source inspection stop point:** Public UK SmPC sections 4.8 and 5.1, original review HTML methods/results/figure; targeted open registry search did not establish exact pre-cutoff FINEARTS 2×2 for the forest “renal failure” row. **No endpoint was relabelled**. No JAMA material, author contact, main merge, or updated/revised analysis.
