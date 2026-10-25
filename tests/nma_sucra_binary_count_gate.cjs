"use strict";
// Synthesis statistical-integrity regression against the actual shipped panels.
// These synthetic count scenarios test fail-closed behaviour, NOT R-metafor parity.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.join(__dirname, "..");
const copies = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const canonical = fs.readFileSync(path.join(root, copies[0]), "utf8");
for (const copy of copies.slice(1)) {
  assert.equal(fs.readFileSync(path.join(root, copy), "utf8"), canonical,
               "distributed SUCRA browser engines must be identical: " + copy);
}
const normal = { tE: 3, tN: 40, cE: 6, cN: 40 };
const continuous = { allOutcomes: [{ type: "CONTINUOUS", md: -2, se: 0.6 }] };
function exercise(code, a, b = normal, reverse = false) {
  const captured = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: { comp: "C", out: "mortality" },
      comparisons: ["A", "B"].map((t, i) => ({
        t1: reverse ? "C" : t,
        t2: reverse ? t : "C",
        trials: [i ? "b" : "a"],
      })),
    },
    PanelHelper: {
      getRealData() { return { a, b }; },
      fmt(value, places) { return Number(value).toFixed(places); },
      buildCollapsiblePanel(p) { captured.push(p); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected bootstrap timer"); },
  };
  context.window = context;
  vm.runInNewContext(code, context);
  assert.equal(context.NMASUCRA.render(), true, "expected a visible outcome or refusal");
  assert.equal(captured.length, 1);
  return captured[0];
}
const invalid = [
  ["fractional treatment events", {tE: 2.5, tN: 20, cE: 4, cN: 20}],
  ["negative counts in both arms, formerly a finite OR", {tE: -1, tN: 20, cE: -1, cN: 20}],
  ["events greater than N in both arms, formerly a finite OR", {tE: 21, tN: 20, cE: 22, cN: 20}],
  ["zero treatment denominator", {tE: 0, tN: 0, cE: 4, cN: 20}],
  ["negative denominator", {tE: 2, tN: -20, cE: 4, cN: 20}],
  ["null count must not coerce to zero", {tE: null, tN: 20, cE: 4, cN: 20}],
  ["boolean count must not coerce to zero", {tE: false, tN: 20, cE: 4, cN: 20}],
  ["empty-string count must not coerce to zero", {tE: "", tN: 20, cE: 4, cN: 20}],
  ["partial binary counts must not disappear", {tE: 2, tN: 20, cN: 20}],
  ["unsafe integer denominator", {tE: 2, tN: 9007199254740992, cE: 4, cN: 20}],
  ["non-integer string", {tE: "2.5", tN: 20, cE: 4, cN: 20}],
  ["malformed binary with valid MD must not fall back",
    {tE: -1, tN: 20, cE: -1, cN: 20,
      allOutcomes: [{type: "CONTINUOUS", md: -2, se: 0.6}]}],
];
const positive = [
  ["valid numeric", {tE: 2, tN: 20, cE: 4, cN: 20}, normal, "OR"],
  ["valid integer strings", {tE: " 2 ", tN: "20", cE: "4", cN: "20"}, normal, "OR"],
  ["valid zero-cell correction", {tE: 0, tN: 20, cE: 4, cN: 20}, normal, "OR"],
  ["valid all-event correction", {tE: 20, tN: 20, cE: 4, cN: 20}, normal, "OR"],
  ["genuinely continuous-only", continuous, continuous, "MD"],
];
let executed = 0;
for (const copy of copies) {
  const code = fs.readFileSync(path.join(root, copy), "utf8");
  for (const [name, row] of invalid) {
    for (const reverse of [false, true]) {
      const panel = exercise(code, row, normal, reverse);
      const ctx = copy + " " + name + " reverse=" + reverse;
      assert.match(panel.summary, /^Refused: invalid binary 2×2/, ctx);
      assert.match(panel.bodyHtml, /role="alert"/, ctx);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled estimate/, ctx);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:/, ctx);
      assert.doesNotMatch(panel.bodyHtml, /Top-ranked:/, ctx);
      executed++;
    }
  }
  for (const [name, a, b, scale] of positive) {
    const panel = exercise(code, a, b);
    const ctx = copy + " " + name;
    assert.match(panel.summary, new RegExp("^" + scale + " scale"), ctx);
    assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, ctx);
    assert.doesNotMatch(panel.summary, /^Refused:/, ctx);
    executed++;
  }
  // A malformed row for the SECOND treatment must also refuse, not silently drop it.
  const second = exercise(code, normal, invalid[0][1]);
  assert.match(second.summary, /^Refused: invalid binary 2×2/, copy);
  assert.doesNotMatch(second.bodyHtml, /Per-treatment ranking summaries:/, copy);
  executed++;
}
assert.equal(executed, copies.length * (invalid.length * 2 + positive.length + 1));
console.log("PASS: " + executed + " source-executed SUCRA binary-count scenarios across 3 distributed copies; no R oracle claimed.");
