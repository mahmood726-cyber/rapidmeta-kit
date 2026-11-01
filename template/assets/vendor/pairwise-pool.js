/* pairwise-pool.js — clean self-contained re-pooling module for RapidMeta reviews.
 *
 * Lifted-and-cleaned from C:/TruthCert_PairwisePro_v2/app.js (R-validated against
 * metafor 100% / 17 core tests). Reimplemented here from first principles rather
 * than extracting from minified app.js.
 *
 * Exports (window.PairwisePool):
 *   pool2x2(trials, opts)   — Paule-Mandel tau^2 + HKSJ + PI per Cochrane Handbook v6.5
 *   renderForest(elem, res, opts) — SVG forest plot with PI band
 *
 * Inputs: trials = [{name, tE, tN, cE, cN}, ...]
 *         opts.measure = 'RR' (default) | 'OR'
 *         opts.haldane = 0.5 (default) for zero-cell continuity correction
 *         opts.tau2Method = 'PM' (default) | 'DL'
 *
 * tau^2 defaults to Paule-Mandel (empirical-Bayes): the value for which the
 * generalized Q-statistic Sum w_i*(y_i - mu_w)^2 equals k-1. Preferred over
 * DerSimonian-Laird, which is downward-biased for small k (Veroniki 2016;
 * Cochrane Handbook). DL remains available via opts.tau2Method='DL'.
 *
 * Output (one shape, log-scale + back-transformed):
 *   { k_used, excludedStudies: [{trial_index, name, reason}], mu_log, mu, ci_lo, ci_hi, pi_lo, pi_hi, tau2, Q, I2, perStudy: [...] }
 *
 * Conventions: Cochrane Handbook v6.5 (Nov 2024 §10.10.4.3) — PI uses t_{k-1};
 * HKSJ floor = max(1, q*) where q* is the RE-weighted statistic
 * (1/df)·Σ wRE_i·(y_i−muRE)²; zero-cell Haldane 0.5 only when ≥1 cell is 0.
 */
