> **IMPLEMENTATION STATUS (2026-07-11):** 8 of 9 fixed & shipped in `correctness-fixes-2026-07-10` (bugs 2,4,6,9 then 3,5,7,8), across all 3 vendor copies, full suite green.
> **Bug 1 (everything-model EM posterior variance) DEFERRED:** the fix breaks the model's documented exact-reduction-to-IV-pool invariant (`test_everything_model_gamma_ref_zero_and_reduces_to_re_pool`) — adding the posterior-variance term changes it from a method-of-moments IV-pool generalization to an ML-EM, a design decision rather than a clear bug fix. Left as-is; revisit only if the model is intentionally re-specified as ML-EM.

All nine findings verified against the live code (line numbers, comments, and weight/quantile definitions all match). Here is the synthesized report.

---

# rapidmeta-kit — Correctness Review Synthesis

**Repo:** `C:\Projects\rapidmeta-kit` · **Findings verified in-code:** 9/9 · **Date:** 2026-07-10

## 1. Verdict

**The engine is NOT correctness-clean.** Nine real defects survived adversarial verification and every one was independently re-confirmed against the live source (line numbers, code, and inline comments all match as reported). None is a false-flag of the known "normal-vs-logistic CDF" or "Clopper-Pearson alpha/2" type.

Important scoping, stated honestly:

- **The primary pooled estimate is safe.** The core inverse-variance / REML / HKSJ pooling in `shared/ma-core.js` and the BCG REML anchor are R-parity verified (`tests/test_r_parity.py`, metafor `dat.bcg` + scipy re-derivation). **Zero** of the 9 bugs touch that path's point estimate.
- **The bugs live in secondary panels and one large-df edge case**: publication-bias diagnostics (Egger/Peters/Deeks funnels), NMA contribution/node-split panels, dose-response pseudo-R², a bespoke multivariate "everything model", and a `df>30` t-quantile cap. These panels are precisely the ones the R-parity harness **does not** cover — the harness uses small-k fixtures and never exercises `df>30`, the funnel modules, `dta-funnel.js`, `contribution-matrix.js`, `nma-consistency.js`, or `everything-model.js`.
- **Impact honesty:** 8 are **medium** (a named statistical test computes the wrong statistic / an anticonservative CI or p-value that can flip a verdict), 1 is **low** (only bites at k≥32 and shrinks with df). None is critical — none silently corrupts the headline effect estimate. But eight of them cause a *named* test (Peters, Deeks, Egger, Bucher node-split, Papakonstantinou contribution) to report an inference that is either wrong or mislabeled.

Two of these are duplicated across file copies (`assets/vendor/`, `template/assets/vendor/`, `docs/assets/vendor/`) and two share a root cause (z-instead-of-t on a WLS intercept), so the 9 findings collapse to ~6 distinct fixes.

---

## 2. Confirmed bugs, ranked by impact

### Ranking summary

| # | Impact | Bug | File:line | Verdict effect |
|---|--------|-----|-----------|----------------|
| 1 | Medium | Variational-EM τ² drops posterior-variance term | `everything-model.js:126` (×3 copies) | Anticonservative μ CIs (primary output of that model) |
| 2 | Medium | Peters test uses log-OR IV weight, not marginal-totals weight | `funnel-diagnostics.js:84` | "Peters test" is not Peters' test |
| 3 | Medium | Deeks funnel weights by 1/Var(lnDOR), not ESS | `dta-funnel.js:70` | "Deeks test" is not Deeks' test |
| 4 | Medium | Egger/Peters intercept tested vs normal, not t_{k-2} | `funnel-diagnostics.js:63` | Anticonservative; flips verdict at k<10 |
| 5 | Medium | Deeks intercept tested vs normal, not t_{k-2} | `dta-funnel.js:104` | Anticonservative; flips verdict at k≥4 |
| 6 | Medium | Contribution split is inverted variance-share, mislabeled as precision-share; not Papakonstantinou | `contribution-matrix.js:137` | RoB roll-up weighted toward least-precise edge |
| 7 | Medium | Pseudo-R² mixes FE-weighted RSS with RE-weighted normalizer | `dose-response.js:133`, `meta-regression.js:82` | pseudo-R² can invert 0%↔100% (secondary descriptor) |
| 8 | Medium | Node-split Bucher indirect not reoriented to common reference | `nma-consistency.js:247` | Sign flip → consistent↔inconsistent, conditional |
| 9 | Low | `tCrit975` caps at z=1.96 for df>30 | `continuous-outcome.js:136`, `pairwise-pool.js:75` | CI/PI ~3% too narrow at k≥32 |

