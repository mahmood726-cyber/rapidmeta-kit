# Advanced-technique import backlog (verified)

Cross-repo mining of `C:\Projects\allmeta` (R-verified `shared/` engines) and the
`glp1-obesity-mbnma` exemplar, 2026-06-13, via a multi-agent workflow with
adversarial verification + node parity. Each item below was confirmed: the gap is
real (grep of `template/assets/vendor/`), the source is named, and the R-verified /
experimental flag is checked. Experimental engines must carry an **"Experimental"**
badge at point of display and never headline (allmeta `EXPERIMENTAL-METHODS.md`).

## DONE this session
- **Survival engine** `rapidmeta-survival.js` (HR pool, RMST, interval-HR, NNT,
  non-PH) authored + wired; HR-NNT + non-PH are first-class (REML+HKSJ+t, Altman-
  Andersen NNT), RMST + interval-HR badged **Experimental** (need KM/interval data
  the model doesn't carry → self-skip). Fixed a generated-code bug: it forced
  fixed-effect pooling at k<5 (anticonservative); now REML+HKSJ+t+PI for all k≥2.
  Field-map: panels read `publishedHR/hrLCI/hrUCI` + gate on `estimandType==='HR'`.

## P1 — high value, R-verified, ready to port (pure-JS `allmeta/shared/`)
| Technique | Source | Kit gap |
|---|---|---|
| PET-PEESE conditional small-study adjustment | `allmeta/pet-peese` | kit has Egger/Peters only, NO PET-PEESE |
| Vevea-Hedges step-function selection model | `allmeta/shared/selmodel.js` | no selection-model engine |
| Robust Variance Estimation (CR2, Hedges-Tipton-Johnson) | `allmeta/shared/rve.js` | no cluster-robust / dependent-effects |
| UWLS / multiplicative-heterogeneity pooling | `allmeta/shared/uwls.js` | additive RE only; advanced-stats prefers UWLS for observational |
| Binomial-normal GLMM for rare events | `allmeta/shared/rare-events-glmm.js` | kit uses +0.5 correction (biases OR→1) |
| **Full bivariate Reitsma ML DTA** | `allmeta/shared/dta-bivariate.js` | kit `dta-bivariate.js` fixes ρ=0 (logit-DL); needs full ML + ρ |
| **Two-stage Greenland-Longnecker dose-response** | `allmeta/shared/dose-response.js` | kit `dose-response.js` is naive one-stage, ignores within-study covariance |

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
