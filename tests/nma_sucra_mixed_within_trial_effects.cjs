"use strict";
// Synthesis | Hourly Statistical Parity — refuse unselected within-study OR/MD endpoints.
// Source: Cochrane Handbook Ch 6, 6.1.1 and 6.5.1 (outcome type and effect).
// These are synthetic, source-executed refusal controls, NOT independent R parity.
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
assert.equal(sources[1], sources[0], "docs SUCRA copy must match canonical");
assert.equal(sources[2], sources[0], "template SUCRA copy must match canonical");

const binary = (i = 0) => ({ tE: 4 + i, tN: 40, cE: 10 + i, cN: 40 });
const md = (effect = 1) => ({
  allOutcomes: [{ type: "CONTINUOUS", shortLabel: "KCCQ", md: effect, se: 1 }],
});
const kccq = { type: "CONTINUOUS", shortLabel: "KCCQ", md: 12, se: 2 };

const cases = [
  { name: "binary-first incorrectly hides MD in A", a: { ...binary(), allOutcomes: [kccq] }, b: binary(1), want: "mixed" },
  { name: "binary-first incorrectly hides MD in B", a: binary(), b: { ...binary(1), allOutcomes: [kccq] }, want: "mixed" },
  { name: "lowercase continuous type", a: { ...binary(), allOutcomes: [{ ...kccq, type: "continuous" }] }, b: binary(1), want: "mixed" },
  { name: "malformed coexisting MD still needs selection", a: { ...binary(), allOutcomes: [{ type: "CONTINUOUS", md: NaN, se: 0 }] }, b: binary(1), want: "mixed" },
  { name: "PRIMARY metadata cannot select between effect types", a: { ...binary(), allOutcomes: [{ type: "PRIMARY", shortLabel: "mortality" }, kccq] }, b: binary(1), want: "mixed" },
  { name: "ordinary binary studies", a: binary(), b: binary(1), want: "OR" },
  { name: "binary plus non-continuous metadata", a: { ...binary(), allOutcomes: [{ type: "PRIMARY", shortLabel: "mortality" }] }, b: binary(1), want: "OR" },
  { name: "MD-only studies", a: md(3), b: md(2), want: "MD" },
  { name: "malformed counts remain a binary-count refusal", a: { ...binary(), tE: 500, allOutcomes: [kccq] }, b: binary(1), want: "invalid" },
  { name: "double-zero remains an uninformative-OR refusal", a: { tE: 0, tN: 40, cE: 0, cN: 40, allOutcomes: [kccq] }, b: binary(1), want: "zero" },
];

function exercise(source, fixture, reversed) {
  const panels = [];
  const cfg = {
    treatments: ["Placebo", "A", "B"],
    protocol: { comp: "Placebo", out: "KCCQ" },
    comparisons: ["A", "B"].map((name, i) => ({
      t1: reversed ? "Placebo" : name,
      t2: reversed ? name : "Placebo",
      trials: [i ? "b" : "a"],
    })),
  };
  const context = {
    NMA_CONFIG: cfg,
    PanelHelper: {
      getRealData() { return { a: fixture.a, b: fixture.b }; },
      fmt(n, digits) { return Number(n).toFixed(digits); },
      buildCollapsiblePanel(panel) { panels.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected scheduled bootstrap"); },
  };
  context.window = context;
  vm.runInNewContext(source, context, { timeout: 10000 });
  assert.equal(context.NMASUCRA.render(), true, fixture.name + ": visible result or refusal");
  assert.equal(panels.length, 1, fixture.name + ": one panel");
  return panels[0];
}

const starts = {
  mixed: "Refused: mixed binary and continuous candidate outcomes in a trial",
  OR: "OR scale",
  MD: "MD scale",
  invalid: "Refused: invalid binary 2×2",
  zero: "Refused: double-zero or double-all-event",
};
let passed = 0;
for (const [i, source] of sources.entries()) {
  for (const fixture of cases) {
    for (const reversed of [false, true]) {
      const panel = exercise(source, fixture, reversed);
      const label = paths[i] + " / " + fixture.name + " / reversed=" + reversed;
      assert.ok(panel.summary.startsWith(starts[fixture.want]), label + ": " + panel.summary);
      if (["mixed", "invalid", "zero"].includes(fixture.want)) {
        assert.match(panel.bodyHtml, /role="alert"/, label);
        assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
        assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      } else {
        assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
        assert.doesNotMatch(panel.summary, /^Refused:/, label);
      }
      passed++;
    }
  }
}
assert.equal(passed, 60);
console.log("PASS: 60 source-executed OR/MD same-study refusal and control scenarios; no R parity claimed.");
