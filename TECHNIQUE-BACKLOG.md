# Advanced-technique import backlog (verified)

Cross-repo mining of `C:\Projects\allmeta` (R-verified `shared/` engines) and the
`glp1-obesity-mbnma` exemplar, 2026-06-13, via a multi-agent workflow with
adversarial verification + node parity. Each item below was confirmed: the gap is
real (grep of `template/assets/vendor/`), the source is named, and the R-verified /
experimental flag is checked. Experimental engines must carry an **"Experimental"**
badge at point of display and never headline (allmeta `EXPERIMENTAL-METHODS.md`).

## DONE 2026-06-13 (P3 batch #2 — GOSH + design-by-treatment inconsistency)
- **GOSH** (`gosh.js` + panel): subset-cloud heterogeneity diagnostic extracted
  verbatim from allmeta/gosh; full enumeration k≤15, seeded xoshiro sample k>15;
  inline canvas scatter (estimate vs I²) + cluster-gap modality hint. Auto, k≥3.
- **Design-by-treatment** (`nma-dbt.js` + panel): global inconsistency test
  extracted verbatim from allmeta/nma-inconsistency; fitNMA matches the netmeta
  inco-tiny oracle EXACTLY (Q=1.3352011607, TE_B=−0.26802239, TE_C=−0.46922524),
  chiSqCDF == R pchisq, single-loop global p == oracle node-split p (0.96149087).
  NMA-conditional; FE + DL-RE columns; complements the kit's node-split.
- Tests: +3 (GOSH enumeration/full-pool, DBT netmeta-oracle parity, DBT
  inconsistent/star behaviour). Smoke harness now mounts 9 panels. Suite = 78.
- This clears every extractable backlog item; remaining are the documented
  data-model-mismatch DEFERRALS, the WILL-NOT-PORT server-side MCMC item, and the
  two rescope-flagged items (Copas full MLE, closed-form POTH).

## DONE 2026-06-13 (P3 batch — Rücker limit-MA + Begg-Mazumdar)
- **Limit meta-analysis** (`limit-ma.js` + panel): engine extracted verbatim from
  the allmeta limit-ma HTML app; metasens::limitmeta parity to 1e-12 (limit,
  seLimit, beta_r, G², tau2 all exact). Panel shows the small-study-adjusted OR
  vs RE, the radial slope, and G². Binary, k≥3, sensitivity-only.
- **Begg-Mazumdar** rank test added to funnel-diagnostics (Kendall τ-b exact vs
  metafor::ranktest); now a 4-test battery (Egger, Peters, Begg, trim-and-fill)
  + PET-PEESE. Harbord/Thompson-Sharp NOT ported — only named in the source
  prose, never coded there.
- Tests: +2 (limit-MA metasens anchor, Begg τ anchor); smoke harness mounts 7
  panels + exercises funnel Begg/trim-fill.

## DONE 2026-06-13 (P2 batch — trim-and-fill upgrade, multiplicative NMA, multilevel REML)
- **Trim-and-fill** upgraded: `trimfill.js` (iterative Duval-Tweedie L0, metafor
  parity 1e-7) vendored; `funnel-diagnostics.js` now delegates to `AlmTrimFill`
  when present (simplified L0 kept only as standalone fallback). Required adding
  a `method:'FE'` branch to `_alm-stats-shim.js` pool (FE → τ²=0).
- **Multiplicative NMA** (`multiplicative-nma.js` + panel): NMA-conditional
  auto-panel; builds per-trial contrast rows from `NMA_CONFIG.comparisons`,
  reports φ=Q/(n−p), φ-inflated SEs, and the additive-vs-multiplicative AIC
  decision (switch when ΔAIC≥2). Self-skips on pairwise dashboards.
- **Multilevel REML** (`multilevel-reml.js` + panel): paste-input tool (kit has
  no nested data model); σ²₃/σ²₂ partition by REML; metafor `rma.mv` parity on
  Konstantopoulos 2011 to 1e-5.
- Tests: +3 engine anchors in `test_advanced_engines.py` (11 total) + smoke
  harness now mounts 6 panels and exercises the funnel trim-and-fill delegation.
- Also reconciled the orphan root `assets/` tree to match template/docs.
- Triage of the rest recorded in the P2/P3 sections below (DEFERRED with reason
  / TODO HTML-app extraction / WILL NOT PORT for the server-side MCMC item).

