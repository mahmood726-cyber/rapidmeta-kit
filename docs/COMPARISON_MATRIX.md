# RapidMeta — Honest Head-to-Head Comparison Matrix

> **Scope & honesty note.** The RapidMeta column is grounded in the actual shipped
> code (`template/base_dupilumab_copd.html`, ~1.26 MB single file, plus
> `assets/vendor/*.js` advanced panels and `assets/js/paper-studio.js`), verified by
> grep on 2026-06-15. Competitor columns are **best-effort and may be dated** — the
> author's knowledge of vendor feature sets can lag releases. **Verify every
> competitor cell against current vendor documentation before relying on it.**
> Per the repo's anti-marketing rule, words like "global / full / complete /
> integrated / world-class" are avoided unless the implementation supports them now.
>
> Legend: **Yes** = implemented and verifiable · **Partial** = exists but narrower
> than a category leader · **No** = not present · **n/a** = not that kind of tool.

## What was verified in the RapidMeta code

Confirmed present in the engine by symbol grep (occurrence counts in parentheses):

- REML τ² estimator (`tau2_reml`, 22) · HKSJ adjustment (`hksj`, 219) ·
  prediction interval with t-quantile (`piLCI` 47, `tQuantile` 10) ·
  Q-profile τ² CI (`qProfileTau2CI`, 3) · I² CI (15).
- Fragility index (27) · cumulative MA (55) · leave-one-out (12).
- Published-ratio pooling (`trialHasPublishedRatio`, 4) ·
  continuous mean-difference engine (`ContinuousMDEngine`, 6).
- Effect-measure extraction patterns (`PATTERNS`, several regex blocks).
- Screening workflow `screenReview` / `DualReviewer` (126) — a **heuristic /
  dual-reviewer reconciliation** workflow, **not** a bundled live LLM API call by
  default (the file references an LLM-assist concept but ships heuristic screening).
- GRADE (227 refs) · PRISMA flow + checklist (92) · TruthCert provenance (3) ·
  Paper Studio educational paper-builder (`assets/js/paper-studio.js` + siblings).

Advanced method panels in `assets/vendor/` (each a self-contained JS module, many
carrying an `r-validation-*` badge vs metafor/mada): NMA consistency / node-split /
design-by-treatment (`nma-consistency.js`, `nma-dbt.js`), SUCRA + POTH
(`nma-sucra.js`, `poth.js`), DTA bivariate / Reitsma (`dta-bivariate.js`,
`dta-reitsma.js`), trim-fill, selection models (`selmodel.js`), Copas
(`copas-shi.js`), RoBMA (`robma.js`), RVE (`rve.js`), multilevel REML, E-value,
dose-response / splines, multiplicative NMA, transportability / transported NMA,
spec-collapse, UWLS, TSA, GRIM/Benford & INSPECT-SR integrity checks, survival /
RMST / interval-HR pooling.

Architecture facts verified: **single self-contained HTML file**; assets bundled;
**storage is `localStorage` only** (no server backend, no websockets → **no
real-time multi-user collaboration**); CSP permits *optional* `cdn.plot.ly` and a
Font-Awesome CDN stylesheet but the analytic engine runs offline without them; the
file can issue a **live `fetch` to ClinicalTrials.gov** when online (limited
retrieval), but it is **not** a full search-import-dedupe ingestion pipeline.

## Comparison matrix

