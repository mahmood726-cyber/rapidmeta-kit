// js_engine.js — the RapidMeta dashboard's OWN pooling engine, extracted VERBATIM
// from template/base_dupilumab_copd.html (functions binaryEffect, hrFromPublished,
// mdFromCont, pauleMandelTau2, poolWith). This is the number the app DISPLAYS.
//
// It exists so the clean-room reproduction test compares the Python harness
// (rmharness/pooling.py) against the app's ACTUAL browser engine — two
// independent language implementations — not against itself. If they agree, the
// harness genuinely reproduces the app's number.
//
// Node >=14, zero dependencies, no network. Usage:
//   node js_engine.js <config-or-bundle.json> [measure] [method]
// Prints JSON: { measure, method, k, estimate_log, se, ci_log, tau2, ... }
'use strict';

function toF(x) { const n = Number(x); return Number.isFinite(n) ? n : null; }

// --- VERBATIM from base_dupilumab_copd.html:43667 -------------------------
function binaryEffect(d, measure) {
  var tE = toF(d.tE), tN = toF(d.tN), cE = toF(d.cE), cN = toF(d.cN);
  if (tE == null || tN == null || cE == null || cN == null) return null;
  if (tN <= 0 || cN <= 0) return null;
  var tNonE = tN - tE, cNonE = cN - cE;
  if (tNonE < 0 || cNonE < 0) return null;
  var add = (tE === 0 || tNonE === 0 || cE === 0 || cNonE === 0) ? 0.5 : 0;
  var a = tE + add, b = tNonE + add, c = cE + add, e = cNonE + add;
  if (a <= 0 || b <= 0 || c <= 0 || e <= 0) return null;
  var y, v;
  if (measure === 'RR') {
    var pt = a / (a + b), pc = c / (c + e);
    if (pt <= 0 || pc <= 0) return null;
    y = Math.log(pt / pc);
    v = (1 / a) - (1 / (a + b)) + (1 / c) - (1 / (c + e));
  } else {
    y = Math.log(a * e / (b * c));
    v = 1 / a + 1 / b + 1 / c + 1 / e;
  }
  if (!Number.isFinite(y) || !Number.isFinite(v) || v <= 0) return null;
  return { y: y, v: v };
}

// --- VERBATIM from base_dupilumab_copd.html:43691 -------------------------
function hrFromPublished(d) {
  var hr = toF(d.publishedHR), lo = toF(d.hrLCI), hi = toF(d.hrUCI);
  if (hr == null || lo == null || hi == null) return null;
  if (hr <= 0 || lo <= 0 || hi <= 0) return null;
  var y = Math.log(hr);
  var se = (Math.log(hi) - Math.log(lo)) / (2 * 1.959964);
  if (!Number.isFinite(se) || se <= 0) return null;
  return { y: y, v: se * se };
}

// --- VERBATIM from base_dupilumab_copd.html:43700 -------------------------
function mdFromCont(d) {
  var tMean = toF(d.tMean), tSD = toF(d.tSD), tN = toF(d.tN);
  var cMean = toF(d.cMean), cSD = toF(d.cSD), cN = toF(d.cN);
  if (tMean == null || tSD == null || tN == null || cMean == null || cSD == null || cN == null) return null;
  if (tN <= 0 || cN <= 0 || tSD < 0 || cSD < 0) return null;
  var v = (tSD * tSD) / tN + (cSD * cSD) / cN;
  if (!Number.isFinite(v) || v <= 0) return null;
  return { y: tMean - cMean, v: v };
}

// --- VERBATIM from base_dupilumab_copd.html:43729 -------------------------
function pauleMandelTau2(y, v) {
  var k = y.length;
  if (k < 2) return 0;
  var tau2 = 0;
  var target = k - 1;
  for (var iter = 0; iter < 200; iter++) {
    var w = v.map(function (vi) { return 1 / (vi + tau2); });
    var sumW = w.reduce(function (a, b) { return a + b; }, 0);
    if (!(sumW > 0)) break;
    var yBar = 0;
    for (var i = 0; i < k; i++) yBar += y[i] * w[i];
    yBar /= sumW;
    var Q = 0;
    for (var j = 0; j < k; j++) { var d = y[j] - yBar; Q += w[j] * d * d; }
    var diff = Q - target;
    if (Math.abs(diff) < 1e-5) break;
    var slope = 0;
    for (var m = 0; m < k; m++) { var dm = y[m] - yBar; slope += -w[m] * w[m] * dm * dm; }
    if (!Number.isFinite(slope) || Math.abs(slope) < 1e-14) break;
    var t2new = Math.max(0, tau2 + diff / slope);
    if (!Number.isFinite(t2new)) break;
    if (Math.abs(t2new - tau2) < 1e-9) { tau2 = t2new; break; }
    tau2 = t2new;
  }
  return tau2;
}

