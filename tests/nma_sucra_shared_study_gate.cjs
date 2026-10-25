"use strict";
// Synthesis | Hourly Statistical Parity: regression for shared multi-arm evidence.
// Source: Cochrane Handbook ch. 23, section 23.3.4.
// Synthetic cases verify a refusal, NOT numerical correctness or native R parity.
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
const contents = copies.map(p => fs.readFileSync(path.join(root, p), "utf8"));
for (let i = 1; i < contents.length; i++) {
  assert.equal(contents[i], contents[0], copies[i] + " differs from canonical source");
}

const a = { tE: 2, tN: 20, cE: 4, cN: 20 };
const b = { tE: 3, tN: 30, cE: 6, cN: 30 };
const A = trials => ({ t1: "A", t2: "C", trials });
const B = trials => ({ t1: "B", t2: "C", trials });
function exercise(code, comparisons, records) {
  const captured = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: { comp: "C", out: "mortality" },
      comparisons,
    },
    PanelHelper: {
      getRealData() { return records; },
      fmt(value, places) { return Number(value).toFixed(places); },
      buildCollapsiblePanel(panel) { captured.push(panel); return {}; },
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
  assert.equal(context.NMASUCRA.render(), true);
  assert.equal(captured.length, 1);
  return captured[0];
}

const scenarios = [
  ["shared reference in two direct edges", [A(["same"]), B(["same"])], { same: a }, true],
  ["shared reference with reversed edge ordering",
    [{ t1: "C", t2: "A", trials: ["same"] },
      { t1: "C", t2: "B", trials: ["same"] }], { same: a }, true],
  ["duplicate trial within one comparison", [A(["a", "a"]), B(["b"])], { a, b }, true],
  ["distinct contrast records with same explicit study ID", [A(["a"]), B(["b"])],
    { a: { ...a, study_id: "NCT100" }, b: { ...b, study_id: "nct100" } }, true],
  ["shared object identity", [A([a]), B([a])], {}, true],
  ["independent trials", [A(["a"]), B(["b"])], { a, b }, false],
  ["independent studies with different explicit IDs", [A(["a"]), B(["b"])],
    { a: { ...a, studyId: "study1" }, b: { ...b, studyId: "study2" } }, false],
  ["continuous independent trials", [A(["a"]), B(["b"])],
    { a: { allOutcomes: [{ type: "CONTINUOUS", md: -2, se: 0.6 }] },
      b: { allOutcomes: [{ type: "CONTINUOUS", md: -3, se: 0.9 }] } }, false],
];
let passed = 0;
contents.forEach((code, copy) => {
  for (const [name, comparisons, records, refused] of scenarios) {
    const panel = exercise(code, comparisons, records);
    const ctx = copies[copy] + ": " + name;
    if (refused) {
      assert.match(panel.summary, /^Refused: shared or duplicated trial evidence/, ctx);
      assert.match(panel.bodyHtml, /role="alert"/, ctx);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled estimate/, ctx);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, ctx);
    } else {
      assert.match(panel.summary, /^(OR|MD) scale/, ctx);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, ctx);
      assert.doesNotMatch(panel.summary, /^Refused:/, ctx);
    }
    passed++;
  }
});
assert.equal(passed, scenarios.length * copies.length);
console.log("PASS: " + passed + " source-executed SUCRA shared-study refusal scenarios; not native R parity.");