---

### Bug 1 — Variational-EM τ² drops the posterior-variance term (Medium)

**File:** `template/assets/vendor/everything-model.js:124-126` (replicated verbatim in `assets/vendor/` and `docs/assets/vendor/`)

**Wrong:** M-step sets `tau2 = max(1e-8, (Σ_s δ̂_s²)/S)` using only the squared posterior *means*. The E-step (lines 112-120) already computes `denom_s = 1/τ² + Σ_{i∈s} 1/v_i`, so each study effect's posterior variance is `1/denom_s` — but the M-step discards it. The comment on line 123 literally promises "τ² = mean of δ² + posterior variance correction"; the correction is absent.

**Right:** `τ²_new = (1/S) Σ_s E[δ_s²|y] = (1/S) Σ_s (δ̂_s² + 1/denom_s)`. The omitted `1/denom_s` is the de-biaser; without it the shrunk `δ̂_s` are pulled toward 0, so τ² converges **below** the true between-study variance. Because per-outcome SE is recomputed as `sqrt(1/Σ 1/(v_i+τ²))` (lines 183-187) with the biased-low τ², the reported μ_o CIs are **anticonservative**. Ranked #1 because it is the only bug that shrinks a CI on a model's *primary* effect output, and it fires every time that model runs.

**Exact fix:** Store posterior variance in the E-step and add it in the M-step, in all three copies:
```js
// E-step, right after delta[s] = num / denom;   (line ~120)
postVar[s] = 1 / denom;
// M-step (replace lines 124-126)
var sumD2 = 0;
for (var s2 = 0; s2 < studies.length; s2++) sumD2 += delta[s2]*delta[s2] + postVar[s2];
tau2 = Math.max(1e-8, sumD2 / studies.length);
```

**R-anchored test:** No native metafor equivalent (bespoke model). Anchor by stacking the study/outcome data and fitting a random-intercept multilevel model: `metafor::rma.mv(yi, V=vi, random = ~ 1 | study, method="ML")` — its `sigma2` is the ML between-study variance the EM should converge to. Assert the engine's converged τ² is within ~1e-3 of `rma.mv$sigma2` on a fixture where studies have few observations (large `1/denom_s`, where the omission bites hardest). The current code will fall materially short.

---

### Bug 2 — Peters test uses the log-OR inverse-variance weight (Medium)

**File:** `template/assets/vendor/funnel-diagnostics.js:81-85`

**Wrong:** `wi = 1/(1/ai + 1/bi + 1/ci + 1/di)` with 0.5 added to *every* cell unconditionally. That is Woolf's inverse variance of the log-OR (identical to `trialLogOR`'s `vi`). Regressing lnOR on 1/N with this weight re-introduces the exact lnOR–SE(lnOR) structural dependence Peters 2006 was built to remove — so the routine is **not** Peters' test. (The line-76 comment `weights = ai*bi/n1i + ci*di/n2i` matches neither the code nor Peters.) Also violates the add-0.5-only-if-a-cell-is-zero rule.

**Right:** `wi = 1/(1/(a+c) + 1/(b+d))` — inverse of the average event-rate variance from marginal totals only (`meta::metabias(method.bias="peters")`: `w <- 1/(1/(event.e+event.c) + 1/(n.e-event.e+n.c-event.c))`). Numeric check a=10,b=90,c=20,d=80: code weight **5.76** vs Peters **25.5** — a materially different statistic and p-value.

**Exact fix:**
```js
const wi = trials.map(t => {
  const events    = t.ai + t.ci;
  const nonevents = (t.n1i - t.ai) + (t.n2i - t.ci);
  return 1 / (1/events + 1/nonevents);
});
// keep xi = 1/(n1i + n2i); apply 0.5 correction only when a cell is 0
```

**R-anchored test:** Build a ≥4-study 2×2 fixture, run `meta::metabias(metabin(ai,n1i,ci,n2i,sm="OR"), method.bias="peters")`, commit its `$statistic` and `$p.value` as the anchor. Assert engine matches to 1e-4. The current code will diverge.

---

### Bug 3 — Deeks funnel weights by 1/Var(lnDOR) instead of ESS (Medium)

**File:** `template/assets/vendor/dta-funnel.js:70`

**Wrong:** `const w = points.map(p => 1 / p.varLnDOR);` where `varLnDOR = 1/TP+1/FP+1/FN+1/TN`. The predictor `1/√ESS` (line 66) is correct, but Deeks 2005 replaced variance weighting *precisely because* Var(lnDOR) depends on the observed cell counts (hence on the DOR), inducing the spurious effect-precision correlation the test exists to avoid. `ESS = 4·n1·n2/(n1+n2)` depends only on the group margins. The two weight vectors are not proportional → intercept, se, t-stat, p-value all wrong; the symmetric/asymmetric verdict can flip.