## DONE 2026-06-13 (P1 batch — selection model, UWLS, rare-events GLMM, RVE)
- Vendored four R-verified `allmeta/shared/` engines VERBATIM into
  `template/assets/vendor/`: `uwls.js`, `selmodel.js`, `rve.js`,
  `rare-events-glmm.js`, plus `_alm-stats-shim.js` (supplies the optional
  `AlmMaCore`/`AlmStats` t-quantile so UWLS/RVE/selmodel use t_{k-1}, not z —
  shim's qt matches R to ≤1e-4).
- Four panels: **UWLS** (multiplicative-heterogeneity sensitivity vs the RE
  primary; observational IV trap), **Vevea-Hedges** (step-function selection
  pub-bias panel, auto k≥4, declines on unidentifiable fits), **rare-events
  GLMM** (CM.EL conditional-exact, auto-mounts only when ≥1 zero cell, contrasts
  the +0.5-corrected OR it replaces), and **RVE/CR2** (paste-input tool for
  dependent effects — the kit's 1-effect-per-trial model has no clusters so it
  can't auto-mount; computes only on explicit user input, anti-fabrication).
- Wired into both HTML hosts (`template/base_dupilumab_copd.html` +
  `docs/index.html`); engines+panels copied to all three asset trees
  (template/docs/root) in lockstep.
- Tests (all green, 70 total): `test_advanced_engines.py` (8 node anchors:
  UWLS vs R lm to 1e-6, RVE β exact, rare-events native zero-cell + CM.EL,
  selmodel ML well-formedness) + `test_panels_mount.py` (DOM-stub smoke proving
  all 4 panels mount without runtime error).
- Data-model note: RVE is the only P1 item that does NOT fit the kit's
  one-effect-per-trial model (it needs clusters), hence paste-input not auto —
  same class of data-model gap as the dose-response GL two-stage below.

## DONE this session
- **Survival engine** `rapidmeta-survival.js` (HR pool, RMST, interval-HR, NNT,
  non-PH) authored + wired; HR-NNT + non-PH are first-class (REML+HKSJ+t, Altman-
  Andersen NNT), RMST + interval-HR badged **Experimental** (need KM/interval data
  the model doesn't carry → self-skip). Fixed a generated-code bug: it forced
  fixed-effect pooling at k<5 (anticonservative); now REML+HKSJ+t+PI for all k≥2.
  Field-map: panels read `publishedHR/hrLCI/hrUCI` + gate on `estimandType==='HR'`.
- **DTA full bivariate Reitsma** `dta-reitsma.js` — replaces the ρ=0 independent-DL
  pool with the R-verified bivariate ML (estimated Σ/ρ), vendored from
  `allmeta/shared/dta-bivariate.js`, bit-exact vs `mada::reitsma` on AuditC. Panel
  auto-upgrades via `RapidMetaDTA`; DL fallback for k<4.
- **Dose-response** slope test z → Knapp-Hartung **t_{k-2}** (the only in-data-model
  flaw; the full GL two-stage needs per-study dose-level cell-count tables the kit's
  one-point-per-trial model doesn't carry — promoted to the data-model item below).
- **PET-PEESE** conditional small-study-effect adjustment added to funnel-diagnostics
  (Stanley-Doucouliagos, t_{k-2}, PET→PEESE switch) — ported from allmeta/pet-peese.
- **Extraction**: vendored allmeta `rct-regex-extract.js` + a self-mounting offline
  "paste-to-extract" tool in the Extraction tab (anti-fabrication guards; never
  auto-writes). Remaining allmeta extractors available to add: `ctgov-extract.js`
  (CT.gov JSON → trial), `rct-classifier-v1.js` (RCT screen), `extract-grounding-v1.js`
  (verify numbers vs source), `pdf-extract-v1.js` (needs pdf.js bundled — offline cost).

## P1 — high value, R-verified, ready to port (pure-JS `allmeta/shared/`)
| Technique | Source | Kit gap |
|---|---|---|
| ~~PET-PEESE conditional small-study adjustment~~ | — | **DONE** (in funnel-diagnostics) |
| ~~Vevea-Hedges step-function selection model~~ | — | **DONE** — `selmodel.js` + `selmodel-panel.js` (pub-bias panel, k≥4, auto) |
| ~~Robust Variance Estimation (CR2, Hedges-Tipton-Johnson)~~ | — | **DONE** — `rve.js` + `rve-panel.js` (paste-input tool; kit's 1-effect/trial model has no clusters, so it's user-supplied dependent-effects, not auto) |
| ~~UWLS / multiplicative-heterogeneity pooling~~ | — | **DONE** — `uwls.js` + `uwls-panel.js` (sensitivity vs RE primary; t_{k-1} CI via `_alm-stats-shim.js`) |
| ~~Binomial-normal GLMM for rare events~~ | — | **DONE** — `rare-events-glmm.js` + `rare-events-panel.js` (CM.EL conditional-exact; auto-mounts only when ≥1 zero cell, contrasts the +0.5-corrected OR) |
| ~~Full bivariate Reitsma ML DTA~~ | — | **DONE** (see above) |
| ~~Two-stage Greenland-Longnecker dose-response~~ | `allmeta/shared/dose-response.js` | **needs a per-study dose-level data model** (cell counts at each dose); kit carries one (dose, effect) per trial. Slope t-test done; GL covariance is a future data-model item. |

## P2 — meaningful, R-verified
- ~~Three-level (multilevel) REML MA~~ — **DONE 2026-06-13** `multilevel-reml.js` + `multilevel-reml-panel.js` (paste-input; kit has no nested data model; metafor parity on Konstantopoulos 2011 to 1e-5)
- Location-scale meta-regression (models τ², not just mean) — `allmeta/shared/location-scale.js` — **DEFERRED**: needs per-study moderator + scale design matrices (X, Z) the kit doesn't carry; would require a matrix-paste UI. Engine vendorable when a moderator data model exists.
- ~~Iterative Duval-Tweedie L0 trim-and-fill~~ — **DONE 2026-06-13** `trimfill.js`; funnel-diagnostics now delegates to it (metafor `trimfill` L0 parity to 1e-7, FE k0=5 / DL k0=4 anchors). Replaced the simplified L0.
- ~~Rücker limit meta-analysis (shrunken small-study-adjusted estimate)~~ — **DONE 2026-06-13** `limit-ma.js` (extracted verbatim from `limit-ma/index.html`) + `limit-ma-panel.js`; metasens::limitmeta parity to 1e-12 (limit=0.411998, G²=0.313521).
- Extended pub-bias battery — `allmeta/pubbias-tests` — **PARTIAL DONE 2026-06-13**: added **Begg-Mazumdar** rank test to funnel-diagnostics (Kendall τ-b = metafor::ranktest exactly, 0.4319297483313; p is the source's normal approximation). NOTE: the allmeta source app only *names* Harbord/Thompson-Sharp in prose — they are NOT implemented as code there, so they were not ported (would be net-new, not a port).
- ~~Multiplicative-heterogeneity NMA (network UWLS)~~ — **DONE 2026-06-13** `multiplicative-nma.js` + `multiplicative-nma-panel.js` (NMA-conditional auto-panel, AIC additive-vs-multiplicative; netmeta FE/Q parity + √φ invariants)
- Additive component-NMA (CNMA) — `allmeta/shared/cnma-receptor.js` — **DEFERRED**: needs a component-design matrix (which treatments contain which components) the kit doesn't model; niche.
- ~~Design-by-treatment global inconsistency~~ — **DONE 2026-06-13** `nma-dbt.js` + `nma-dbt-panel.js` (extracted verbatim from `nma-inconsistency`): fitNMA matches the netmeta inco-tiny oracle exactly (Q=1.3352011607, TE_B/C exact); chiSqCDF == R pchisq; single-loop global p == oracle node-split p. NMA-conditional; complements the existing node-split.

## P3 — niche / experimental
- ~~Q-profile CI for I²/τ² helper~~ — **ALREADY IN KIT** (`tau2-qprofile.js`, Viechtbauer 2007). No port needed.
- ~~GOSH plot (multimodal/subgroup heterogeneity)~~ — **DONE 2026-06-13** `gosh.js` + `gosh-panel.js` (extracted verbatim from `allmeta/gosh`): full enumeration k≤15 / seeded random sample k>15; inline canvas scatter (estimate vs I²) with full-sample point + a simple cluster-gap modality hint.
- Spec-collapse / multiverse weighted-likelihood aggregator — `allmeta/shared/spec-collapse.js` — **DEFERRED**: needs multiverse specs (many analyses of one dataset); the kit is single-MA. This is the separate Spec-Collapse Atlas project's domain.
- **[Experimental]** Browser least-squares Emax dose-response — `allmeta/glp1-obesity-mbnma/bayes_mbnma.py` — **WILL NOT PORT**: server-side MCMC; integration notes say do NOT port MCMC to the browser. Surface only as pre-computed Experimental results.
- **[Experimental]** Population-transported NMA (entropy balancing) — `allmeta/shared/transported-nma-v1.js` — **DEFERRED (experimental)**: surface only as pre-computed; needs target-population covariate data.

## DONE 2026-06-13 (Flagged-item resolution — closed-form Wigle POTH)
- **Closed-form Wigle POTH** (`alm-poth.js` vendored verbatim from
  `allmeta/shared/poth.js`; CRAN `poth` oracle: `poth([.9,.6,.3,.2])=0.54`,
  perfect=1, flat=0). The kit's `poth.js` previously headlined a Shannon
  rank-entropy ratio under Wigle's name — a misattribution, since Wigle's POTH
  IS the S²/S²max variance ratio. Fixed: `POTH.compute(rankogram)` now derives
  SUCRA from the rankogram and headlines the canonical closed form (matches
  `AlmPOTH` to float precision — single source of truth), with the entropy
  metric demoted to a clearly-labelled secondary `rankEntropyPrecision` field +
  "Secondary" render section. The `nma-sucra.js` POTH≥0.5 winner-gate now gates
  on the correct (canonical) value with no call-site change. `alm-poth.js`
  wired before `poth.js` in both HTML hosts; copied to all three asset trees.
- Tests: +2 (`test_alm_poth_cran_closed_form_anchor`,
  `test_poth_compute_headline_is_canonical_wigle`). Suite = 80.

## DONE 2026-06-13 (Flagged-item resolution — Copas-Shi full MLE)
- **Copas-Shi (2000) selection-model profile MLE** (`copas-shi.js` extracted
  VERBATIM from the allmeta `copas/index.html` engine — a faithful port of
  `metasens:::copas.loglik.without.beta` + its analytic gradient, box-constrained
  MLE). Re-scope decision: PORT the real MLE rather than patch the heuristic.
  Reproduces `copas-oracle.json` (R metasens 1.5-3): unadjusted FE = metafor
  (`0.246944262521`, 1e-6); profile-MLE effect/ρ/τ match the oracle to ~1e-7
  where ρ is identified (publprob ≤ 0.9). At publprob=1, g1=0 so ρ is
  non-identified (degenerate) — anchored on effect/τ there, not ρ; the seTE
  *display* fallback chain differs ~6e-3 (metasens-faithful carry-forward, not a
  validated quantity).
- New `copas-shi-panel.js` auto-mounts (binary, k≥3) a Copas-Shi sensitivity
  table (publprob path → adjusted OR + 95% CI + ρ + est. unpublished) with the
  k<15 illustrative caveat (advanced-stats), via `PanelHelper`. Wired after the
  GOSH/DBT panels in both hosts; copied to all three asset trees; smoke harness
  now mounts **10** panels.
- **Secondary-claim fix**: the kit's pre-existing heuristic Copas chart (#13)
  borrowed Copas's "ρ" parameter name for an ad-hoc severity knob. Relabelled
  its x-axis to "Selection severity (heuristic knob, NOT Copas ρ)" and its
  EXPLORATORY disclosure now points to the validated Copas-Shi MLE panel for
  inference (both HTML hosts).
- Tests: +1 (`test_copas_shi_profile_mle_matches_metasens_oracle`). Suite = 81.

## Flagged (needs correction before applying)
- ~~**Copas-Shi full MLE**~~ — **DONE 2026-06-13** (see above; ported the real MLE).
- ~~**Closed-form Wigle POTH (S²/S²max)**~~ — **DONE 2026-06-13** (see above).
- _All flagged items resolved. Remaining backlog = documented data-model
  DEFERRALS (location-scale, CNMA, spec-collapse, transported-NMA) + the
  WILL-NOT-PORT server-side MCMC item (Emax MBNMA)._

## Integration notes
- Port targets are self-contained `allmeta/shared/*.js`; adapt to `PanelHelper`
  (`buildCollapsiblePanel` / `insertAfterRBadge`) and add a `<script defer>` after
  `_panel-helper.js`. The MBNMA/transport engines are server-side MCMC — surface
  only as pre-computed Experimental results; do NOT port MCMC to the browser.
- The DTA (ρ=0) and dose-response (one-stage) upgrades replace *existing wired*
  panels and are the highest-leverage NMA/DTA/dose items (task #7).
