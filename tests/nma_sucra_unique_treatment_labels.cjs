"use strict";
// Synthesis | Hourly Statistical Parity — distinct treatment identity gate.
// Statistical rationale: Cochrane Handbook Ch 11 section 11.4.3.3.
// Synthetic V8 source-executed controls, NOT external R/NMA scientific parity.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const paths = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const sources = paths.map(p => fs.readFileSync(path.join(root, p), "utf8"));
assert.equal(sources[0], sources[1], "docs copy must match canonical");
assert.equal(sources[0], sources[2], "template copy must match canonical");
const cases = [
  { name: "distinct controls", labels: ["Placebo", "A", "B"], refuse: false },
  { name: "distinct similar treatments", labels: ["Placebo", "A", "AA"], refuse: false },
  { name: "duplicate active treatment", labels: ["Placebo", "A", "A", "B"], refuse: true },
  { name: "duplicate protocol reference", labels: ["Placebo", "Placebo", "A", "B"], refuse: true },
  { name: "case-folded duplicate", labels: ["Placebo", "A", "a", "B"], refuse: true },
  { name: "whitespace variant duplicate", labels: ["Placebo", "A", " A ", "B"], refuse: true },
  { name: "whitespace reference duplicate", labels: ["Placebo", " placebo ", "A", "B"], refuse: true },
  { name: "empty name", labels: ["Placebo", "", "A", "B"], refuse: true },
  { name: "blank name", labels: ["Placebo", "   ", "A", "B"], refuse: true },
  { name: "null name", labels: ["Placebo", null, "A", "B"], refuse: true },
  { name: "numeric name", labels: ["Placebo", 12, "A", "B"], refuse: true },
  { name: "object name", labels: ["Placebo", {}, "A", "B"], refuse: true },
];
function exercise(source, test, reversed) {
  const panels = [];
  const second = test.labels.includes("B") ? "B" : "AA";
  const context = {
    NMA_CONFIG: {
      treatments: test.labels,
      protocol: { comp: "Placebo", out: "mortality" },
      comparisons: ["A", second].map((t,i) => ({
        t1: reversed ? "Placebo" : t,
        t2: reversed ? t : "Placebo",
        trials: [i ? "two" : "one"],
      })),
    },
    PanelHelper: {
      getRealData() {
        return {
          one: { tE: 16, tN: 20, cE: 4, cN: 20 },
          two: { tE: 12, tN: 20, cE: 4, cN: 20 },
        };
      },
      fmt(x, n) { return Number(x).toFixed(n); },
      buildCollapsiblePanel(p) { panels.push(p); return {}; },
      insertAfterRBadge() {},
    },
    document: { readyState: "loading", addEventListener() {}, getElementById() { return null; } },
    setTimeout() { throw Error("unexpected timer"); },
  };
  context.window = context;
  vm.runInNewContext(source, context, { timeout: 10000 });
  assert.equal(context.NMASUCRA.render(), true, test.name + ": visible output");
  assert.equal(panels.length, 1, test.name + ": one panel");
  return panels[0];
}
let passed = 0;
for (const [i, source] of sources.entries()) {
  for (const test of cases) for (const reversed of [false, true]) {
    const panel = exercise(source, test, reversed);
    const label = paths[i] + " " + test.name + " reversed=" + reversed;
    if (test.refuse) {
      assert.equal(panel.summary, "Refused: invalid or duplicate treatment labels", label);
      assert.match(panel.bodyHtml, /role="alert"/, label);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
    } else {
      assert.match(panel.summary, /^OR scale · 3 treatments/, label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.doesNotMatch(panel.summary, /^Refused:/, label);
    }
    passed++;
  }
}
assert.equal(passed, 72);
console.log("PASS: 72 source-executed treatment-label negative and positive controls (not R parity).");
