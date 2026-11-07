# Worker 3 — heart-failure hospitalisation (HFH), finerenone benchmark

**Checkpoint: 7 November 2026 | Status: PARTIAL (published Fig. 2 arithmetic reconstructed; endpoint-compatible HR reproduction / RapidMeta execution not yet verified).**
Scope: Rivera-Martinez et al., *Cardiovascular Drugs and Therapy*, DOI [10.1007/s10557-024-07666-x](https://doi.org/10.1007/s10557-024-07666-x); original search cutoff 1 September 2024. Exclusive worker-3 lane. No author contact.

## Source and estimand provenance

The benchmark authors say that HF hospitalisation uses generic inverse-variance random-effects meta-analysis of **log hazard ratios**. Their [published Fig. 2](https://media.springernature.com/lw1200/springer-static/image/art%3A10.1007%2Fs10557-024-07666-x/MediaObjects/10557_2024_7666_Fig2_HTML.png) supplies the *actual inputs* shown below; this is not the Kit's example composite dataset. DOI and NCT identifiers identify three distinct trial families.

| Trial / registry / trial publication | Published Fig. 2 input labelled logHR | Fig. 2 SE(logHR) | Fig. 2 HR [95% CI] | Source / intended endpoint |
| --- | ---: | ---: | --- | --- |
| FIDELIO-DKD / [NCT02540993](https://clinicaltrials.gov/study/NCT02540993) / [10.1056/NEJMoa2025845](https://doi.org/10.1056/NEJMoa2025845) | -0.1508 | 0.1180 | 0.86 [0.68, 1.08] | First HF hospitalisation, original trial comparison supported by [clinical evidence summary](https://dig.pharmacy.uic.edu/faqs/2021-2/september-2021-faqs/what-evidence-is-available-for-use-of-the-newest-mineralocorticoid-receptor-antagonist-finerenone-in-diabetic-kidney-disease/). |
| FIGARO-DKD / [NCT02545049](https://clinicaltrials.gov/study/NCT02545049) / [10.1056/NEJMoa2110956](https://doi.org/10.1056/NEJMoa2110956) | -0.3425 | 0.1210 | 0.71 [0.56, 0.90] | First HF hospitalisation HR from [open FIGARO secondary analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC8812430/). Same analysis gives **total** (first and recurrent) HF hospitalisations as *rate ratio* 0.70 [0.52, 0.94], a distinct estimand. |
| FINEARTS-HF / [NCT04435626](https://clinicaltrials.gov/study/NCT04435626) / [10.1056/NEJMoa2407107](https://doi.org/10.1056/NEJMoa2407107) | -0.1985 | 0.0716 | **0.82 [0.71, 0.94]**, labelled HR in benchmark | **Important unresolved estimand gate:** the original trial gives this exact 0.82 [0.71, 0.94] as a *rate ratio* for **842 versus 1,024 total worsening HF events** (first/recurrent, hospitalisations and urgent HF visits), not a first-HFH HR. See [FINEARTS trial summary](https://www.acc.org/latest-in-cardiology/clinical-trials/2024/08/29/20/16/finearts-hf) and [trial abstract](https://www.nejm.org/doi/10.1056/NEJMoa2407107). Do **not** treat 842/1,024 as unique persons or derive 2×2 risks from them. |

Cross-check from the open FINE-HEART participant-level pooled paper [10.1038/s41591-024-03264-4](https://doi.org/10.1038/s41591-024-03264-4), **Extended Data Fig. 4**, shows *first HF hospitalisation* FIDELIO 0.85 [0.68, 1.07] (138 vs 162 first-event participants), FIGARO 0.71 [0.56, 0.90] (117 vs 163), FINEARTS 0.86 [0.76, 0.97] (450 vs 514); its Methods explicitly use time-to-first event Cox regression. The FINE-HEART analysis has different harmonisation/analysis populations and must not be silently substituted for the benchmark; it is an independent endpoint-identity comparator, not proof of error.

The meta-analysis abstract and Fig. 2 call the pooled HFH effect an **HR**, whereas one main-text Results sentence calls the same 0.80 an **RR**. The abstract, Methods, source forest and statistical type support a likely reporting-label inconsistency; **not a confirmed error** in isolation. More importantly, the FINEARTS numeric input appears to correspond to a recurrent-event **rate ratio** rather than first hospitalisation HR. Verify the figure's extraction source and trial/supplementary endpoint definitions with a second extractor before adjudication.

## Independent numerical oracle (executed, not RapidMeta output)

Input from **Fig. 2 printed log estimates and SEs**, not counts. Python 3 + NumPy/SciPy independent generic-inverse-variance calculation:
```python
import numpy as np
from scipy.stats import chi2, norm
yi = np.array([-0.1508, -0.3425, -0.1985])      # Fig. 2 logHR labels
sei = np.array([0.1180, 0.1210, 0.0716])        # Fig. 2 SE(logHR) labels
wi = 1 / sei**2
mu = np.sum(wi*yi)/np.sum(wi)
Q = np.sum(wi*(yi-mu)**2)
C = np.sum(wi)-np.sum(wi**2)/np.sum(wi)
tau2_DL = max(0., (Q-2)/C)                       # k=3
wRE = 1 / (sei**2+tau2_DL)
muRE = np.sum(wRE*yi)/np.sum(wRE)
seRE = np.sqrt(1/np.sum(wRE))
print(np.exp(muRE), np.exp(muRE-1.96*seRE), np.exp(muRE+1.96*seRE))
```
**Executed result:** HR-labelled mathematical pooling **0.8044287461 [0.7227586069, 0.8953274322]**, Q **1.4571334052** (df=2; heterogeneity p **0.4826002042**), I² **0%**, DL tau² **0**, weight fractions **0.21426677 / 0.20377368 / 0.58195954**, |z| **3.98423682**, two-sided p **0.0000676973**. Rounded to two decimals: **0.80 [0.72, 0.90]**, matching the meta-analysis's target **numerically**. The paper's figure reports I²=0%, heterogeneity p=0.48, and weight fractions 21.4% / 20.4% / 58.2%, consistent with this calculation.

Independent false-positive check: using only the *rounded plotted HRs and 95% CIs* with SE=(ln upper-ln lower)/3.92 yields **0.8044617502 [0.7227905620, 0.8953613141]**, Q **1.4564362144**, again 0.80 [0.72,0.90]. This independently verifies robustness to printed rounding, not endpoint validity.

**Recurrent-to-first-event substitution sensitivity, separately labelled (not published benchmark):** using the first-event FINE-HEART per-trial HRs 0.85 [0.68,1.07], 0.71 [0.56,0.90], 0.86 [0.76,0.97] under inverse-variance DL yields **0.8300569536 [0.7516072743, 0.9166948881]**, Q=2.03228488, I²=1.59%, tau²=0.00015409. This is a different estimation source/analysis and does not by itself demonstrate what the original review should have reported. It illustrates why arithmetic matching and clinical outcome identity are separate acceptance gates.

## RapidMeta Kit gate

Read Kit's [README](https://github.com/mahmood726-cyber/rapidmeta-kit), [clone.py](https://github.com/mahmood726-cyber/rapidmeta-kit/blob/benchmark/finerenone-open-meta-2026/clone.py), and generic [example_finerenone_ckd.json](https://github.com/mahmood726-cyber/rapidmeta-kit/blob/benchmark/finerenone-open-meta-2026/configs/example_finerenone_ckd.json). Its example outcome is a **different cardiovascular composite**; those example event counts are **NOT** HFH inputs. `clone.py` can stamp trial `publishedHR`, `hrLCI`, `hrUCI`, and per-outcome `effect`, `se`, `estimandType` into the browser dashboard. However the actual browser model and its log-HR inverse-variance pooling have not been executed or checked against the independent oracle in this worker run. **Kit result = NOT_RUN / NOT_ENOUGH_INFO**, not a validated reproduction. A validated outcome-specific config must avoid fake patient counts, guarantee HR-vs-rate-ratio distinction, and be independently smoke-tested before reporting a Kit match.

## Verification gates and status

- **PASS, restricted:** 3-trial **figure-value arithmetic** reproduces the published rounded pooled estimate and I² with independent code.
- **FAIL TO ESTABLISH:** endpoint-compatible *three first-HFH HRs* for the published input; FINEARTS forest input exactly matches a **recurrent worsening-HF rate ratio**. Alternative explanations include author sourcing from a different trial analysis, change in endpoint definitions, or figure labelling/transcription. Requires second extractor and original full-text/supplement verification with lawful access.
- **NOT_ENOUGH_INFO:** whether Kit's browser analysis reproduces this exact HR model, and original RevMan settings/precision beyond the printed forest. Unable to run full Kit because checkout and browser engine were unavailable in this execution environment; no claims about Kit were made.
- **No RR/HR error adjudicated; no emails, author contact, changes to other workers, controller status files, or public main merge.**
- Controller handoff: request source/endpoint adjudication before upgrading status to REPRODUCED; pass these exact numeric inputs and sensitivity to worker 8 for independent Kit/oracle parity.

Caveat: the independently reproduced **plotted numbers** alone cannot validate combining a first-event HR with a recurrent-event rate ratio. The strict scientific reproducibility gate remains unresolved.
