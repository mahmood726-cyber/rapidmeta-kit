# Advanced-technique import backlog (verified)

Cross-repo mining of `C:\Projects\allmeta` (R-verified `shared/` engines) and the
`glp1-obesity-mbnma` exemplar, 2026-06-13, via a multi-agent workflow with
adversarial verification + node parity. Each item below was confirmed: the gap is
real (grep of `template/assets/vendor/`), the source is named, and the R-verified /
experimental flag is checked. Experimental engines must carry an **"Experimental"**
badge at point of display and never headline (allmeta `EXPERIMENTAL-METHODS.md`).

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
- Three-level (multilevel) REML MA — `allmeta/shared/multilevel-reml.js`
- Location-scale meta-regression (models τ², not just mean) — `allmeta/shared/location-scale.js`
- Iterative Duval-Tweedie L0 trim-and-fill (replace kit's simplified L0) — `allmeta/shared/trimfill.js`
- Rücker limit meta-analysis (shrunken small-study-adjusted estimate) — `allmeta/limit-ma`
- Extended pub-bias battery (Harbord, Begg, Thompson-Sharp) — `allmeta/pubbias-tests`
- Multiplicative-heterogeneity NMA (network UWLS) — `allmeta/shared/multiplicative-nma.js`
- Additive component-NMA (CNMA) — `allmeta/shared/cnma-receptor.js`
- Design-by-treatment global inconsistency (complete node-split panel) — `allmeta/nma-inconsistency`

## P3 — niche / experimental
- Q-profile CI for I²/τ² helper — `allmeta/shared/heterogeneity-ci.js`
- GOSH plot (multimodal/subgroup heterogeneity) — `allmeta/gosh`
- Spec-collapse / multiverse weighted-likelihood aggregator — `allmeta/shared/spec-collapse.js`
- **[Experimental]** Browser least-squares Emax dose-response (offline surrogate for the server-side MBNMA) — `allmeta/glp1-obesity-mbnma/bayes_mbnma.py`
- **[Experimental]** Population-transported NMA (entropy balancing) — `allmeta/shared/transported-nma-v1.js`

## Flagged (needs correction before applying)
- **Copas-Shi full MLE** (kit's "Copas" is a heuristic ρ-sweep, not the MLE) — verifier found a secondary claim issue; re-scope before porting.
- **Closed-form Wigle POTH (S²/S²max)** — kit `poth.js` uses a Shannon-entropy ratio (a *different* valid metric); allmeta has the CRAN-`poth`-verified variance form. Treat as an optional refinement, not a bug.

## Integration notes
- Port targets are self-contained `allmeta/shared/*.js`; adapt to `PanelHelper`
  (`buildCollapsiblePanel` / `insertAfterRBadge`) and add a `<script defer>` after
  `_panel-helper.js`. The MBNMA/transport engines are server-side MCMC — surface
  only as pre-computed Experimental results; do NOT port MCMC to the browser.
- The DTA (ρ=0) and dose-response (one-stage) upgrades replace *existing wired*
  panels and are the highest-leverage NMA/DTA/dose items (task #7).
