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


## Private-to-public workbook verification (added 26 October 2026)

This pilot now has an **executable local source bridge** that reads the original XLSX only on the user's computer. It first authenticates the workbook against the recorded SHA-256, then checks the three trial rows in Analysis_Dataset (30 selected fields: identifiers, denominators, count-unit effect types, aggregate counts and effect/CI components) against the public reference JSON. It also checks that the human review's *unverified Clinical Endpoint Committee source wording* remains explicitly unverified.

Run with the privately held, unchanged workbook:

    python research_pilots/finerenone_hf_2026_10_26/verify_human_workbook.py --workbook /private/path/Finerenone_HF_Extraction_Record-3.xlsx

The local verification on the 26 October original returned PASS_PRIVATE_WORKBOOK_TO_PUBLIC_AGGREGATE_BRIDGE_ONLY, checked_aggregate_cells=30 and cec_appendix_status=NOT_VERIFIED. The workbook's literal spreadsheet data were inspected without reuploading or releasing the file. The seven actual tabs are README, Analysis_Dataset, Extraction_Summary, Detailed_Extraction, Endpoint_Definitions, MetaAnalysis_Extraction and Discrepancy_Log; the README mentions a Next_Steps tab that does not exist. That documentation omission does not affect the checked trial numbers but is recorded, not silently repaired.

The Python test file tests/test_finerenone_workbook_bridge.py uses **constructed synthetic XLSX files** only. It deliberately fails for altered hashes, one modified FINEARTS event count, an incorrect HR label and overwritten CEC uncertainty. Those CI tests exercise the bridge code but **do not run against the private original**. The local human-XLSX check is a separate piece of evidence, not an independently blinded second extraction.

## Additional candidate source discrepancies — do not report as adjudicated

We compared the published Rivera-Martinez version-of-record PDF, DOI 10.1007/s10557-024-07666-x ([PDF](https://d-nb.info/1360377204/34), Table 3, PDF page 9 / zero-based page 8), with the original FINEARTS-HF trial results ([NEJM](https://doi.org/10.1056/NEJMoa2407107); [PubMed](https://pubmed.ncbi.nlm.nih.gov/39225278/)). The following claims are separately recorded in reference.json as **candidate source-to-source discrepancies**, not confirmed published corrections:

1. The review's FINEARTS cardiovascular-death row prints HR **0.93 (0.71–0.94)**, whereas the original FINEARTS trial reports **0.93 (0.78–1.11)**. This crosses the null in the original interval, whereas the review table's upper bound does not. Confirm against the complete publication PDF and any published correction history, and obtain independent reviewer adjudication before contacting an editor.
2. The review's Methods state that all three studies supplied HRs for HF hospitalisation, while the FINEARTS **0.82 (0.71–0.94)** input is a total (first and recurrent) worsening-HF **event-rate ratio**. Its main results include urgent visits, beyond hospital admissions.
3. The review table's generic patients-with-events heading covers FINEARTS counts **842/1024**, which are actually *total recurrent event counts*, not numbers of distinct patients affected. The asterisk may explain the exceptional counting unit, so independently inspect its table note and supplementary materials before calling the wording incorrect.

These findings are *not* part of the already tested 3-trial forest-plot numerical reproduction and should not automatically be promoted to the common programme's scientific-validation gate. The original review already acknowledges population differences, which must be preserved in any critique. No contact with the authors or editors was made through this PR.

### Verification ledger

| Piece of work | Denominator | Status | Meaning |
| --- | ---: | --- | --- |
| Private human workbook to published aggregate fixture | 30 selected cells | PASS locally | SHA-256 matched; 30 fields concordant |
| Bridge failure-injection cases | 5 synthetic tests | PASS locally; PR CI separately | No private workbook in CI |
| Public paper arithmetic reproduction | 3 rounded published log effects | PASS numerical only | Not a common-estimand clinical result |
| FINEARTS CEC appendix exact charter | Not yet documented | NOT_RUN | Prior spreadsheet itself says verification incomplete |
| Pinned method-matched external R parity | 0 confirmed methods | NOT_RUN | Existing generic R CI is not this test |
| Human independent blinded second adjudication | 0 confirmations | BLOCKED | Human reviewer requested |
| Clinical admissibility of mixed trial effects | 0 endorsements | BLOCKED | Different endpoints, effect measures, populations |

Source/provenance scope is deliberately narrow. Public aggregate figures are cited to their original sources, and the unpublished contributor's workbook is not shared without explicit permission.


### Verified PDF forest-plot cross-check: cardiovascular mortality uncertainty

Direct visual inspection of the [published Figure 2](https://link.springer.com/content/pdf/10.1007/s10557-024-07666-x.pdf#page=9) confirmed a *third* confidence interval for the same FINEARTS-HF cardiovascular-death HR: the forest plot prints **0.93 (0.81–1.07)**, with **SE(log HR)=0.0710** and **53.2% inverse-variance weight**. Table 3 on the same page prints **0.93 (0.71–0.94)**, whereas the [original FINEARTS report](https://pubmed.ncbi.nlm.nih.gov/39225278/) prints **0.93 (0.78–1.11)**. These are three different intervals.

A sensitivity calculation using the same two DKD CV-death trial estimates from Figure 2, changing *only* the FINEARTS CV-death interval, gives:

| Scenario | FINEARTS log-HR SE (rounded-input) | FINEARTS weight | Approximate pooled HR (95% CI) |
| --- | ---: | ---: | --- |
| **Using printed forest-plot interval** 0.81–1.07 | 0.07102 | 53.23% | 0.908 (0.820–1.005) |
| **Using original trial interval** 0.78–1.11 | 0.09001 | 41.47% | 0.902 (0.805–1.011) |

Both scenarios have DerSimonian–Laird tau-squared equal to zero when reconstructed from rounded intervals; both overall confidence intervals include 1 (non-significant). The 11.8-percentage-point difference in FINEARTS weight is not a proven reanalysis of the authors' original RevMan project, and the precise source of their uncertainty input is **not established**. Nonetheless, this is a concrete and testable source-to-forest mismatch, not merely a narrative wording issue. Please request independent adjudication and source-located method/CI verification before any correction correspondence. The separate machine-readable sensitivity and corresponding regression test live in reference.json and tests/test_finerenone_hf_human_reference.py.


### Separate native R arithmetic cross-check

An additional test in oracle-tests/test_finerenone_hf_base_r.py executes an independent base-R formula implementation inside the repository's existing GitHub Actions **R 4.4.3** job, without importing a stored Python calculation. It compares three explicitly labelled scenarios: the historical HF mixed-measure *numeric replay*, the printed CV-death forest inputs and the CV-death sensitivity using original FINEARTS uncertainty. This is computational cross-checking of rounded published log effects, **not** a methodological match to a version-pinned RevMan project or external blinded adjudication. The A four-family method-matched benchmark and B prospective scientific validation remain NOT_RUN/BLOCKED independently of this component check. A PASS is claimable for this added R test only after exact-head GitHub Actions success.
