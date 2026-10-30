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
  { name: "title-case continuous type in A", a: { ...binary(), allOutcomes: [{ ...kccq, type: "Continuous" }] }, b: binary(1), want: "mixed" },
  { name: "padded mixed-case continuous type in B", a: binary(), b: { ...binary(1), allOutcomes: [{ ...kccq, type: " CoNtInUoUs " }] }, want: "mixed" },
  { name: "malformed title-case continuous data still needs endpoint selection", a: { ...binary(), allOutcomes: [{ ...kccq, type: "Continuous", se: NaN }] }, b: binary(1), want: "mixed" },
  { name: "unknown effect type with explicit MD and SE cannot silently select OR", a: { ...binary(), allOutcomes: [{ type: "UNKNOWN", md: 12, se: 2 }] }, b: binary(1), want: "mixed" },
  { name: "missing effect type with explicit MD and SE cannot silently select OR", a: { ...binary(), allOutcomes: [{ md: 12, se: 2 }] }, b: binary(1), want: "mixed" },
  { name: "MD-only title-case outcomes remain valid", a: { allOutcomes: [{ ...kccq, type: "Continuous", md: 3, se: 1 }] }, b: { allOutcomes: [{ ...kccq, type: " CoNtInUoUs ", md: 2, se: 1 }] }, want: "MD" },
  { name: "object-shaped continuous metadata must not silently select OR", a: { ...binary(), allOutcomes: { type: "CONTINUOUS", md: 12, se: 2 } }, b: binary(1), want: "shape" },
  { name: "string allOutcomes must not silently select OR", a: binary(), b: { ...binary(1), allOutcomes: "CONTINUOUS" }, want: "shape" },
  { name: "null allOutcomes cannot establish absent continuous endpoint", a: { ...binary(), allOutcomes: null }, b: binary(1), want: "shape" },
  // Red-before-green: the old engine silently ranked crude ORs despite a
  // competing reported survival effect for the same trial. These source-executed
  // cases are synthetic refusals, not an R or clinical-source oracle.
  { name: "published HR inside allOutcomes cannot silently select OR",
    a: { ...binary(), allOutcomes: [{ type: "PRIMARY", shortLabel: "KCCQ",
      pubHR: 0.8, pubHR_LCI: 0.7, pubHR_UCI: 0.94 }] }, b: binary(1), want: "survival" },
  { name: "typed hazard ratio inside allOutcomes cannot silently select OR",
    a: binary(), b: { ...binary(1), allOutcomes: [{ type: "hazard_ratio", HR: 0.8 }] },
    want: "survival" },
  { name: "publishedHR inside allOutcomes cannot silently select OR",
    a: { ...binary(), allOutcomes: [{ type: "PRIMARY", publishedHR: 0.8 }] },
    b: binary(1), want: "survival" },
  // Preserve the established RapidMeta config pattern: a top-level publishedHR
  // accompanied by explicit BINARY outcome metadata is not itself a competing
  // allOutcomes candidate, so this guard does not indiscriminately refuse it.
  { name: "top-level historical publishedHR with binary-only outcomes",
    a: { ...binary(), publishedHR: 0.8,
      allOutcomes: [{ type: "binary", shortLabel: "mortality" }] },
    b: binary(1), want: "OR" },
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
  survival: "Refused: binary counts and time-to-event effect candidate",
  shape: "Refused: malformed outcome metadata",
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
      if (["mixed", "invalid", "zero", "shape", "survival"].includes(fixture.want)) {
        assert.match(panel.bodyHtml, /role="alert"/, label);
        const requiredRefusal = fixture.want === "invalid"
          ? /No SUCRA, treatment hierarchy or pooled estimate was computed/
          : /No SUCRA, treatment hierarchy or pooled result was computed/;
        assert.match(panel.bodyHtml, requiredRefusal, label);
        assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      } else {
        assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
        assert.doesNotMatch(panel.summary, /^Refused:/, label);
      }
      passed++;
    }
  }
}
assert.equal(passed, cases.length * sources.length * 2);
console.log("PASS: " + passed + " source-executed OR/MD same-study refusal and control scenarios; no R parity claimed.");
