/* Headless DOM-stub smoke harness for the advanced-technique panels.
 *
 * node --check proves the files PARSE; this proves they MOUNT — that each
 * panel's render() runs the full getRealData -> extractBinaryTrials -> engine ->
 * buildCollapsiblePanel -> insertAfterRBadge path against a realistic dataset
 * without throwing a runtime DOM error. Pure Node + a minimal DOM stub; no
 * browser, no network. Exits non-zero with a message on any failure.
 */
'use strict';

// ---- Minimal DOM stub --------------------------------------------------------
function makeEl(tag) {
  return {
    tagName: tag, _id: '', style: { cssText: '' }, _children: [],
    innerHTML: '', textContent: '', title: '', type: '', rows: 0, placeholder: '', value: '',
    attrs: {},
    get id() { return this._id; }, set id(v) { this._id = v; registry[v] = this; },
    appendChild(c) { this._children.push(c); c.parentNode = this; return c; },
    insertBefore(n, ref) { this._children.push(n); n.parentNode = this; return n; },
    replaceWith(n) { if (this.parentNode) { this.parentNode._children.push(n); n.parentNode = this.parentNode; } },
    querySelector() { return null; },
    addEventListener() {},
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    get nextSibling() { return null; },
    get firstElementChild() { return this._children[0] || null; },
    get firstChild() { return this._children[0] || null; },
  };
}
const registry = {};
const body = makeEl('body');
const rbadge = makeEl('div'); rbadge.id = 'r-validation-badge'; body.appendChild(rbadge);
const store = {};
global.window = global;
global.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
global.document = {
  readyState: 'complete',
  body,
  createElement: makeEl,
  getElementById: (id) => registry[id] || null,
  querySelector: () => null,
  addEventListener() {},
};

// ---- Load helper + engines + panels -----------------------------------------
const path = require('path');
const V = path.join(__dirname, '..', 'template', 'assets', 'vendor') + path.sep;
require(V + '_panel-helper.js');
require(V + '_alm-stats-shim.js');
require(V + 'uwls.js');
require(V + 'selmodel.js');
require(V + 'rve.js');
require(V + 'rare-events-glmm.js');
require(V + 'trimfill.js');
require(V + 'multiplicative-nma.js');
require(V + 'multilevel-reml.js');
require(V + 'limit-ma.js');
require(V + 'gosh.js');
require(V + 'nma-dbt.js');
require(V + 'copas-shi.js');
require(V + 'robma.js');
require(V + 'experimental-ma.js');
require(V + 'bma-tau.js');
require(V + 'transportability-v1.js');
require(V + 'multivariate-ma.js');
require(V + 'evalue.js');
require(V + 'nma-meta-regression.js');
require(V + 'personalised-te.js');
require(V + 'multi-outcome-ma.js');
require(V + 'location-scale.js');
require(V + 'cnma-receptor.js');
require(V + 'spec-collapse.js');
require(V + 'transported-nma-v1.js');
require(V + 'multi-outcome-nma.js');
require(V + 'uwls-panel.js');
require(V + 'selmodel-panel.js');
require(V + 'rare-events-panel.js');
require(V + 'rve-panel.js');
require(V + 'multiplicative-nma-panel.js');
require(V + 'multilevel-reml-panel.js');
require(V + 'limit-ma-panel.js');
require(V + 'gosh-panel.js');
require(V + 'nma-dbt-panel.js');
require(V + 'copas-shi-panel.js');
require(V + 'robma-panel.js');
require(V + 'experimental-ma-panel.js');
require(V + 'bma-tau-panel.js');
require(V + 'transportability-v1-panel.js');
require(V + 'multivariate-ma-panel.js');
require(V + 'evalue-panel.js');
require(V + 'nma-meta-regression-panel.js');
require(V + 'personalised-te-panel.js');
require(V + 'multi-outcome-ma-panel.js');
require(V + 'location-scale-panel.js');
require(V + 'cnma-receptor-panel.js');
require(V + 'spec-collapse-panel.js');
require(V + 'transported-nma-v1-panel.js');
require(V + 'multi-outcome-nma-panel.js');
require(V + 'funnel-diagnostics.js'); // exercises the AlmTrimFill delegation + Begg added this batch