// --- VERBATIM from base_dupilumab_copd.html:43756 -------------------------
function poolWith(y, v, tau2, confLevel) {
  var z = 1.959964;
  if (confLevel && confLevel > 0 && confLevel < 1) {
    if (Math.abs(confLevel - 0.95) < 0.001) z = 1.959964;
    else if (Math.abs(confLevel - 0.90) < 0.001) z = 1.644854;
    else if (Math.abs(confLevel - 0.99) < 0.001) z = 2.575829;
  }
  var k = y.length;
  var w = v.map(function (vi) { return 1 / (vi + tau2); });
  var sumW = w.reduce(function (a, b) { return a + b; }, 0);
  var effect = 0;
  for (var i = 0; i < k; i++) effect += y[i] * w[i];
  effect /= sumW;
  var se = 1 / Math.sqrt(sumW);
  return { effect: effect, se: se, lo: effect - z * se, hi: effect + z * se };
}

// --- driver: mirror computeREML()'s per-trial effect selection ------------
function effectForTrial(t, measure) {
  var d = (t.data && typeof t.data === 'object') ? t.data : t; // accept flat or {data:...}
  if (measure === 'MD' || measure === 'SMD') return mdFromCont(d);
  if (measure === 'HR') return hrFromPublished(d) || binaryEffect(d, 'OR');
  var e = binaryEffect(d, measure);
  if (!e) e = hrFromPublished(d);
  return e;
}

function _effects(trials, measure) {
  var y = [], v = [], used = [];
  trials.forEach(function (t) {
    var e = effectForTrial(t, measure);
    if (e && Number.isFinite(e.y) && Number.isFinite(e.v) && e.v > 0) {
      y.push(e.y); v.push(e.v); used.push({ label: t.name || t.nct || '', yi: e.y, vi: e.v });
    }
  });
  return { y: y, v: v, used: used };
}

// --- REML tau2, VERBATIM Fisher scoring from base_dupilumab_copd.html:6183-6205
function remlTau2(yi, vi) {
  var k = yi.length;
  if (k < 2) return 0;
  // DL warm start (matches the app: tau2_reml = tau2_dl)
  var wf = vi.map(function (v) { return 1 / v; });
  var sWf = wf.reduce(function (a, b) { return a + b; }, 0);
  var sWf2 = wf.reduce(function (a, w) { return a + w * w; }, 0);
  var muf = 0; for (var i = 0; i < k; i++) muf += wf[i] * yi[i]; muf /= sWf;
  var Q = 0; for (var j = 0; j < k; j++) { var dq = yi[j] - muf; Q += wf[j] * dq * dq; }
  var df = k - 1;
  var tau2_reml = (Q > df) ? (Q - df) / (sWf - sWf2 / sWf) : 0;
  for (var it = 0; it < 100; it++) {
    var w = vi.map(function (v) { return 1 / (v + tau2_reml); });
    var sW = w.reduce(function (a, b) { return a + b; }, 0);
    var mu = w.reduce(function (a, wi, i2) { return a + wi * yi[i2]; }, 0) / sW;
    var sW2 = w.reduce(function (a, wi) { return a + wi * wi; }, 0);
    var sW3 = w.reduce(function (a, wi) { return a + wi * wi * wi; }, 0);
    var trP = sW - sW2 / sW;
    var yP2y = w.reduce(function (a, wi, i3) { return a + wi * wi * Math.pow(yi[i3] - mu, 2); }, 0);
    var trP2 = sW2 - 2 * sW3 / sW + sW2 * sW2 / (sW * sW);
    if (trP2 < 1e-15) break;
    var delta = (yP2y - trP) / trP2;
    var neu = Math.max(0, tau2_reml + delta);
    if (Math.abs(neu - tau2_reml) < 1e-10) { tau2_reml = neu; break; }
    tau2_reml = neu;
  }
  return tau2_reml;
}