(function (global) {
  'use strict';

  // Generalized Q-statistic at a given tau^2 (w_i = 1/(v_i+tau2)); strictly
  // decreasing in tau^2. Shared by the Paule-Mandel solver.
  function genQ(yi, vi, t2) {
    let sw = 0, swy = 0;
    for (let i = 0; i < yi.length; i++) { const w = 1 / (vi[i] + t2); sw += w; swy += w * yi[i]; }
    const mu = swy / sw;
    let F = 0;
    for (let i = 0; i < yi.length; i++) F += (yi[i] - mu) * (yi[i] - mu) / (vi[i] + t2);
    return F;
  }

  // Paule-Mandel tau^2: solve genQ(tau2) = df by bisection (genQ monotone-
  // decreasing, so the root is unique when genQ(0) > df). Robust for small k.
  function tau2PM(yi, vi, df) {
    if (genQ(yi, vi, 0) <= df) return 0;
    let lo = 0, hi = 1, guard = 0;
    while (genQ(yi, vi, hi) > df && guard++ < 200) hi *= 2;
    for (let it = 0; it < 200; it++) {
      const mid = 0.5 * (lo + hi);
      // An absolute tolerance of 1e-12 grossly overestimates PM tau2
      // when Q(0) is just above df and the true root is ~1e-15.
      // Converge until the bracket cannot be split in floating-point.
      if (mid === lo || mid === hi) break;
      if (genQ(yi, vi, mid) > df) lo = mid; else hi = mid;
    }
    return 0.5 * (lo + hi);
  }

  // DerSimonian-Laird tau^2 (opts.tau2Method='DL').
  function tau2DL(wFE, sumWFE, Q, df) {
    if (Q <= df) return 0;
    // C = 2 * sum_{i<j}(w_i * w_j) / sum(w), algebraically identical
    // to sum(w) - sum(w^2)/sum(w). Avoid catastrophic cancellation when
    // one highly precise study dwarfs the other inverse-variance weights.
    let preceding = 0, crossProducts = 0;
    for (let i = 0; i < wFE.length; i++) {
      crossProducts += preceding * wFE[i];
      preceding += wFE[i];
    }
    const C = 2 * crossProducts / sumWFE;
    return Math.max(0, (Q - df) / C);
  }

  // t-distribution two-sided critical value at p=0.025 (95% interval).
  // Exact 97.5th percentiles from R stats::qt(.975, df), for integer df 1..30.
  // Cochrane k-1 confidence/prediction intervals must not be silently distorted
  // by 3-decimal critical values; df>30 uses a fourth-order expansion.
  const T_975 = {
    1: 12.706204736175, 2: 4.302652729749, 3: 3.182446305284, 4: 2.776445105198, 5: 2.570581835636,
    6: 2.446911851145, 7: 2.364624251593, 8: 2.306004135204, 9: 2.262157162798, 10: 2.228138851986,
    11: 2.200985160092, 12: 2.178812829667, 13: 2.160368656463, 14: 2.144786687918, 15: 2.131449545560,
    16: 2.119905299221, 17: 2.109815577833, 18: 2.100922040241, 19: 2.093024054408, 20: 2.085963447266,
    21: 2.079613844728, 22: 2.073873067904, 23: 2.068657610419, 24: 2.063898561628, 25: 2.059538552753,
    26: 2.055529438643, 27: 2.051830516480, 28: 2.048407141795, 29: 2.045229642133, 30: 2.042272456301
  };
  function tCrit975(df) {
    if (df < 1) return NaN;
    // Fourth-order Cornish-Fisher expansion for integer df >= 31, using the
    // N(0,1) 97.5th quantile and Student-t correction coefficients. Check
    // against actually executed R stats::qt(.975, df) in oracle-tests;
    // unlike the previous truncated formula, terms through df^-4 remain.
    if (df > 30) {
      const v = df, v2 = v * v;
      return 1.959963984540054 + 2.372271230298562/v
        + 2.8224986157396112/v2
        + 2.555849679507722/(v2*v)
        + 1.5895340533938225/(v2*v2);
    }
    return T_975[Math.round(df)] || 1.96;
  }

  function effectAndVar(tEa, tNa, cEa, cNa, measure) {
    // Returns {logEff, varLog} on log-RR or log-OR scale.
    if (measure === 'OR') {
      const a = tEa, b = tNa - tEa, c = cEa, d = cNa - cEa;
      const logOR = Math.log((a * d) / (b * c));
      const v = 1 / a + 1 / b + 1 / c + 1 / d;
      return { logEff: logOR, varLog: v };
    }
    // default RR (Greenland-Robins variance)
    const logRR = Math.log((tEa / tNa) / (cEa / cNa));
    const v = 1 / tEa - 1 / tNa + 1 / cEa - 1 / cNa;
    return { logEff: logRR, varLog: v };
  }

  function pool2x2(trials, opts) {
    opts = opts || {};
    // Only RR and OR are implemented for raw binomial 2x2 counts.
    // Never silently present an RR as a requested HR/RD or another estimand.
    const measureInput = opts.measure == null ? 'RR' : opts.measure;
    const tau2Input = opts.tau2Method == null ? 'PM' : opts.tau2Method;
    const measure = typeof measureInput === 'string' ? measureInput.toUpperCase() : '';
    const tau2Method = typeof tau2Input === 'string' ? tau2Input.toUpperCase() : '';
    const haldane = opts.haldane != null ? opts.haldane : 0.5;
    const out = { k_used: 0, perStudy: [], excludedStudies: [], measure, opts };
    // This inverse-variance route requires a strictly positive correction:
    // zero would leave boundary cells uncomputable and silently remove trials.
    // Do not coerce numeric-looking strings or booleans (JS "+" concatenates).
    if (typeof haldane !== 'number' || !Number.isFinite(haldane) || haldane <= 0) {
      out.error = 'Invalid zero-cell continuity correction; expected a finite positive number'
        + ' (pooling refused rather than silently omitting boundary studies)';
      return out;
    }
    if (measure !== 'RR' && measure !== 'OR') {
      out.error = 'Unsupported raw 2x2 effect measure ' + JSON.stringify(measureInput)
        + '; expected RR or OR (HR requires time-to-event evidence)';
      return out;
    }
    // REML and other methods are available in other engines, not in this
    // PM/DL-only module. Do not claim the requested estimator was executed.
    if (tau2Method !== 'PM' && tau2Method !== 'DL') {
      out.error = 'Unsupported between-study variance method ' + JSON.stringify(tau2Input)
        + '; expected PM or DL in PairwisePool';
      return out;
    }

    // Raw 2x2 pooling must not silently drop studies with missing or
    // impossible summary data. Keep such studies in the *review* and resolve
    // their eligibility before pooling (Cochrane Handbook, section 10.12).
    const countFields = ['tE', 'tN', 'cE', 'cN'];
    if (!Array.isArray(trials)) {
      out.error = 'Invalid raw 2x2 input; expected an array of trials (pooling refused)';
      return out;
    }
    const incompleteIndex = trials.findIndex(t =>
      t == null || typeof t !== 'object' || Array.isArray(t) ||
      countFields.some(key => t[key] == null));
    if (incompleteIndex !== -1) {
      out.error = 'Missing raw 2x2 counts or malformed record in trial '
        + (incompleteIndex + 1) + '; pooling refused (requires tE, tN, cE, cN)';
      return out;
    }
    // Raw binomial counts must be exact non-fractional integers.
    const badCountIndex = trials.findIndex(t =>
      countFields.some(key => !Number.isSafeInteger(t[key])));
    if (badCountIndex !== -1) {
      out.error = 'Non-integer or unsafe 2x2 raw count in trial ' + (badCountIndex + 1)
        + '; pooling refused (requires exact integer event and arm counts)';
      return out;
    }

    // Impossible 2x2 tables must not disappear from the analysis silently.
    // The established double-zero exclusion policy is separate (below).
    const badBoundsIndex = trials.findIndex(t =>
      t.tN <= 0 || t.cN <= 0 || t.tE < 0 || t.cE < 0 ||
      t.tE > t.tN || t.cE > t.cN);
    if (badBoundsIndex !== -1) {
      out.error = 'Impossible raw 2x2 counts in trial ' + (badBoundsIndex + 1)
        + '; pooling refused (requires positive denominators and 0 <= events <= total)';
      return out;
    }

    // Comparisons from one registered trial may share participants/arms.
    // This simple inverse-variance model has no multi-arm covariance handling;
    // do not silently double-count an NCT identifier (Cochrane ch. 6 s 6.2.9,
    // ch. 23 s 23.3.4). Manual resolution/aggregation is required.
    const seenNct = new Map();
    for (let i = 0; i < trials.length; i++) {
      const raw = trials[i].nct;
      if (raw == null || raw === '') continue;
      if (typeof raw !== 'string' || !raw.trim()) {
        out.error = 'Invalid NCT identifier in trial ' + (i + 1)
          + '; pooling refused (study identity must be a non-empty string)';
        return out;
      }
      const id = raw.trim().toUpperCase();
      if (seenNct.has(id)) {
        out.error = 'Repeated NCT study identifier ' + id + ' in trials '
          + seenNct.get(id) + ' and ' + (i + 1)
          + '; pooling refused pending multi-arm/shared-participant assessment';
        return out;
      }
      seenNct.set(id, i + 1);
    }

    // R stats::qnorm(0.975): full-precision two-sided 95% normal quantile.
    // This is for study-level Wald intervals, NOT pooled t(k-1) HKSJ CIs.
    const zStudy = 1.959963984540054;
    const yi = [], vi = [], names = [], origIdx = [];
    let unrepresentableTrial = -1;
    trials.forEach(function (t, idx) {
      const tE = t.tE, tN = t.tN, cE = t.cE, cN = t.cN;
      if (tE == null || tN == null || cE == null || cN == null) return;
      if (tN <= 0 || cN <= 0) return;
      if (!isFinite(tE) || !isFinite(tN) || !isFinite(cE) || !isFinite(cN)) return;
      if (tE > tN || cE > cN || tE < 0 || cE < 0) return; // GRIM violation
      if (tE === tN && cE === cN) {
        // Both arms have 100% events. As with neither arm having an event,
        // these data do not identify a relative effect (Cochrane Handbook
        // chapter 6, section 6.4.1.2). Do not manufacture an RR/OR and
        // inverse-variance weight by applying an arbitrary 0.5 correction.
        out.excludedStudies.push({
          trial_index: idx + 1,
          name: t.name || ('Study ' + (idx + 1)),
          reason: 'BOTH_ARMS_ALL_EVENTS'
        });
        return;
      }
      if (tE === 0 && cE === 0) {
        // Neither-arm events give no direction/magnitude for RR or OR. Preserve
        // the established exclusion policy but disclose the study and reason.
        // This is an analysis exclusion, not removal from the evidence review.
        out.excludedStudies.push({
          trial_index: idx + 1,
          name: t.name || ('Study ' + (idx + 1)),
          reason: 'DOUBLE_ZERO_EVENTS'
        });
        return;
      }
      let tEa = tE, tNa = tN, cEa = cE, cNa = cN;
      if (tE === 0 || cE === 0 || tE === tN || cE === cN) {
        tEa = tE + haldane; tNa = tN + 2 * haldane;
        cEa = cE + haldane; cNa = cN + 2 * haldane;
      }
      const e = effectAndVar(tEa, tNa, cEa, cNa, measure);
      if (!Number.isFinite(e.logEff) || !Number.isFinite(e.varLog) || e.varLog <= 0) {
        // Never silently remove a study because double-precision arithmetic
        // cannot represent its log effect or strictly positive variance.
        unrepresentableTrial = idx + 1;
        return;
      }
      yi.push(e.logEff);
      vi.push(e.varLog);
      names.push(t.name || ('Study ' + (idx + 1)));
      origIdx.push(idx);
      out.perStudy.push({
        name: t.name || ('Study ' + (idx + 1)),
        eff: Math.exp(e.logEff),
        ci_lo: Math.exp(e.logEff - zStudy * Math.sqrt(e.varLog)),
        ci_hi: Math.exp(e.logEff + zStudy * Math.sqrt(e.varLog)),
        weight: null  // filled below
      });
    });

    if (unrepresentableTrial !== -1) {
      out.error = 'Numerically unrepresentable 2x2 log effect or non-positive variance in trial '
        + unrepresentableTrial + '; entire pool refused rather than silently omitting a study';
      out.perStudy = [];
      out.excludedStudies = [];
      return out;
    }

    const k = yi.length;
    out.k_used = k;
    if (k < 2) {
      out.error = 'Insufficient trials (k<2 with usable raw counts)';
      return out;
    }

    // Fixed-effect for Q
    const wFE = vi.map(v => 1 / v);
    const sumWFE = wFE.reduce((a, b) => a + b, 0);
    const muFE = yi.reduce((s, y, i) => s + wFE[i] * y, 0) / sumWFE;
    const Q = yi.reduce((s, y, i) => s + wFE[i] * Math.pow(y - muFE, 2), 0);
    const df = k - 1;

    // tau^2 — Paule-Mandel by default (robust for small k); DL via opts.tau2Method='DL'.
    const tau2 = tau2Method === 'DL'
      ? tau2DL(wFE, sumWFE, Q, df)
      : tau2PM(yi, vi, df);

    // Random-effects pool
    const wRE = vi.map(v => 1 / (v + tau2));
    const sumWRE = wRE.reduce((a, b) => a + b, 0);
    const muRE = yi.reduce((s, y, i) => s + wRE[i] * y, 0) / sumWRE;
    const seMu = Math.sqrt(1 / sumWRE);

    // HKSJ floor + scaling. The Hartung-Knapp-Sidik-Jonkman statistic uses
    // RANDOM-effects weights and the RE pooled mean — q* = (1/df)·Σ wRE_i·(y_i−muRE)²
    // — NOT the fixed-effect Q/df. Using FE Q/df overstates the multiplier whenever
    // tau2>0 (CIs come out ~3x too wide vs metafor test="knha"). Floored at
    // max(1, q*) per the HKSJ-floor rule; matches the bit-exact in-page computeCore.
    let qStar = 0;
    for (let i = 0; i < k; i++) { qStar += wRE[i] * Math.pow(yi[i] - muRE, 2); }
    qStar /= df;
    const hksjFactor = Math.max(1, qStar);
    const seMuHKSJ = seMu * Math.sqrt(hksjFactor);

    const tCi = tCrit975(df);
    const ciLo = muRE - tCi * seMuHKSJ;
    const ciHi = muRE + tCi * seMuHKSJ;

    // Cochrane Handbook v6.5: PI uses t_{k-1} × √(τ² + SE_µ²)
    let piLo = NaN, piHi = NaN;
    if (k >= 3) {
      const seP = Math.sqrt(tau2 + seMu * seMu);
      const tPi = tCrit975(df);
      piLo = muRE - tPi * seP;
      piHi = muRE + tPi * seP;
    }

    // I^2 (Higgins-Thompson)
    const I2 = Math.max(0, (Q - df) / Q) * 100;

    // Per-study weights (RE)
    out.perStudy.forEach(function (s, i) {
      s.weight = (wRE[i] / sumWRE) * 100;
    });

    out.mu_log = muRE;
    out.mu = Math.exp(muRE);
    out.ci_lo = Math.exp(ciLo);
    out.ci_hi = Math.exp(ciHi);
    out.pi_lo = isFinite(piLo) ? Math.exp(piLo) : NaN;
    out.pi_hi = isFinite(piHi) ? Math.exp(piHi) : NaN;
    out.tau2 = tau2;
    out.tau2Method = tau2Method;
    out.Q = Q;
    out.I2 = I2;
    out.df = df;
    out.hksjFactor = hksjFactor;

    // PI gap flag (Cochrane fragility): CI excludes null but PI doesn't.
    const ciExcludes = (out.ci_hi < 1.0) || (out.ci_lo > 1.0);
    const piIncludes = isFinite(out.pi_lo) && (out.pi_lo <= 1.0 && out.pi_hi >= 1.0);
    out.piGap = (ciExcludes && piIncludes && k >= 3);

    return out;
  }

  // -------------------------- forest plot SVG --------------------------

  function fmtRatio(x) {
    if (!isFinite(x)) return '—';
    return x >= 10 ? x.toFixed(1) : x.toFixed(2);
  }

  function renderForest(container, res, opts) {
    if (typeof container === 'string') container = document.getElementById(container);
    if (!container) return;
    container.innerHTML = '';
    if (res.error) {
      container.innerHTML = '<div style="color:#f87171;font-size:12px;padding:1em;">' + res.error + '</div>';
      return;
    }
    opts = opts || {};
    const referenceEffect = opts.referenceEffect; // optional published value to overlay

    const k = res.perStudy.length;
    const W = opts.width || 720;
    const rowH = 28;
    const headH = 40, footH = 90; // foot extended for PI band + ref line
    const H = headH + rowH * (k + 1) + footH;

    // Compute log-scale x range from per-study CIs + pooled CI/PI
    let lo = Math.min.apply(null, res.perStudy.map(s => s.ci_lo).concat([res.ci_lo, res.pi_lo].filter(isFinite)));
    let hi = Math.max.apply(null, res.perStudy.map(s => s.ci_hi).concat([res.ci_hi, res.pi_hi].filter(isFinite)));
    lo = Math.max(0.01, lo * 0.9);
    hi = hi * 1.1;
    const xL = Math.log(lo), xH = Math.log(hi);

    const padL = 240, padR = 130;
    const plotW = W - padL - padR;
    const xScale = v => padL + ((Math.log(v) - xL) / (xH - xL)) * plotW;

    // SVG begins
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    svg.setAttribute('width', '100%');
    svg.setAttribute('style', 'background:transparent;font-family:ui-sans-serif,system-ui,sans-serif;');

    function el(tag, attrs, text) {
      const e = document.createElementNS(svgNS, tag);
      Object.keys(attrs || {}).forEach(k => e.setAttribute(k, attrs[k]));
      if (text != null) e.textContent = text;
      return e;
    }

    // Headers
    svg.appendChild(el('text', { x: 8, y: 22, fill: '#94a3b8', 'font-size': 12, 'font-weight': 600 }, 'Trial'));
    svg.appendChild(el('text', { x: padL + plotW / 2, y: 22, fill: '#94a3b8', 'font-size': 12, 'font-weight': 600, 'text-anchor': 'middle' },
      res.measure + ' (95% CI) [random-effects + HKSJ]'));
    svg.appendChild(el('text', { x: W - 8, y: 22, fill: '#94a3b8', 'font-size': 12, 'font-weight': 600, 'text-anchor': 'end' }, 'Weight'));

    // Null line
    const xNull = xScale(1.0);
    svg.appendChild(el('line', {
      x1: xNull, x2: xNull, y1: headH - 6, y2: H - footH + 6,
      stroke: '#475569', 'stroke-width': 1, 'stroke-dasharray': '3,3'
    }));

    // Optional reference effect (published HR) line in gold
    if (referenceEffect != null && isFinite(referenceEffect) && referenceEffect > 0) {
      const xRef = xScale(referenceEffect);
      svg.appendChild(el('line', {
        x1: xRef, x2: xRef, y1: headH - 6, y2: H - footH + 6,
        stroke: '#fbbf24', 'stroke-width': 1.2, 'stroke-dasharray': '6,3'
      }));
      svg.appendChild(el('text', {
        x: xRef + 4, y: headH - 8,
        fill: '#fbbf24', 'font-size': 9
      }, 'published ' + fmtRatio(referenceEffect)));
    }

    // Per-study rows
    res.perStudy.forEach(function (s, i) {
      const y = headH + rowH * (i + 1);
      svg.appendChild(el('text', { x: 8, y: y + 4, fill: '#cbd5e1', 'font-size': 11 }, s.name.length > 35 ? s.name.slice(0, 33) + '…' : s.name));
      svg.appendChild(el('line', {
        x1: xScale(s.ci_lo), x2: xScale(s.ci_hi),
        y1: y, y2: y, stroke: '#60a5fa', 'stroke-width': 1.6
      }));
      const sz = Math.max(3, Math.min(11, Math.sqrt(s.weight)));
      svg.appendChild(el('rect', {
        x: xScale(s.eff) - sz / 2, y: y - sz / 2,
        width: sz, height: sz, fill: '#3b82f6'
      }));
      svg.appendChild(el('text', {
        x: padL + plotW + 8, y: y + 4,
        fill: '#94a3b8', 'font-size': 10
      }, fmtRatio(s.eff) + ' (' + fmtRatio(s.ci_lo) + '–' + fmtRatio(s.ci_hi) + ')'));
      svg.appendChild(el('text', {
        x: W - 8, y: y + 4,
        fill: '#64748b', 'font-size': 10, 'text-anchor': 'end'
      }, s.weight.toFixed(1) + '%'));
    });

    // Pooled diamond
    const yPool = headH + rowH * (k + 1) + 8;
    const xL_p = xScale(res.ci_lo), xR_p = xScale(res.ci_hi), xC_p = xScale(res.mu);
    svg.appendChild(el('polygon', {
      points: [xL_p, yPool, xC_p, yPool - 8, xR_p, yPool, xC_p, yPool + 8].join(','),
      fill: '#22d3ee', stroke: '#0891b2', 'stroke-width': 1
    }));
    svg.appendChild(el('text', { x: 8, y: yPool + 4, fill: '#22d3ee', 'font-size': 11, 'font-weight': 600 },
      'POOLED (k=' + res.k_used + ', τ²=' + res.tau2.toFixed(3) + ', I²=' + res.I2.toFixed(0) + '%)'));
    svg.appendChild(el('text', {
      x: padL + plotW + 8, y: yPool + 4,
      fill: '#22d3ee', 'font-size': 10, 'font-weight': 600
    }, fmtRatio(res.mu) + ' (' + fmtRatio(res.ci_lo) + '–' + fmtRatio(res.ci_hi) + ')'));

    // PI band as horizontal range
    if (isFinite(res.pi_lo)) {
      const yPI = yPool + 24;
      svg.appendChild(el('line', {
        x1: xScale(res.pi_lo), x2: xScale(res.pi_hi),
        y1: yPI, y2: yPI,
        stroke: '#f97316', 'stroke-width': 2, 'stroke-dasharray': '4,2'
      }));
      svg.appendChild(el('text', {
        x: 8, y: yPI + 4, fill: '#f97316', 'font-size': 10, 'font-weight': 600
      }, '95% PI (Cochrane v6.5)'));
      svg.appendChild(el('text', {
        x: padL + plotW + 8, y: yPI + 4, fill: '#f97316', 'font-size': 10
      }, fmtRatio(res.pi_lo) + '–' + fmtRatio(res.pi_hi)));
      if (res.piGap) {
        svg.appendChild(el('text', {
          x: 8, y: yPI + 22, fill: '#f87171', 'font-size': 10, 'font-weight': 600
        }, '⚠ PI gap: CI excludes null but PI does not — heterogeneity-fragile'));
      }
    }

    container.appendChild(svg);
  }

  global.PairwisePool = { pool2x2, renderForest };
})(typeof window !== 'undefined' ? window : globalThis);