**Right:** `const w = points.map(p => p.ess);` (Deeks 2005 J Clin Epidemiol 58:882-93; Stata `midas`: regress lnDOR on 1/√ESS weighted by ESS). Also fix the line-69 comment and the line-154 "Weights = 1/Var(ln DOR)" note to "Weights = ESS".

**R-anchored test:** No first-class R function (`mada` omits Deeks; canonical is Stata `midas`). Anchor to the Deeks 2005 worked example, cross-checked by an independent weighted `lm(lnDOR ~ I(1/sqrt(ess)), weights = ess)` in R and asserting the intercept t-stat/p match — consistent with how this repo already anchors (`docs/VALIDATION_DOSSIER.md` honesty ledger: literature anchor + independent re-derivation, not the package itself).

---

### Bug 4 — Egger/Peters intercept tested against normal instead of t_{k-2} (Medium)

**File:** `template/assets/vendor/funnel-diagnostics.js:63` (in `wlsReg`, consumed by both `eggerTest` and `petersTest`; repeated at `comparison-adjusted-funnel.js:132`)

**Wrong:** `wlsReg` estimates a residual dispersion `sigma2 = rss/max(1,k-2)` (line 60) and builds `se_alpha` from it (line 61) — the lm/WLS-with-estimated-dispersion formulation, for which `alpha/se_alpha` is exactly t_{k-2}. Line 63 tests it against `normalCDF` → anticonservative. Decisive self-inconsistency: the **same file's** `petPeese` reuses this `wlsReg` but deliberately recomputes `pPET` with `_tcdf(|t|, k-2)` and comments that a z-test "is anticonservative at the small k typical of these regressions" — the author applied the t fix to the structurally identical PET regression but left Egger/Peters on z.

