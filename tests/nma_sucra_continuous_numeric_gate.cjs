"use strict";
// Synthesis | Hourly Statistical Parity
// Cochrane Handbook chapter 10.3: generic inverse variance requires a valid
// effect estimate and its standard error; inverse of variance is the weight.
// Synthetic browser-gate tests only: NOT independent R/metafor validation.
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
sources.slice(1).forEach((src, i) =>
  assert.equal(src, sources[0], "SUCRA distributed copies disagree: " + paths[i+1]));

const md = (mean, se) => ({ allOutcomes: [{ type: "CONTINUOUS", md: mean, se }] });
const valid = md(-2, 0.5);
const binary = { tE: 3, tN: 20, cE: 7, cN: 20 };
const hr = { allOutcomes: [{ type: "PRIMARY", shortLabel: "MMSE", pubHR: 0.8 }] };
const onlyContinuous = entries => ({ allOutcomes: entries });
function clone(x) {
  if (Array.isArray(x)) return x.map(clone);
  if (x && typeof x === "object") {
    return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, clone(v)]));
  }
  return x;
}
function render(source, first, second, reversed = false) {
  const panels = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: { comp: "C", out: "MMSE" },
      comparisons: [
        { t1: reversed ? "C" : "A", t2: reversed ? "A" : "C", trials: ["a"] },
        { t1: "B", t2: "C", trials: ["b"] },
      ],
    },
    PanelHelper: {
      getRealData() { return { a: clone(first), b: clone(second) }; },
      fmt(n, digits) { return Number(n).toFixed(digits); },
      buildCollapsiblePanel(panel) { panels.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected bootstrap"); },
  };
  context.window = context;
  vm.runInNewContext(source, context, { timeout: 10000 });
  assert.equal(context.NMASUCRA.render(), true);
  assert.equal(panels.length, 1);
  return panels[0];
}
const cases = [
  ["NaN mean difference", md(NaN, 0.5), valid, "invalid"],
  ["infinite mean difference", md(Infinity, 0.5), valid, "invalid"],
  ["negative infinite MD", md(-Infinity, 0.5), valid, "invalid"],
  ["NaN standard error", md(1, NaN), valid, "invalid"],
  ["infinite standard error", md(1, Infinity), valid, "invalid"],
  ["zero standard error", md(1, 0), valid, "invalid"],
  ["negative standard error", md(1, -0.5), valid, "invalid"],
  ["SE square overflows", md(1, 1e200), valid, "invalid"],
  ["SE square underflows", md(1, 1e-200), valid, "invalid"],
  ["inverse variance overflows", md(1, 1e-160), valid, "invalid"],
  ["missing MD", onlyContinuous([{ type: "CONTINUOUS", se: 0.5 }]), valid, "invalid"],
  ["missing SE", onlyContinuous([{ type: "CONTINUOUS", md: 1 }]), valid, "invalid"],
  ["string MD", onlyContinuous([{ type: "CONTINUOUS", md: "1", se: 0.5 }]), valid, "invalid"],
  ["string SE", onlyContinuous([{ type: "CONTINUOUS", md: 1, se: "0.5" }]), valid, "invalid"],
  ["valid first, malformed second", onlyContinuous([
    { type: "CONTINUOUS", md: 1, se: 0.5 },
    { type: "CONTINUOUS", md: 2, se: NaN },
  ]), valid, "invalid"],
  ["malformed first, valid second", onlyContinuous([
    { type: "CONTINUOUS", md: 1, se: NaN },
    { type: "CONTINUOUS", md: 2, se: 0.5 },
  ]), valid, "invalid"],
  ["reverse orientation invalid", md(NaN, 0.5), valid, "invalid", true],
  ["legitimate MD controls", md(-2, 0.5), md(1, 0.5), "MD"],
  ["legitimate binary controls", binary, { ...binary }, "OR"],
  ["prior HR refusal preserved", hr, valid, "HR"],
  ["source-typed MD overrides published HR field", onlyContinuous([
    { type: "CONTINUOUS", md: 1, se: 0.5 },
    ...hr.allOutcomes,
  ]), valid, "MD"],
];
let passed = 0;
for (const [i, source] of sources.entries()) {
  for (const [name, first, second, expected, reversed] of cases) {
    const label = paths[i] + ": " + name;
    const panel = render(source, first, second, reversed);
    if (expected === "invalid") {
      assert.match(panel.summary, /^Refused: invalid continuous MD or standard error/, label);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
    } else if (expected === "HR") {
      assert.match(panel.summary, /^Refused: published HR fields cannot be treated as mean differences/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
    } else {
      assert.match(panel.summary, new RegExp("^" + expected + " scale"), label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
    }
    passed++;
  }
}
assert.equal(passed, paths.length * cases.length);
console.log("PASS: " + passed + " source-executed SUCRA continuous-numeric scenarios; no native R parity claimed.");