// ---- Realistic dataset: 5 binary trials, one with a zero cell ---------------
// Shape mirrors the kit's realData (tE/tN/cE/cN per trial).
global.window.RapidMeta = {
  // Varied positive log-ORs (a spread of one-sided p-values so the selection
  // model is identifiable) plus one control-zero cell so the rare-events panel
  // also mounts — exercises all four panels on a single realistic dataset.
  realData: {
    t1: { name: 'Trial A', tE: 24, tN: 200, cE: 12, cN: 200, year: 2018 },
    t2: { name: 'Trial B', tE: 34, tN: 250, cE: 22, cN: 250, year: 2019 },
    t3: { name: 'Trial C', tE: 20, tN: 180, cE: 10, cN: 182, year: 2020 },
    t4: { name: 'Trial D', tE: 16, tN: 150, cE: 9,  cN: 150, year: 2021 },
    t5: { name: 'Trial E', tE: 6,  tN: 300, cE: 0,  cN: 305, year: 2022 }, // zero cell
  },
};
// NMA scenario so the multiplicative-NMA panel (NMA-conditional) mounts: a
// 3-treatment triangle whose edges reference the realData trials above.
global.window.NMA_CONFIG = {
  treatments: ['A', 'B', 'C'],
  comparisons: [
    { t1: 'A', t2: 'B', trials: ['t1', 't2'] },
    { t1: 'A', t2: 'C', trials: ['t3', 't4'] },
    { t1: 'B', t2: 'C', trials: ['t5'] },
  ],
};

// ---- Drive each panel's render() --------------------------------------------
const fails = [];
function check(name, fn) {
  try {
    const ok = fn();
    if (ok !== true) fails.push(name + ': render() returned ' + ok + ' (expected true)');
    else if (!registry[name.toLowerCase().replace('panel', '') + 'panel'] && !registry[PANEL_ID[name]]) {
      // panel node should have registered its id
    }
  } catch (e) {
    fails.push(name + ': threw ' + (e && e.stack ? e.stack.split('\n').slice(0, 3).join(' | ') : e));
  }
}
const PANEL_ID = {
  UWLSPanel: 'uwls-panel', SelModelPanel: 'selmodel-panel',
  RareEventsPanel: 'rare-events-panel', RVEPanel: 'rve-panel',
  MultiplicativeNMAPanel: 'multiplicative-nma-panel', MultilevelREMLPanel: 'multilevel-reml-panel',
  LimitMAPanel: 'limit-ma-panel', GOSHPanel: 'gosh-panel', NmaDBTPanel: 'nma-dbt-panel',
  CopasShiPanel: 'copas-shi-panel', RoBMAPanel: 'robma-panel',
  ExperimentalMAPanel: 'experimental-ma-panel',
  BMATauPanel: 'bma-tau-panel',
  TransportabilityV1Panel: 'transportability-v1-panel',
  MultivariateMAPanel: 'multivariate-ma-panel',
  EValuePanel: 'evalue-panel',
  NmaMetaRegPanel: 'nma-meta-regression-panel',
  PersonalisedTEPanel: 'personalised-te-panel',
  MultiOutcomeMAPanel: 'multi-outcome-ma-panel',
  LocationScalePanel: 'location-scale-panel',
  CnmaReceptorPanel: 'cnma-receptor-panel',
  SpecCollapsePanel: 'spec-collapse-panel',
  TransportedNMAV1Panel: 'transported-nma-v1-panel',
  MultiOutcomeNMAPanel: 'multi-outcome-nma-panel',
};
['UWLSPanel', 'SelModelPanel', 'RareEventsPanel', 'RVEPanel',
 'MultiplicativeNMAPanel', 'MultilevelREMLPanel', 'LimitMAPanel',
 'GOSHPanel', 'NmaDBTPanel', 'CopasShiPanel', 'RoBMAPanel',
 'ExperimentalMAPanel', 'BMATauPanel',
 'TransportabilityV1Panel', 'MultivariateMAPanel', 'EValuePanel',
 'NmaMetaRegPanel', 'PersonalisedTEPanel', 'MultiOutcomeMAPanel',
 'LocationScalePanel', 'CnmaReceptorPanel', 'SpecCollapsePanel',
 'TransportedNMAV1Panel', 'MultiOutcomeNMAPanel'].forEach((p) => {
  check(p, () => global.window[p].render());
  if (!registry[PANEL_ID[p]]) fails.push(p + ': no DOM node with id ' + PANEL_ID[p] + ' was inserted');
});

