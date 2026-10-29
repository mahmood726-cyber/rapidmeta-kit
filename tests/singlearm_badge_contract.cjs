// Fail-closed single-arm R-comparison UI contract tests.
// These are synthetic *interface* tests; they do not execute R or establish parity.
'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
function load(path) {
  const scope = { console };
  vm.createContext(scope);
  vm.runInContext(fs.readFileSync(path, 'utf8'), scope, { filename: path });
  return scope;
}
const R = {
  fit_ok: true, engine: 'R 4.5.2', metafor_version: '4.8.0',
  review: 'synthetic', k: 4,
  logit_pool: { pool: 0.18, lci: 0.10, uci: 0.27, tau2: 0.04, I2: 30 },
  freeman_tukey_pool: { pool: 0.19, lci: 0.11, uci: 0.28 },
};
function badge(engine, r = R) {
  const scope = load('assets/vendor/r-validation-singlearm.js');
  let config = null;
  scope.PanelHelper = {
    buildCollapsiblePanel(obj) { config = obj; return { id: obj.id }; },
    insertAfterRBadge() {},
  };
  scope.document = { getElementById() { return null; } };
  assert.equal(scope.RValidationSingleArm.render(r, engine), true);
  assert.ok(config);
  return config;
}
function notValidated(out) {
  assert.doesNotMatch(out.summary, /✓|cross-validated|R-validated/);
  assert.match(out.bodyHtml, /No method-matched R parity/i);
}
// A numerically exact point estimate is not evidence of DL/Wald vs REML/HKSJ parity.
let out = badge({ prop: R.logit_pool.pool, k: 4, method: 'logit-RE-DL-Wald' });
notValidated(out);
assert.match(out.summary, /Method mismatch/);
assert.match(out.summary, /NOT parity/);
// Missing engine evidence cannot be inferred from formatted DOM percentages.
out = badge(null);
notValidated(out);
assert.match(out.summary, /not detected/);
// Even a declared matching estimator and k cannot certify an R process was run.
out = badge({ prop: R.logit_pool.pool, k: 4, method: 'logit-RE-REML-HKSJ' });
notValidated(out);
assert.match(out.summary, /independently executed/);
// Count mismatch and low-k cannot be awarded validation.
for (const k of [null, 2, 5]) {
  out = badge({ prop: R.logit_pool.pool, k, method: 'logit-RE-REML-HKSJ' });
  notValidated(out);
  assert.match(out.summary, /Study count/);
}
// The actual shipped JS engine advertises DL/Wald runtime provenance, never REML.
const scope = load('assets/vendor/single-arm-proportion.js');
scope.document = { getElementById() { return null; } };
const P = {
  getRealData() {
    return {
      a: { name: 'A', singleArm: true, events: 4, n: 40 },
      b: { name: 'B', singleArm: true, events: 9, n: 80 },
      c: { name: 'C', singleArm: true, events: 11, n: 90 },
      d: { name: 'D', singleArm: true, events: 13, n: 100 },
    };
  },
  fmt(x, digits) { return Number(x).toFixed(digits == null ? 1 : digits); },
  buildCollapsiblePanel(obj) { return { id: obj.id }; },
  insertAfterRBadge() {},
};
scope.PanelHelper = P;
assert.equal(scope.SingleArmProportion.render(), true);
assert.equal(scope.SingleArmProportion.lastFit.method, 'logit-RE-DL-Wald');
assert.equal(scope.SingleArmProportion.lastFit.k, 4);
assert.ok(scope.SingleArmProportion.lastFit.prop > 0);
P.getRealData = () => null;
assert.equal(scope.SingleArmProportion.render(), false);
assert.equal(scope.SingleArmProportion.lastFit, null); // stale fit removed
console.log('single-arm method-mismatch and R-badge refusal tests passed (Node; no R)');
