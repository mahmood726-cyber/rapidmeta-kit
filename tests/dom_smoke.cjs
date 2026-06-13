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
require(V + 'uwls-panel.js');
require(V + 'selmodel-panel.js');
require(V + 'rare-events-panel.js');
require(V + 'rve-panel.js');

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
};
['UWLSPanel', 'SelModelPanel', 'RareEventsPanel', 'RVEPanel'].forEach((p) => {
  check(p, () => global.window[p].render());
  if (!registry[PANEL_ID[p]]) fails.push(p + ': no DOM node with id ' + PANEL_ID[p] + ' was inserted');
});

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
console.log('SMOKE OK: 4 panels mounted + RVE parse/fit verified');
