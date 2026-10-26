# Synthesis | Finerenone HF human-extraction reference (26 October 2026)

**Research-stage provenance and reproducibility fixture; NOT a validated clinical synthesis.** This is a separately scoped cardiovascular-outcome pilot, not a replacement for the existing CKD/T2D cardiovascular-composite dashboard or the kidney-outcome Meta-Harness review.

## Human source and permissions

Dr Yousef Moradi supplied a seven-tab source-linked workbook, Finerenone_HF_Extraction_Record-3.xlsx, on 26 October 2026. He reports that he manually extracted the three trials and reproduced the statistics **outside** RapidMeta and Meta-Harness. This gives us a valuable independent human reference, but it does not automatically validate the software or the completeness of study discovery.

Original workbook SHA-256: 5cbc23255023bf293b0b9e5a604b026f7fa19464a4a2595e555d89ffb4538fc7. **The workbook itself is NOT in this public repository**, pending author permission for onward distribution and agreement on attribution. The public reference JSON contains published aggregate numbers and references, not the underlying unpublished charter extracts or original workbook.

Target published review: Rivera-Martinez et al., Cardiovascular Drugs and Therapy, DOI https://doi.org/10.1007/s10557-024-07666-x, Table 3 and Fig. 2 (“Hospitalization for HF,” journal p. 175). Primary sources:
- FIDELIO-DKD: https://doi.org/10.1056/NEJMoa2025845
- FIGARO-DKD: https://doi.org/10.1056/NEJMoa2110956
- FINEARTS-HF: https://doi.org/10.1056/NEJMoa2407107

## Endpoint and estimand comparison

| Trial | Published event counts: finerenone / placebo | Endpoint and measure |
| --- | --- | --- |
| FIDELIO-DKD | 139 / 162 participants with first event | First hospitalisation for HF; hazard ratio 0.86 (0.68–1.08) |
| FIGARO-DKD | 117 / 163 participants with first event | First hospitalisation for HF; hazard ratio 0.71 (0.56–0.90) |
| FINEARTS-HF | 842 / 1024 **total first and recurrent events** | Worsening HF including urgent visits; event rate ratio 0.82 (0.71–0.94) |

FINEARTS-HF enrolled patients with symptomatic HF with LVEF at least 40%, not the same CKD/T2D population. Its 842 and 1024 are **event totals, not numbers of participants with an event**. Its event-rate ratio must not be silently parsed as a time-to-first-event HR or as a binary relative risk. An I-squared estimate of 0% does not establish clinical comparability.

**Method clarification:** Rivera-Martinez explicitly describes a *random-effects generic inverse-variance* method for this outcome, and the forest plot shows between-study tau-squared of zero. The supplied workbook describes an independent *fixed-effect* numerical reconstruction and elsewhere implies fixed effect from I-squared zero. These are numerically close here because estimated tau-squared is zero, not because the methods are universally interchangeable. The source-linked, rounded-publication, DL reconstruction in replay.py yields **0.80446 (0.72279–0.89536)** versus the manuscript **0.80 (0.72–0.90)**. This is historical arithmetic replay only; the mixed effect measures and clinical populations prevent treating it as a verified homogeneous clinical result.

## Reproduce locally

Python 3.9 or later; no extra runtime dependencies:

    python research_pilots/finerenone_hf_2026_10_26/replay.py
    # Intentionally fails closed: INCOMPATIBLE_ESTIMANDS
    python research_pilots/finerenone_hf_2026_10_26/replay.py --paper-reconstruction
    python research_pilots/finerenone_hf_2026_10_26/replay.py --dkd-only
    python -m pytest tests/test_finerenone_hf_human_reference.py -q

The optional paper-reconstruction flag permits **only a clearly labelled numerical reconstruction of the historical reported forest plot**. The DKD-only numerical sensitivity uses two published first-event HRs and remains exploratory, not an endorsed clinical conclusion. The default operation deliberately refuses pooling all three effects. Ten unit tests cover provenance anchors, effect types, recurrent-event count units, numerical anchors, statistical-model label, mutation controls, CI validation and scientific independence status.

These tests do NOT run the browser statistical engine, independent version-pinned R/metafor/RevMan replication or full Meta-Harness prospective discovery. This is a source-grounded input-safety fixture, not a claimed PASS for independent programme benchmark B or cross-system reproducibility.

## Still open (do not substitute assumptions)

- Obtain exact source page/paragraph anchors for FIGARO and FINEARTS Clinical Endpoint Committee charters. The original workbook explicitly notes incomplete charter verification and inferred similarity of two DKD programmes; do not certify these passages without source checks.
- Request a prespecified clinical/estimand-harmonisation judgement and available FINEARTS first-hospitalisation-only HR, if an eligible estimate exists; do not silently pool unharmonised populations.
- Execute an independent, method-matched version-pinned R oracle separately; a Python reconstruction from rounded CIs is **not R parity**.
- For prospective evidence validation, conduct a fully documented search, eligibility assessment and separate independent blinded second adjudication. A single independent researcher’s extraction is not dual adjudication.
- Reconcile with the existing RapidMeta CKD example correction PR #2, without undoing its planned removal of FINEARTS from the CKD/T2D composite dashboard. Do not modify that live dashboard via this pilot.
- Obtain contributor consent, agreed attribution and redistribution terms **before** releasing the original workbook; secure it separately until then.

Programme: Synthesis — Evidence Integrity, Research and Education. [Code repositories](https://github.com/mahmood726-cyber); [related Synthesis journal](https://synthesis-medicine.org/index.php/journal). Conducted in a personal scholarly capacity; no NHS, university, journal-publisher, or regulator endorsement is implied.