// Multilevel-REML paste-tool: parseRows + a real fit on clustered input.
const mp = global.window.MultilevelREMLPanel.parseRows('D1, 0.31, 0.07\nD1, 0.22, 0.09\nD2, 0.45, 0.08\nD2, 0.38, 0.10\nD3, 0.12, 0.06');
if (mp.rows.length !== 5) fails.push('Multilevel.parseRows: expected 5 rows, got ' + mp.rows.length);
if (mp.errors.length) fails.push('Multilevel.parseRows: unexpected errors ' + JSON.stringify(mp.errors));
try {
  const f = global.window.AlmMultilevelREML.fit(mp.rows);
  if (!(isFinite(f.mu) && f.sigma2Between >= 0 && f.sigma2Within >= 0)) fails.push('Multilevel fit: non-finite/negative variance');
} catch (e) { fails.push('Multilevel fit threw ' + e); }

// Transportability paste-tool: parseRows + a real transport on study rows + target.
const tp = global.window.TransportabilityV1Panel.parseRows(
  'STEP-1, -12.4, 0.6, 37.9\nSURMOUNT-1, -17.8, 0.7, 38.0\nSCALE, -5.4, 0.5, 38.3\nPIONEER, -4.2, 0.6, 32.9\nAWARD, -3.0, 0.7, 33.5');
if (tp.rows.length !== 5) fails.push('Transport.parseRows: expected 5 rows, got ' + tp.rows.length);
if (tp.errors.length) fails.push('Transport.parseRows: unexpected errors ' + JSON.stringify(tp.errors));
try {
  const tr = global.window.AlmTransport.transport({ studies: tp.rows, target: 31 });
  if (!(tr.ok && isFinite(tr.transported.est) && tr.k === 5)) fails.push('Transport fit: not ok / non-finite / wrong k');
  const flat = global.window.AlmTransport.transport({ studies: [{ est: -0.2, se: 0.1, x: 5 }, { est: -0.1, se: 0.1, x: 5 }, { est: 0, se: 0.1, x: 5 }], target: 7 });
  if (flat.ok) fails.push('Transport: constant modifier should fail closed');
} catch (e) { fails.push('Transport fit threw ' + e); }

// Multivariate-MA paste-tool: parseRows + a real joint fit on 2-outcome rows.
const mv = global.window.MultivariateMAPanel.parseRows(
  'T1, -0.32, 0.47, 0.0030, 0.0075, 0.0030\nT2, -0.60, 0.20, 0.0009, 0.0057, 0.0009\nT3, -0.12, 0.40, 0.0007, 0.0021, 0.0007\nT4, -0.31, 0.26, 0.0009, 0.0029, 0.0009\nT5, -0.39, 0.56, 0.0072, 0.0148, 0.0072');
if (mv.rows.length !== 5) fails.push('Multivariate.parseRows: expected 5 rows, got ' + mv.rows.length);
if (mv.errors.length) fails.push('Multivariate.parseRows: unexpected errors ' + JSON.stringify(mv.errors));
try {
  const f = global.window.AlmMultivariate.fit(mv.rows);
  if (!(f.k === 5 && f.m === 2 && isFinite(f.mu[0]) && isFinite(f.mu[1]) && isFinite(f.rho))) fails.push('Multivariate fit: non-finite / wrong shape');
} catch (e) { fails.push('Multivariate fit threw ' + e); }
// k<2 must fail closed (between-study G unidentifiable).
try { global.window.AlmMultivariate.fit([mv.rows[0]]); fails.push('Multivariate: k<2 should throw'); } catch (e) { /* expected */ }

