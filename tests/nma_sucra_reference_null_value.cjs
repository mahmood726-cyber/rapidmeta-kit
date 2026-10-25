"use strict";
// Synthesis statistical integrity: source-executed UI regression.
// Identity/null-value checks are not independent R validation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const copies = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const canonical = fs.readFileSync(path.join(root, copies[0]), "utf8");
for (const copy of copies.slice(1)) {
  assert.equal(fs.readFileSync(path.join(root, copy), "utf8"), canonical,
               "distributed SUCRA panel copies must match: " + copy);
}

function exercise(code, effectType, reverse) {
  const evidence = effectType === "MD"
    ? {
        a: {allOutcomes: [{type: "CONTINUOUS", md: -3, se: 0.5}]},
        b: {allOutcomes: [{type: "CONTINUOUS", md: -2, se: 0.7}]},
      }
    : {
        a: {tE: 3, tN: 100, cE: 9, cN: 100},
        b: {tE: 5, tN: 100, cE: 10, cN: 100},
      };
  let captured = null;
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: {comp: "C", out: "mortality"},
      comparisons: ["A", "B"].map((t, i) => ({
        t1: reverse ? "C" : t,
        t2: reverse ? t : "C",
        trials: [i ? "b" : "a"],
      })),
    },
    PanelHelper: {
      getRealData() { return evidence; },
      fmt(n, places) { return Number(n).toFixed(places); },
      buildCollapsiblePanel(p) { captured = p; return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("unexpected timer in direct render test"); },
  };
  context.window = context;
  vm.runInNewContext(code, context);
  assert.equal(context.NMASUCRA.render(), true);
  assert.ok(captured);
  return captured;
}
let scenarios = 0;
for (const copy of copies) {
  const code = fs.readFileSync(path.join(root, copy), "utf8");
  for (const effectType of ["MD", "OR"]) {
    for (const reverse of [false, true]) {
      const panel = exercise(code, effectType, reverse);
      const testName = copy + " " + effectType + " reverse=" + reverse;
      assert.match(panel.summary, new RegExp("^" + effectType + " scale"), testName);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, testName);
      const match = panel.bodyHtml.match(/\\(ref\\)<\\/td>\\s*<td[^>]*>([^<]+)<\\/td>/);
      assert.ok(match, "reference row missing: " + testName);
      assert.equal(match[1], effectType === "MD" ? "0.00" : "1.00", testName);
      if (effectType === "MD") {
        assert.doesNotMatch(match[1], /^1\\.00$/, testName);
      } else {
        assert.doesNotMatch(match[1], /^0\\.00$/, testName);
      }
      scenarios++;
    }
  }
}
console.log("PASS: " + scenarios + " source-executed SUCRA reference-null-value scenarios across three distributed copies.");
