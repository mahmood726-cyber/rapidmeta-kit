"use strict";
// Synthesis | Hourly Statistical Parity — ambiguous clinical outcome-direction guard.
// Source: Cochrane Handbook current Chapter 6, MECIR C61 (effect-scale direction).
// Synthetic/source-executed UI regressions; NOT external R/NMA parity.
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
  { name: "overall survival", out: "overall survival", refuse: true },
  { name: "progression-free survival", out: "progression-free survival", refuse: true },
  { name: "disease-free survival", out: "disease-free survival", refuse: true },
  { name: "failure-free survival", out: "failure-free survival", refuse: true },
  { name: "mixed mortality improvement", out: "mortality improvement", refuse: true },
  { name: "mixed adverse response", out: "adverse response", refuse: true },
  { name: "mortality control", out: "mortality", direction: "smaller value = better" },
  { name: "response control", out: "response", direction: "larger value = better" },
];
function exercise(source, c, reversed) {
  const panels = [];
  const rd = {
    a: {tE:16,tN:20,cE:4,cN:20},
    b: {tE:12,tN:20,cE:4,cN:20},
  };
  const context = {
    NMA_CONFIG: {
      treatments: ["Placebo", "A", "B"],
      protocol: { comp: "Placebo", out: c.out },
      comparisons: ["A", "B"].map((t, i) => ({
        t1: reversed ? "Placebo" : t,
        t2: reversed ? t : "Placebo",
        trials: [i ? "b" : "a"],
      })),
    },
    POTH: { compute() { return {poth: 0.8, verdict: "informative"}; } },
    PanelHelper: {
      getRealData() { return rd; },
      fmt(x,n) { return Number(x).toFixed(n); },
      buildCollapsiblePanel(p) { panels.push(p); return {}; },
      insertAfterRBadge() {},
    },
    document: {readyState:"loading",addEventListener(){},getElementById(){return null;}},
    setTimeout() { throw Error("unexpected timer"); },
  };
  context.window = context;
  vm.runInNewContext(source, context, { timeout: 10000 });
  assert.equal(context.NMASUCRA.render(), true, c.name + ": visible outcome");
  assert.equal(panels.length, 1, c.name + ": exactly one panel");
  return panels[0];
}
let passed = 0;
for (const [i, source] of sources.entries()) {
  for (const c of cases) for (const reversed of [false, true]) {
    const p = exercise(source, c, reversed);
    const label = paths[i] + " " + c.name + " reversed=" + reversed;
    if (c.refuse) {
      assert.equal(p.summary, "Refused: ambiguous outcome direction for treatment ranking", label);
      assert.match(p.bodyHtml, /role="alert"/, label);
      assert.match(p.bodyHtml, /No SUCRA or treatment hierarchy was computed/, label);
      assert.doesNotMatch(p.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
    } else {
      assert.match(p.summary, /^OR scale/, label);
      assert.match(p.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.ok(p.bodyHtml.includes(c.direction), label + ": positive direction");
      assert.doesNotMatch(p.summary, /^Refused:/, label);
    }
    passed++;
  }
}
assert.equal(passed, 48);
console.log("PASS: 48 source-executed survival/mixed-direction refusal and positive-control scenarios (not R parity).");