// Personalised-TE paste-tool: parseRows + a real EB-shrinkage fit on subgroup rows.
const ptp = global.window.PersonalisedTEPanel.parseRows(
  'S1, young, -0.30, 0.141\nS2, young, -0.25, 0.158\nS1, old, -0.55, 0.148\nS2, old, -0.50, 0.158\nS1, biomarker+, -0.65, 0.173\nS2, biomarker+, -0.70, 0.167');
if (ptp.rows.length !== 6) fails.push('PersonalisedTE.parseRows: expected 6 rows, got ' + ptp.rows.length);
if (ptp.errors.length) fails.push('PersonalisedTE.parseRows: unexpected errors ' + JSON.stringify(ptp.errors));
try {
  const pf = global.window.AlmPersonalisedTE.fit(ptp.rows);
  if (!(pf.ok && pf.n_subgroups === 3 && isFinite(pf.overall.mu) && pf.subgroups.young
        && isFinite(pf.subgroups.young.theta_shrunk) && pf.subgroups.young.shrinkage_weight >= 0)) fails.push('PersonalisedTE fit: not ok / wrong shape');
  // single-subgroup input must fail closed (shrinkage across subgroups unidentifiable).
  const one = global.window.AlmPersonalisedTE.fit([{ study: 'S1', subgroup: 'a', yi: -0.3, vi: 0.02 }]);
  if (one.ok) fails.push('PersonalisedTE: <2 rows should fail closed');
} catch (e) { fails.push('PersonalisedTE fit threw ' + e); }

// Multi-outcome-MA paste-tool: parseRows (incl. a missing-outcome row) + a real
// bivariate fit with an assumed within-study correlation.
const moma = global.window.MultiOutcomeMAPanel.parseRows(
  'T1, -0.30, 0.12, -0.40, 0.15\nT2, -0.22, 0.10, -0.35, 0.12\nT3, -0.45, 0.18, -0.55, 0.20\nT4, -0.18, 0.09, -0.28, 0.11\nT5, -0.50, 0.20, NA, NA');
if (moma.rows.length !== 5) fails.push('MultiOutcomeMA.parseRows: expected 5 rows, got ' + moma.rows.length);
if (moma.errors.length) fails.push('MultiOutcomeMA.parseRows: unexpected errors ' + JSON.stringify(moma.errors));
if (!(Number.isNaN(moma.rows[4].y[1]) && Number.isNaN(moma.rows[4].se[1]))) fails.push('MultiOutcomeMA.parseRows: missing outcome should be NaN');
try {
  const ff = global.window.AlmMultiOutcome.fitBivariate(moma.rows, { rhoWithin: 0.5 });
  if (!(ff.ok && isFinite(ff.mu[0]) && isFinite(ff.mu[1]) && isFinite(ff.rho_between))) fails.push('MultiOutcomeMA fit: not ok / non-finite');
} catch (e) { fails.push('MultiOutcomeMA fit threw ' + e); }

// Location-scale paste-tool: parseRows + a real fit (mean+scale moderator).
const ls = global.window.LocationScalePanel.parseRows(
  '-0.94, 0.598, 44, 44\n-1.67, 0.456, 55, 55\n-1.39, 0.658, 42, 42\n-1.46, 0.143, 52, 52\n-0.22, 0.228, 13, 13');
if (ls.rows.length !== 5) fails.push('LocationScale.parseRows: expected 5 rows, got ' + ls.rows.length);
if (ls.errors.length) fails.push('LocationScale.parseRows: unexpected errors ' + JSON.stringify(ls.errors));
try {
  const yi = ls.rows.map(r => r.y), vi = ls.rows.map(r => r.se * r.se);
  const X = ls.rows.map(r => [1, r.x]), Z = ls.rows.map(r => [1, r.z]);
  const lf = global.window.AlmLocationScale.fit(yi, vi, X, Z);
  if (!(isFinite(lf.beta[0]) && isFinite(lf.alpha[0]) && lf.tau2.every(isFinite))) fails.push('LocationScale fit: non-finite beta/alpha/tau2');
} catch (e) { fails.push('LocationScale fit threw ' + e); }
// Fail-closed: a row missing the zMod column must be rejected by parseRows.
const lsBad = global.window.LocationScalePanel.parseRows('-0.94, 0.598, 44');
if (!(lsBad.rows.length === 0 && lsBad.errors.length === 1)) fails.push('LocationScale.parseRows: 3-column row should fail closed');