// The app's HEADLINE pooled number (forest-plot diamond): REML random-effects,
// mirrors base_dupilumab_copd.html:6181-6285 exactly. This is "our number".
function poolHeadline(trials, measure, confLevel) {
  var e = _effects(trials, measure);
  var y = e.y, v = e.v, k = y.length;
  if (k < 2) throw new Error('need k>=2 poolable trials, got ' + k);
  var z = 1.959964; // app default zCrit at 95%
  // Q / I2 from fixed-effect weights (matches app)
  var wf = v.map(function (vi) { return 1 / vi; });
  var sW = wf.reduce(function (a, b) { return a + b; }, 0);
  var sWY = 0, sW_y2 = 0; for (var i = 0; i < k; i++) { sWY += wf[i] * y[i]; sW_y2 += wf[i] * y[i] * y[i]; }
  var Q = Math.max(0, sW_y2 - (sWY * sWY) / sW);
  var df = k - 1;
  var I2 = (Q > df) ? ((Q - df) / Q) * 100 : 0;
  var tau2 = remlTau2(y, v);
  // random-effects pooling with REML weights
  var sWR = 0, sWRY = 0;
  for (var j = 0; j < k; j++) { var wr = 1 / (v[j] + tau2); sWR += wr; sWRY += wr * y[j]; }
  var pMD = sWRY / sWR;
  var pSE = Math.sqrt(1 / sWR);
  var lci = pMD - z * pSE, uci = pMD + z * pSE;
  var isRatio = (measure === 'OR' || measure === 'RR' || measure === 'HR');
  return {
    engine: 'RapidMeta JS main engine (REML random-effects), verbatim from base_dupilumab_copd.html:6181-6285',
    measure: measure, method: 'REML', k: k,
    estimate_log: pMD, se: pSE, ci_log: [lci, uci],
    tau2: tau2, Q: Q, df: df, I2_percent: I2,
    estimate_ratio: isRatio ? Math.exp(pMD) : null,
    ci_ratio: isRatio ? [Math.exp(lci), Math.exp(uci)] : null,
    per_trial: e.used
  };
}

// The app's PM *sensitivity* retrofit (computeREML). NOTE: this path has a
// Paule-Mandel Newton sign bug (tau2 + diff/slope) that diverges when Q<k-1;
// exposed here so the harness can demonstrate catching it. Not the headline.
function poolPM(trials, measure, confLevel) {
  var e = _effects(trials, measure);
  var y = e.y, v = e.v, k = y.length;
  if (k < 2) throw new Error('need k>=2 poolable trials, got ' + k);
  var tau2 = pauleMandelTau2(y, v);
  var p = poolWith(y, v, tau2, confLevel || 0.95);
  var isRatio = (measure === 'OR' || measure === 'RR' || measure === 'HR');
  return {
    engine: 'RapidMeta JS PM sensitivity retrofit (computeREML), verbatim',
    measure: measure, method: 'PM', k: k,
    estimate_log: p.effect, se: p.se, ci_log: [p.lo, p.hi],
    tau2: tau2, df: k - 1,
    estimate_ratio: isRatio ? Math.exp(p.effect) : null,
    ci_ratio: isRatio ? [Math.exp(p.lo), Math.exp(p.hi)] : null,
    per_trial: e.used
  };
}

if (require.main === module) {
  var fs = require('fs');
  var path = process.argv[2];
  var measure = process.argv[3] || null;
  if (!path) { console.error('usage: node js_engine.js <config.json> [measure] [method]'); process.exit(2); }
  var cfg = JSON.parse(fs.readFileSync(path, 'utf8'));
  var trials = cfg.trials || cfg;
  if (!measure) {
    // default measure: RR if 2x2 present, else HR if published effect present
    var t0 = trials[0] || {};
    var d0 = t0.data || t0;
    measure = (d0.tE != null && d0.cE != null) ? 'RR' : (d0.publishedHR != null ? 'HR' : 'OR');
  }
  var mode = process.argv[4] || 'headline';
  var out = (mode === 'pm') ? poolPM(trials, measure, 0.95) : poolHeadline(trials, measure, 0.95);
  process.stdout.write(JSON.stringify(out, null, 2) + '\n');
}

module.exports = { binaryEffect, hrFromPublished, mdFromCont, pauleMandelTau2, poolWith, remlTau2, poolHeadline, poolPM };
