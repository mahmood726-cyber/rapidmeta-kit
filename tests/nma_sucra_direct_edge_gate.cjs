"use strict";
// Actual shipped browser panel, synthetic structural fixtures; not external R verification.
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
const source = fs.readFileSync(path.join(root, copies[0]), "utf8");
for (const copy of copies.slice(1)) {
  assert.equal(fs.readFileSync(path.join(root, copy), "utf8"), source,
               "distributed SUCRA engines must remain byte-identical: " + copy);
}
const DATA = {
  a: {tE: 4, tN: 100, cE: 8, cN: 100},
  b: {tE: 6, tN: 100, cE: 10, cN: 100},
  ab: {tE: 2, tN: 100, cE: 20, cN: 100},
};
const AC = {t1: "A", t2: "C", trials: ["a"]};
const BC = {t1: "B", t2: "C", trials: ["b"]};
const AB = {t1: "A", t2: "B", trials: ["ab"]};
const BA = {t1: "B", t2: "A", trials: ["ab"]};

function exercise(code, comparisons) {
  const captured = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: {comp: "C", out: "mortality"},
      comparisons,
    },
    PanelHelper: {
      getRealData() { return DATA; },
      fmt(n, places) { return Number(n).toFixed(places); },
      buildCollapsiblePanel(p) { captured.push(p); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("unexpected timer during direct panel test"); },
  };
  context.window = context;
  vm.runInNewContext(code, context);
  assert.equal(context.NMASUCRA.render(), true);
  assert.equal(captured.length, 1);
  return captured[0];
}
const cases = [
  {name: "star direct-evidence control", comparisons: [AC, BC], refuse: false},
  {name: "reversed star orientation", comparisons: [
    {t1: "C", t2: "A", trials: ["a"]},
    {t1: "C", t2: "B", trials: ["b"]},
  ], refuse: false},
  {name: "triangle adds unused A-B evidence", comparisons: [AC, BC, AB], refuse: true},
  {name: "reverse B-A edge also unused", comparisons: [AC, BC, BA], refuse: true},
  {name: "only indirect bridge for B", comparisons: [AC, AB], refuse: true},
  {name: "empty non-reference comparison is not evidence", comparisons: [
    AC, BC, {t1: "A", t2: "B", trials: []},
  ], refuse: false},
  {name: "literal trial object on non-reference edge", comparisons: [
    AC, BC, {t1: "A", t2: "B", trials: [DATA.ab]},
  ], refuse: true},
];
for (const copy of copies) {
  const code = fs.readFileSync(path.join(root, copy), "utf8");
  for (const test of cases) {
    const panel = exercise(code, test.comparisons);
    const label = copy + ": " + test.name;
    if (test.refuse) {
      assert.match(panel.summary, /^Refused: network comparisons omitted/, label);
      assert.match(panel.bodyHtml, /role="alert"/, label);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled estimate/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.doesNotMatch(panel.bodyHtml, /Top-ranked:/, label);
    } else {
      assert.match(panel.summary, /^OR scale/, label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.match(panel.bodyHtml, /Exploratory direct-only analysis \(not a fitted NMA\)/, label);
    }
  }
}
console.log("PASS: 21 actual SUCRA-panel scenarios over 3 shipped engines (4 refusals + 3 controls each).");