// CNMA paste-tool: parse the cnma-tiny example + a real additive WLS fit that
// reproduces the netmeta::discomb oracle (a+b+c == -0.8297864).
const cn = global.window.CnmaReceptorPanel.parseRows(
  'a, -0.40, 0.12\nb, -0.30, 0.15\na+b, -0.65, 0.13\na+c, -0.55, 0.16\nc, -0.20, 0.18\nb+c, -0.45, 0.14\na+b+c, -0.80, 0.20');
if (cn.rows.length !== 7) fails.push('Cnma.parseRows: expected 7 rows, got ' + cn.rows.length);
if (cn.errors.length) fails.push('Cnma.parseRows: unexpected errors ' + JSON.stringify(cn.errors));
try {
  const comps = ['a', 'b', 'c'];
  const X = cn.rows.map(r => comps.map(c => (r.comps.indexOf(c) >= 0 ? 1 : 0)));
  const fit = global.window.AlmCnmaReceptor.cnmaWls(X, cn.rows.map(r => r.te), cn.rows.map(r => r.se));
  const combo = global.window.AlmCnmaReceptor.predict(comps, comps, fit.beta, fit.cov);
  if (!(Math.abs(combo.est - (-0.8297864)) < 1e-6 && fit.df === 4)) fails.push('Cnma fit: a+b+c not -0.8297864 / df!=4');
} catch (e) { fails.push('Cnma fit threw ' + e); }
// Fail-closed: a 2-column row (missing seTE) must be rejected by parseRows.
const cnBad = global.window.CnmaReceptorPanel.parseRows('a+b, -0.65');
if (!(cnBad.rows.length === 0 && cnBad.errors.length === 1)) fails.push('Cnma.parseRows: 2-column row should fail closed');

// Spec-collapse paste-tool: parse the python-anchor spec curve + the correct
// weighted-likelihood aggregator (theta -0.345, total var 0.08865833) and the
// naive IV-RE pool (theta -0.29532374).
const sc = global.window.SpecCollapsePanel.parseRows(
  '-0.40, 0.17320508, 8\n-0.25, 0.2236068, 8\n-0.55, 0.28284271, 6\n-0.18, 0.14142136, 8');
if (sc.rows.length !== 4) fails.push('SpecCollapse.parseRows: expected 4 rows, got ' + sc.rows.length);
if (sc.errors.length) fails.push('SpecCollapse.parseRows: unexpected errors ' + JSON.stringify(sc.errors));
try {
  const wl = global.window.AlmSpecCollapse.weightedLikelihood(sc.rows);
  const nv = global.window.AlmSpecCollapse.naiveIvre(sc.rows);
  if (!(Math.abs(wl.theta - (-0.345)) < 1e-6 && Math.abs(wl.var - 0.08865833) < 1e-6)) fails.push('SpecCollapse WL: theta/var off anchor');
  if (!(Math.abs(nv.theta - (-0.29532374)) < 1e-6)) fails.push('SpecCollapse naive: theta off anchor');
  // structural: total variance must exceed the collapsed naive pool variance.
  if (!(wl.var > nv.var)) fails.push('SpecCollapse: WL var should exceed naive (collapsed) var');
} catch (e) { fails.push('SpecCollapse fit threw ' + e); }
// Fail-closed: a 1-column row (missing se) must be rejected by parseRows.
const scBad = global.window.SpecCollapsePanel.parseRows('-0.40');
if (!(scBad.rows.length === 0 && scBad.errors.length === 1)) fails.push('SpecCollapse.parseRows: 1-column row should fail closed');

// Transported-NMA paste-tool: parse contrasts + a real transport. Self-consistency:
// when the target equals the source covariate mean, weights are uniform (ESS=n) and
// the transported league equals the source league.
const tn = global.window.TransportedNMAV1Panel.parseRows(
  'A, B, -0.40, 0.12, 60\nA, C, -0.55, 0.16, 55\nB, C, -0.20, 0.18, 65\nA, B, -0.30, 0.14, 50');