| Dimension | RapidMeta | Covidence | DistillerSR | RevMan / RevMan Web | metafor + meta (R) | Elicit |
|---|---|---|---|---|---|---|
| Literature search / retrieval | Partial — optional live CT.gov fetch; no bundled multi-database search | Partial — import from databases; no native search engine | Yes — search + API connectors | No (manual import) | No (you bring data) | Yes — searches literature corpus |
| Title/abstract screening | Yes — heuristic + dual-reviewer reconcile | Yes — dual-reviewer, conflict mgmt | Yes — workflow + AI options | No | No | Yes — AI screening |
| AI-assisted screening | Partial — heuristic, not a live LLM by default | Partial — AI prioritization | Yes — AI/ML classifiers | No | No | Yes — LLM-based |
| Full-text / data extraction | Partial — regex `PATTERNS` + extract-assist | Yes — extraction forms | Yes — configurable forms | Partial (RoB/data tables) | No | Yes — LLM extraction |
| Deduplication | Partial / not a focus | Yes — strong dedup | Yes | No | No | Partial |
| Reference management | No (not a RIS/EndNote manager) | Partial | Partial | No | No | Partial |
| Pairwise MA depth (τ² estimators, HKSJ, PI, Q-profile) | **Yes — REML, HKSJ, t-PI, Q-profile τ² CI, I² CI** | No / minimal | No / minimal | Partial (RevMan: limited estimators) | **Yes — reference-grade, all estimators** | No |
| Network meta-analysis | Yes — consistency, node-split, DBT, SUCRA+POTH, league/forest | No | No | No | Yes (via netmeta/multinma in R ecosystem) | No |
| Diagnostic test accuracy MA | Yes — bivariate/Reitsma, SROC, Fagan, QUADAS-2 | No | No | No | Yes (via mada/extensions) | No |
| Publication-bias suite | Yes — trim-fill, Egger/funnel, selection models, Copas, RoBMA, LFK | No | No | Partial (funnel/Egger) | Yes | No |
| GRADE / certainty | Yes — GRADE SoF, CINeMA-style NMA certainty | Partial (export to GRADEpro) | Partial | Partial (links to GRADEpro) | No (not its job) | No |
| PRISMA flow | Yes — flow + checklist generator | Yes | Yes | Yes | No | Partial |
| Living / auto-update review | Yes — living-review tabs | Partial (living review support) | Partial | No | No (manual rerun) | No |
| Works fully offline | **Yes — analytic engine offline; optional CDN only** | No (cloud SaaS) | No (cloud SaaS) | Partial (RevMan desktop yes; Web no) | Yes (local R) | No (cloud) |
| Single-file portability | **Yes — one HTML file, open in a tab** | No | No | No | No (R env needed) | No |
| Real-time multi-user collaboration | **No — localStorage, single browser** | **Yes — core strength** | **Yes — core strength** | Partial (RevMan Web) | No | Partial |
| Audit trail / regulatory acceptance | Partial — self-audit logs; no institutional pedigree | Yes — used in Cochrane/HTA workflows | **Yes — 21 CFR Part 11 positioning** | **Yes — Cochrane standard of record** | Partial (script = audit) | No |
| Provenance / cryptographic signing | **Yes — TruthCert signed bundles** | No | Partial (audit logs) | No | No | No |
| Built-in education / teaching | **Yes — Paper Studio, transparent panels, learning links** | No | No | Partial | No (docs, not in-app) | No |
| Transparent / readable methods (read the math?) | **Yes — JS engine + R-validation badges inline** | No (closed SaaS) | No (closed SaaS) | Partial | **Yes — open-source R** | No (closed) |
| External validation track record | Partial — internal R-parity vs metafor/mada; limited independent publication | Yes — widely cited in published SRs | Yes — widely cited | **Yes — Cochrane gold standard** | **Yes — extensively peer-reviewed** | Partial (vendor benchmarks) |
| Licensing & cost | Free / open (MIT) | Paid SaaS (free trials/Cochrane access) | Paid SaaS (enterprise) | Free (Cochrane) | Free / open source | Paid (freemium) |
| Platform | Browser (single HTML) | Cloud SaaS | Cloud SaaS | Desktop + Web | R / local | Cloud / web |

## (a) Where RapidMeta is genuinely distinctive or leading

The defensible niche is the **combination**, not any single row:

1. **Self-contained single-file, offline analytic engine.** The whole platform is
   one HTML file you can email, archive, or run air-gapped. No SaaS, no install, no
   R environment. None of the listed competitors offer this packaging.
2. **Methods depth unusual for a browser tool.** REML + HKSJ + t-prediction-interval
   + Q-profile τ² CI, NMA (node-split, DBT, SUCRA+POTH), DTA bivariate/Reitsma, and
   a broad publication-bias suite (Copas, RoBMA, selection models) — depth that
   normally lives only in R, here delivered in-browser with R-parity badges.
3. **Self-auditing + provenance.** Assurance/capsule checks and TruthCert signed
   bundles make the artifact attest to its own internal consistency — a provenance
   story the established SR tools do not ship.
4. **Integrated education.** Paper Studio and transparent, readable JS engines let a
   learner see and run the actual math, not a black box.

## (b) Where established tools clearly beat it

- **Collaboration & scale.** Covidence and DistillerSR are built for teams: shared
  projects, conflict resolution, role permissions, thousands of records. RapidMeta is
  single-browser `localStorage` with **no real-time multi-user collaboration** — a
  genuine gap, not a stylistic choice.
- **Search / ingestion / dedup.** Covidence and DistillerSR (and Elicit) own the
  front of the pipeline — multi-database search, import, deduplication, extraction
  forms. RapidMeta's retrieval is limited (optional CT.gov fetch) and its dedup is
  not a focus.
- **Regulatory & institutional trust.** RevMan is the Cochrane standard of record;
  DistillerSR carries 21 CFR Part 11 / enterprise-audit positioning. RapidMeta has
  self-audit logs but **no institutional pedigree or regulatory acceptance**.
- **Published external validation.** metafor/meta are peer-reviewed and decades-cited;
  Cochrane reviews validate RevMan in practice. RapidMeta's validation is mostly
  **internal R-parity testing**, with limited independent published validation.
- **Vendor support & SLAs.** Commercial tools offer support contracts, training, and
  uptime guarantees; RapidMeta is a free open project.

## (c) Net positioning

RapidMeta is **frontier-class within a specific niche**: a free, transparent,
offline, single-file analytic-and-reporting layer with methods depth (pairwise, NMA,
DTA, publication bias, GRADE), self-audit, and provenance signing that is rare for a
browser tool — plus built-in teaching. It is **not** the world's most advanced
SR platform overall, and should not be marketed as such. It does **not** replace
Covidence/DistillerSR for team-based search–screen–extract at scale, RevMan for
Cochrane-accepted reviews, or metafor/meta for peer-review-grade reference
statistics. The honest one-line verdict: **best-in-class for solo/offline,
transparent, reproducible synthesis-and-analysis with a teaching and provenance
angle; clearly behind the incumbents on collaboration, ingestion at scale,
regulatory trust, and published validation.**