**Right:** `p = 2*(1 - _tcdf(|stat|, k-2))`, matching `meta::metabias(method.bias="linreg"/"peters")`. (metafor `regtest`'s default `model="rma"` uses z — defensible only for the variances-known variant, which this WLS-with-estimated-sigma2 code is not.) At k=5 (df=3), |t|=2.0 gives normal p=0.045 (flagged) vs t₃ p=0.14 (not flagged) — flips the verdict in exactly the k<10 regime these tests target.

**Exact fix:**
```js
const p_alpha = 2 * (1 - _tcdf(Math.abs(z_alpha), Math.max(1, k - 2)));
```
(`_tcdf` is a hoisted declaration, callable here; `petPeese` unaffected — it ignores `wlsReg`'s `p_alpha`.) Apply the same change to the pnorm-based intercept p at `comparison-adjusted-funnel.js:132`.

**R-anchored test:** `meta::metabias(method.bias="linreg")$p.value` on a k=5 fixture where |t|≈2; assert engine matches the t₃ p (~0.14), not 0.045.

---

### Bug 5 — Deeks intercept tested against normal instead of t_{k-2} (Medium)

**File:** `template/assets/vendor/dta-funnel.js:104`

**Wrong:** `const p_two = 2 * (1 - normalCDF(Math.abs(t_stat)));`. Same root cause as Bug 4: `sigma2 = rss/(k-2)` (line 91) is estimated, so `t_stat = alpha/se_alpha` is genuinely t_{k-2}. The panel gates at k≥4, so df can be 2. At |t|=2.9, df=2: true two-sided p ≈ **0.101** vs normal ≈ **0.0037** — flips the p<0.05 verdict from "no evidence" to "publication bias". The code even computes `df` (line 95) and a t→z transform `z` (line 96) that it then discards, feeding raw `t_stat` into `normalCDF` — internally inconsistent.

**Right:** Evaluate from t_{k-2} via the regularized incomplete beta: two-sided `P(|T_df|>|t|) = I_{df/(df+t²)}(df/2, ½)`.

**Exact fix:** Add `lgamma`/`betacf`/`betai` helpers (Numerical Recipes forms) and replace line 104 with:
```js
const p_two = betai(df/2, 0.5, df/(df + t_stat*t_stat));
```
(then the discarded `z` at line 96 and `normalCDF` can be removed.)

**R-anchored test:** Weighted `lm(lnDOR ~ I(1/sqrt(ess)), weights = ess)`; take `2*pt(abs(t), df=k-2)` on a k=4 fixture; assert engine's `p` matches the t₂ tail, not the normal tail. (Combine with Bug 3's ESS-weight fix so the whole Deeks statistic is correct.)

---

### Bug 6 — Contribution split is inverted variance-share, mislabeled, and not Papakonstantinou (Medium)

**File:** `assets/vendor/contribution-matrix.js:137-138` (comment 134-136, footnote 241)

**Wrong:** `cA = ea.var_mu / totalVar; cB = eb.var_mu / totalVar`. The comment says "precision-share via inverse-variance" and the footnote says "Contribution % = inverse-variance share", but raw variance-share gives the **less-precise** (higher-variance) leg the **larger** %, the exact inverse of a precision share (e.g. var_a=1, var_b=3: edge A is more precise, true precision share 75%, code shows 25%). It also does not implement the cited Papakonstantinou 2018 flow/streams method, under which every 2-edge purely-indirect comparison in a star network is **50/50** regardless of edge precision. This feeds a CINeMA-style per-edge RoB roll-up, so the roll-up is weighted toward the least-precise edge — inverted from intent.

**Right:** For the cited method use `const cA = 0.5; const cB = 0.5;` and correct the comment/footnote to "flow/streams share (Papakonstantinou 2018): each direct leg contributes 50% to a purely-indirect 2-edge comparison." If a genuine precision share were intended instead, it would be `(1/var_a)/((1/var_a)+(1/var_b)) = var_b/totalVar` (i.e. swap the numerators) — but the cited method requires 50/50.

**R-anchored test:** `netmeta::netcontrib()` (or `netmeta`'s contribution matrix) on a 3-node star; assert each direct edge's contribution to a purely-indirect comparison is 0.5. The current code returns a precision-dependent split ≠ 0.5.

---

### Bug 7 — Pseudo-R² mixes FE-weighted RSS with a RE-weighted normalizer (Medium)

**File:** `template/assets/vendor/dose-response.js:131-135`; duplicated at `meta-regression.js:80-84`

**Wrong:** `rss` accumulated with FE weights `1/vi` (line 131), but `c_after = Sw - sumW2/Sw` uses `Sw = Σ 1/(vi+tau2_total)` (RE weights, line 93) and `sumW2 = Σ(1/vi)²` (FE-squared, line 88). Three weight definitions in one moment estimator; the comment "using the model-based weights' RSS" contradicts the FE weights actually used. Worse than biased: when tau2_total is a moderate fraction of vi (the common reporting case), `sumW2/Sw > Sw` → `c_after` goes **negative** → `tau2_resid` clamps to 0 → `pseudoR2` forced to **100%**. Reproduced on flat pure-noise data (k=8, vi=0.03): code `c_after=-5.02`, `tau2_resid=0`, `pseudoR2=100%`; the metafor-convention FE-weighted DL residual gives `tau2_resid=0.065 > tau2_total=0.057` → R²=0%. The statistic inverts 0%↔100%. Only the displayed pseudo-R² is affected — the primary β/SE/CI/p are computed separately and remain correct.

**Right:** One consistent FE weight set. Minimal coherent fix (reuse the FE sum `W0` at line 84):
```js
const c_after = W0 - sumW2 / W0;
```
Metafor-exact (2-parameter) fix: compute FE-weighted `X'WX` and `c_after = W0 - tr((X'WX)⁻¹ X'W²X)`, and compute `rss` from the FE-weighted fit. Apply the identical fix at `meta-regression.js:82`.

**R-anchored test:** `metafor::rma(yi, vi, mods=~x, method="DL")`; the fitted object reports pseudo-R² directly (`$R2`). Assert engine matches on a fixture with `tau2_total ≈ 0.5·mean(vi)` (the regime that currently drives `c_after` negative). Current code returns 100% where metafor returns a finite value.

---

### Bug 8 — Node-split indirect not reoriented to a common reference (Medium, conditional)

**File:** `assets/vendor/nma-consistency.js:247`

**Wrong:** `poolEdge()` orients each edge as its own declared t1-vs-t2 with no reference reorientation, and `computeNodeSplits` does `indirect = bucher(e1.pooled, e2.pooled) = e1.mu_log - e2.mu_log` (line 247), fetching the two reference-side edges by sorted name key and subtracting blindly. Bucher's `indirect(t1 vs t2) = (t1 vs ref) - (t2 vs ref)` requires each leg expressed vs the shared reference. When the reference edge is declared with the reference as its *t1*, that leg's sign is inverted and never corrected. Concrete: triangle {placebo, ramipril, telmisartan} selects ref=ramipril (highest degree, tie broken to an active drug declared as t1); both ref-legs need negation the code omits → code indirect = −(correct), so `direct − indirect` ≈ 2× the true contrast, spuriously flipping consistent↔inconsistent. Sibling `nma-sucra.js:163` (`flip = c.t1 === reference`) proves the codebase knows this reorientation is required; `nma-consistency` omits it. Scope is limited — stars are skipped, and placebo-anchored networks line up by luck — so it only bites closed-loop networks whose reference is a mixed-orientation active drug. Hence medium, not critical.

**Exact fix:** In `computeNodeSplits` (~line 247), reorient each reference leg before Bucher (`byEdge` stores `{edge, pooled}`, so `e1.edge.t1` is available):
```js
const leg1 = e1.edge.t1 === ref ? { mu_log: -e1.pooled.mu_log, se: e1.pooled.se } : e1.pooled;
const leg2 = e2.edge.t1 === ref ? { mu_log: -e2.pooled.mu_log, se: e2.pooled.se } : e2.pooled;
const indirect = bucher(leg1, leg2);
```

**R-anchored test:** `netmeta::netsplit()` on a triangle where the reference node appears as the *treatment* arm in some trials and the *control* arm in others; assert the engine's indirect log-effect matches `netsplit`'s `indirect$TE` in **sign and magnitude**. No current test exercises the numeric indirect sign (only `classifyNetwork`), so this path is unguarded.

---

### Bug 9 — `tCrit975` caps at z=1.96 for df>30 (Low)

**File:** `assets/vendor/continuous-outcome.js:136`; identically `pairwise-pool.js:75`

**Wrong:** `if (df > 30) return 1.96;` — returns z, not the Student-t quantile, for all df>30. This value feeds both the HKSJ random-effects CI (`yRE ± t·seH`) and the Cochrane v6.5 prediction interval (`yRE ± t·√(τ²+seMu²)`). At k=40 (df=39) it uses 1.96 instead of t₀.₉₇₅,₃₉ = 2.0227 → CI and PI ~3.1% too narrow; error is 3.9% at k=32 and ~1.2% at k=101. Self-inconsistent: the same repo computes large-df t correctly in `pi-convention.js:28-30` (Cornish-Fisher) and `_alm-stats-shim.js:48` (exact qt bisection). metafor's `rma(test="knha")`/`predict()` always use `qt(0.975, k-1)`. Low because it only bites at k≥32 (uncommon) and shrinks with df.

**Exact fix (both files):**
```js
function tCrit975(df){
  if (df < 1) return NaN;
  if (df > 30){ const z = 1.959963984540054; return z + (z*z*z + z)/(4*df); }
  return T_975[Math.round(df)] || 1.96;
}
```
(or delegate to the exact `qt()` bisection in `_alm-stats-shim.js`).

**R-anchored test:** Trivial closed form — assert `tCrit975(39)` is within 1e-3 of `qt(0.975, 39) = 2.022691`, and `tCrit975(31)` within 1e-3 of `qt(0.975, 31) = 2.039513`. Also add a k=40 pooling fixture and check the HKSJ CI half-width against `metafor::rma(..., test="knha")` `predict()`; the current code is ~3% narrow.

---

## 3. What was checked (grounding note)

Independently re-confirmed in the live tree: the z=1.96 branch (`continuous-outcome.js:136`), the Peters full-cellwise IV weight and its mismatched line-76 comment (`funnel-diagnostics.js:81-85`), the `normalCDF` intercept p (`funnel-diagnostics.js:63`, `dta-funnel.js:104`), the inverted variance-share with "inverse-variance share" comment (`contribution-matrix.js:137`), the `1/varLnDOR` Deeks weight (`dta-funnel.js:70`), the FE-RSS / RE-`Sw` / FE²-`sumW2` mix (`dose-response.js:88/93/131/133`, mirrored `meta-regression.js:82`), the un-reoriented Bucher subtraction versus `nma-sucra.js:163`'s `flip` (`nma-consistency.js:247`), and the τ² M-step that omits `1/denom_s` despite the line-123 promise (`everything-model.js:126`). The repo's R-parity harness (`tests/test_r_parity.py`, `tests/baselines/ma_core_baseline.json`) covers only the core pooling on small-k BCG-style fixtures — it does not reach any of the eight defective panels or the `df>30` branch, which is why these passed CI. R is not installed in-environment, so every "R-anchored test" above follows the repo's existing convention (`docs/VALIDATION_DOSSIER.md`): commit the package/literature value as an anchor plus an independent scipy/lm re-derivation, not a live metafor call.