if (tn.rows.length !== 4) fails.push('TransportedNMA.parseRows: expected 4 rows, got ' + tn.rows.length);
if (tn.errors.length) fails.push('TransportedNMA.parseRows: unexpected errors ' + JSON.stringify(tn.errors));
try {
  const treatments = [];
  tn.rows.forEach(r => { [r.trtA, r.trtB].forEach(t => { if (treatments.indexOf(t) < 0) treatments.push(t); }); });
  const studies = tn.rows.map(r => ({ cov: { x: r.x } }));
  const netRows = tn.rows.map((r, i) => ({ trtA: r.trtA, trtB: r.trtB, yi: r.yi, sei: r.sei, study: i }));
  const meanX = tn.rows.reduce((a, r) => a + r.x, 0) / tn.rows.length;
  const rr = global.window.AlmTransportedNMA.run({ studies, rows: netRows, treatments, target: { x: meanX } });
  if (!(rr.ok && rr.transport.converged)) fails.push('TransportedNMA: did not converge');
  if (!(Math.abs(rr.transport.essRatio - 1) < 1e-6)) fails.push('TransportedNMA: ESS ratio should be 1 at the source mean');
  const dB = Math.abs(rr.source.effects.B.estimate - rr.transported.effects.B.estimate);
  const dC = Math.abs(rr.source.effects.C.estimate - rr.transported.effects.C.estimate);
  if (!(dB < 1e-9 && dC < 1e-9)) fails.push('TransportedNMA: transported league should equal source at the source mean');
} catch (e) { fails.push('TransportedNMA fit threw ' + e); }
// Fail-closed: a 4-column row (missing modifier) must be rejected by parseRows.
const tnBad = global.window.TransportedNMAV1Panel.parseRows('A, B, -0.40, 0.12');
if (!(tnBad.rows.length === 0 && tnBad.errors.length === 1)) fails.push('TransportedNMA.parseRows: 4-column row should fail closed');

// Multi-outcome-NMA paste-tool: parse contrasts + a real fit. Self-consistency:
// with single-contrast studies and consistent data the outcome-correlation seeds
// to 0, so outcome-1's league equals the single-outcome FE-NMA on the same rows.
const mon = global.window.MultiOutcomeNMAPanel.parseRows(
  'S1, A, B, -0.40, 0.12, -0.50, 0.15\nS2, A, C, -0.55, 0.16, -0.62, 0.18\nS3, B, C, -0.20, 0.18, -0.25, 0.20\nS4, A, B, -0.30, 0.14, -0.38, 0.16');
if (mon.rows.length !== 4) fails.push('MultiOutcomeNMA.parseRows: expected 4 rows, got ' + mon.rows.length);
if (mon.errors.length) fails.push('MultiOutcomeNMA.parseRows: unexpected errors ' + JSON.stringify(mon.errors));
try {
  const treatments = [];
  mon.rows.forEach(r => { [r.trtA, r.trtB].forEach(t => { if (treatments.indexOf(t) < 0) treatments.push(t); }); });
  const byStudy = {}, order = [];
  mon.rows.forEach(r => { if (!byStudy[r.study]) { byStudy[r.study] = []; order.push(r.study); } byStudy[r.study].push(r); });
  const studies = order.map(id => ({ id, contrasts: byStudy[id].map(r => ({ trtA: r.trtA, trtB: r.trtB, outcomes: [r.o1, r.o2] })) }));
  const f = global.window.AlmMultiOutcomeNMA.fit(studies, treatments, { K: 2 });
  if (!(f.ok && f.K === 2 && f.n_contrasts === 4)) fails.push('MultiOutcomeNMA fit: not ok / wrong shape');
  // outcome-1 league vs single-outcome FE NMA on the same rows (taus seed to 0 here).
  const NMA = global.window.AlmMultiplicativeNMA;
  const o1rows = mon.rows.map(r => ({ trtA: r.trtA, trtB: r.trtB, yi: r.o1.yi, sei: r.o1.sei }));
  const d = NMA._buildDesign(o1rows, treatments);
  const fe = NMA._fitWLS(d.X, d.y, d.v, 0);
  if (!(Math.abs(f.effects[0].B.estimate - fe.beta[0]) < 1e-9 && Math.abs(f.effects[0].C.estimate - fe.beta[1]) < 1e-9))
    fails.push('MultiOutcomeNMA: outcome-1 league should equal single-outcome FE NMA when outcome ρ seeds to 0');
} catch (e) { fails.push('MultiOutcomeNMA fit threw ' + e); }
// Fail-closed: a 6-column row (missing se2) must be rejected by parseRows.
const monBad = global.window.MultiOutcomeNMAPanel.parseRows('S1, A, B, -0.40, 0.12, -0.50');
if (!(monBad.rows.length === 0 && monBad.errors.length === 1)) fails.push('MultiOutcomeNMA.parseRows: 6-column row should fail closed');

