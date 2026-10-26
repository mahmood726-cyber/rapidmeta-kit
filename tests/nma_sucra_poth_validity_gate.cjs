"use strict";
// Synthesis | Hourly Statistical Parity — ranking precision validity.
// Wigle et al., Statistics in Medicine (2025), doi:10.1002/sim.70176.
// POTH is bounded on [0,1]. These are UI/negative regression tests,
// not a network-model implementation or independent R-oracle validation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const paths = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const sources = paths.map(p => fs.readFileSync(path.join(root, p), "utf8"));
assert.equal(sources[1], sources[0], "docs implementation differs");
assert.equal(sources[2], sources[0], "template implementation differs");
const cases = [
  { name: "POTH helper absent", absent: true, expected: "unavailable" },
  { name: "POTH returns null", result: null, expected: "unavailable" },
  { name: "POTH metric missing", result: {verdict: "Test"}, expected: "unavailable" },
  { name: "POTH NaN", result: {poth: NaN, verdict: "Test"}, expected: "unavailable" },
  { name: "POTH +Infinity", result: {poth: Infinity, verdict: "Test"}, expected: "unavailable" },
  { name: "POTH -Infinity", result: {poth: -Infinity, verdict: "Test"}, expected: "unavailable" },
  { name: "POTH negative", result: {poth: -0.01, verdict: "Test"}, expected: "unavailable" },
  { name: "POTH >1", result: {poth: 1.01, verdict: "Test"}, expected: "unavailable" },
  { name: "POTH string", result: {poth: "0.80", verdict: "Test"}, expected: "unavailable" },
  { name: "POTH low", result: {poth: 0.49, verdict: "Test"}, expected: "low" },
  { name: "POTH boundary", result: {poth: 0.50, verdict: "Test"}, expected: "high" },
  { name: "POTH high", result: {poth: 0.80, verdict: "Test"}, expected: "high" },
];
function render(source, fixture, reversed) {
  const panels = [];
  const realData = {
    trial_A: {allOutcomes: [{type: "CONTINUOUS", md: 1, se: 0.2}]},
    trial_B: {allOutcomes: [{type: "CONTINUOUS", md: 2, se: 0.3}]},
  };
  const comparisons = ["A", "B"].map(t => ({
    t1: reversed ? "Placebo" : t,
    t2: reversed ? t : "Placebo",
    trials: ["trial_" + t],
  }));
  const ctx = {
    NMA_CONFIG: {treatments: ["Placebo", "A", "B"],
      protocol: {comp: "Placebo", out: "MMSE"}, comparisons},
    PanelHelper: {
      getRealData() {return realData;},
      fmt(value, digits) {return Number(value).toFixed(digits);},
      buildCollapsiblePanel(panel) {panels.push(panel); return {};},
      insertAfterRBadge() {},
    },
    document: {readyState: "loading", addEventListener() {},
      getElementById() {return null;}},
    setTimeout() {throw Error("Unexpected timer");},
  };
  ctx.window = ctx;
  if (!fixture.absent) ctx.POTH = {compute() {return fixture.result;}};
  vm.runInNewContext(source, ctx, {timeout: 10000});
  assert.equal(ctx.NMASUCRA.render(), true, fixture.name + " failed to render");
  assert.equal(panels.length, 1, fixture.name + " must create one panel");
  return panels[0];
}
let passed = 0;
for (const [i, source] of sources.entries()) {
  for (const c of cases) for (const reversed of [false, true]) {
    const p = render(source, c, reversed);
    const label = paths[i] + " " + c.name + " reversed=" + reversed;
    assert.match(p.bodyHtml, /Per-treatment ranking summaries:/, label);
    if (c.expected === "unavailable") {
      assert.match(p.summary, /ranking precision unavailable — no top treatment claimed/, label);
      assert.match(p.bodyHtml, /Ranking precision unavailable/, label);
      assert.match(p.bodyHtml, /role="alert"/, label);
      assert.doesNotMatch(p.bodyHtml, /<strong>Top-ranked:<\/strong>/, label);
      assert.doesNotMatch(p.summary, /POTH=(?:NaN|Infinity)/, label);
    } else if (c.expected === "low") {
      assert.match(p.summary, /hierarchy non-informative/, label);
      assert.match(p.summary, /POTH=0.49/, label);
      assert.doesNotMatch(p.bodyHtml, /<strong>Top-ranked:<\/strong>/, label);
    } else {
      assert.match(p.summary, /top:/, label);
      assert.match(p.bodyHtml, /<strong>Top-ranked:<\/strong>/, label);
      assert.match(p.summary, /POTH=0.(?:50|80)/, label);
    }
    passed++;
  }
}
assert.equal(passed, 72);
console.log("PASS: 72 source-executed POTH-validity regression/negative scenarios (not R parity).");
