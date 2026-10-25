"use strict";
// Synthesis | Hourly Statistical Parity: reject unselected multiple MD endpoints.
// Source: Cochrane Handbook Ch 10, appropriate effect/outcome selection.
// Synthetic refusal controls only; these are NOT native R oracle parity tests.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const copies = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const sources = copies.map(p => fs.readFileSync(path.join(root, p), "utf8"));
for (let i = 1; i < sources.length; i++) {
  assert.equal(sources[i], sources[0], copies[i] + " must equal canonical SUCRA source");
}
const outcome = (label, md, se, extra = {}) =>
  ({type: "CONTINUOUS", shortLabel: label, md, se, ...extra});
const singleA = () => ({allOutcomes: [outcome("MMSE", -2, 0.5)]});
const singleB = () => ({allOutcomes: [outcome("MMSE", -1, 0.8)]});
const binaryA = () => ({tE: 2, tN: 20, cE: 5, cN: 20});
const binaryB = () => ({tE: 3, tN: 30, cE: 7, cN: 30});

function exercise(code, a, b, reverse = false) {
  const panels = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: {comp: "C", out: "MMSE"},
      comparisons: ["A", "B"].map((t, i) => ({
        t1: reverse ? "C" : t,
        t2: reverse ? t : "C",
        trials: [i ? "b" : "a"],
      })),
    },
    PanelHelper: {
      getRealData() { return {a, b}; },
      fmt(value, places) { return Number(value).toFixed(places); },
      buildCollapsiblePanel(panel) { panels.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected panel timer"); },
  };
  context.window = context;
  vm.runInNewContext(code, context);
  assert.equal(context.NMASUCRA.render(), true, "must display result or refusal");
  assert.equal(panels.length, 1, "must display exactly one panel");
  return panels[0];
}
const refused = [
  ["two different clinical instruments", () =>
    [{allOutcomes: [outcome("MMSE", -2, 0.5), outcome("KCCQ", 10, 1.2)]}, singleB()]],
  ["same instrument at two follow-up visits", () =>
    [{allOutcomes: [outcome("MMSE", -2, 0.5, {week: 12}),
                    outcome("MMSE", -3, 0.7, {week: 24})]}, singleB()]],
  ["two identical typed outcomes are still ambiguous", () =>
    [{allOutcomes: [outcome("MMSE", -2, 0.5),
                    outcome("MMSE", -2, 0.5)]}, singleB()]],
  ["upper- and lower-case CONTINUOUS rows", () =>
    [{allOutcomes: [outcome("MMSE", -2, 0.5),
                    {type: "continuous", shortLabel: "KCCQ", md: 3, se: 1}]}, singleB()]],
  ["multiple effects in second treatment", () =>
    [singleA(), {allOutcomes: [outcome("MMSE", -1, 0.8),
                              outcome("KCCQ", 5, 1.2)]}]],
  ["unrelated PRIMARY metadata does not disambiguate typed MDs", () =>
    [{allOutcomes: [{type: "PRIMARY", shortLabel: "safety"},
                    outcome("MMSE", -2, 0.5), outcome("KCCQ", 5, 1.2)]}, singleB()]],
];
const accepted = [
  ["one verified-style MD per independent study", singleA, singleB, "MD"],
  ["valid binary two-by-two controls", binaryA, binaryB, "OR"],
  ["single MD plus unrelated non-HR PRIMARY row",
    () => ({allOutcomes: [outcome("MMSE", -2, 0.5),
                         {type: "PRIMARY", shortLabel: "safety"}]}),
    singleB, "MD"],
];
let scenarios = 0;
for (let i = 0; i < sources.length; i++) {
  for (const [name, inputs] of refused) {
    for (const reverse of [false, true]) {
      const [a, b] = inputs();
      const panel = exercise(sources[i], a, b, reverse);
      const label = copies[i] + ": " + name + " reverse=" + reverse;
      assert.match(panel.summary, /^Refused: multiple continuous effect records/, label);
      assert.match(panel.bodyHtml, /role="alert"/, label);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      scenarios++;
    }
  }
  for (const [name, a, b, scale] of accepted) {
    for (const reverse of [false, true]) {
      const panel = exercise(sources[i], a(), b(), reverse);
      const label = copies[i] + ": " + name + " reverse=" + reverse;
      assert.match(panel.summary, new RegExp("^" + scale + " scale"), label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.doesNotMatch(panel.summary, /^Refused:/, label);
      scenarios++;
    }
  }
}
assert.equal(scenarios, 54);
console.log("PASS: 54 source-executed SUCRA multiple-continuous-outcome cases; not an R oracle.");