// Multiplicative-NMA buildRows from the NMA scenario must yield n>p contrast rows.
const nrows = global.window.MultiplicativeNMAPanel.buildRows(global.window.NMA_CONFIG, global.window.RapidMeta.realData);
if (nrows.length < 5) fails.push('MultiplicativeNMA.buildRows: expected 5 rows, got ' + nrows.length);

// NMA-meta-reg buildRows must carry a finite year covariate per contrast row,
// and a real fit on the scenario must return per-treatment β + interaction slopes.
const mrrows = global.window.NmaMetaRegPanel.buildRows(global.window.NMA_CONFIG, global.window.RapidMeta.realData);
if (mrrows.length < 5) fails.push('NmaMetaReg.buildRows: expected 5 rows, got ' + mrrows.length);
if (!mrrows.every(r => isFinite(r.covariate))) fails.push('NmaMetaReg.buildRows: a row has a non-finite year covariate');
try {
  const fr = global.window.AlmNmaMetaReg.fit(mrrows, global.window.NMA_CONFIG.treatments, { predictAt: [2018, 2022] });
  if (!(fr.ok && isFinite(fr.tau2) && fr.gamma.B && isFinite(fr.gamma.B.estimate))) fails.push('NmaMetaReg fit: not ok / non-finite');
} catch (e) { fails.push('NmaMetaReg fit threw ' + e); }

// Funnel diagnostics must still mount with the AlmTrimFill delegation active.
check('FunnelDiagnostics', () => global.window.FunnelDiagnostics.render());
if (!registry['funnel-diagnostics-panel']) fails.push('FunnelDiagnostics: panel did not mount');

// RVE parseRows pure-function contract (clustered input).
const pr = global.window.RVEPanel.parseRows('S1, 0.4, 0.11\nS1, 0.5, 0.13\nS2, 0.3, 0.09\nS2, 0.35, 0.10');
if (pr.rows.length !== 4) fails.push('RVE.parseRows: expected 4 rows, got ' + pr.rows.length);
if (pr.errors.length) fails.push('RVE.parseRows: unexpected errors ' + JSON.stringify(pr.errors));
if (pr.hasMod) fails.push('RVE.parseRows: hasMod should be false (no 4th column)');
// RVE fit on the parsed clustered rows must produce a finite robust SE.
try {
  const fit = global.window.AlmRVE.fitCORR(pr.rows, { rho: 0.8, method: 'CR2' });
  const summ = global.window.AlmRVE.summary(fit);
  if (!(summ[0].se > 0)) fails.push('RVE: non-positive robust SE');
  if (!(summ[0].df > 0)) fails.push('RVE: non-positive Satterthwaite df');
} catch (e) { fails.push('RVE fit threw ' + e); }

if (fails.length) {
  console.error('SMOKE FAIL:\n - ' + fails.join('\n - '));
  process.exit(1);
}
console.log('SMOKE OK: 24 panels mounted + RVE/multilevel/transport/multivariate/personalised-TE/multi-outcome/location-scale/cnma/spec-collapse/transported-nma/multi-outcome-nma parse/fit + NMA buildRows + funnel/Begg + GOSH/DBT + Copas-Shi + RoBMA + ExperimentalMA + BMATau + Transportability + Multivariate + E-value + NMA-meta-reg + Personalised-TE + Multi-outcome + Location-scale + CNMA + SpecCollapse + TransportedNMA + MultiOutcomeNMA verified');
