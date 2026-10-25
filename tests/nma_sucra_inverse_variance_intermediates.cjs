"use strict";
// Synthesis | Hourly Statistical Parity
// Cochrane Handbook 10.3: inverse-variance DL pooling requires representable
// weighted sums and heterogeneity quantities, not merely finite per-trial SE.
// These are synthetic numerical-refusal tests, NOT native R/metafor parity.
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
for (let i = 1; i < sources.length; i++) {
  assert.equal(sources[i], sources[0], paths[i] + ": source drift");
}
const md = (value, se) => ({ allOutcomes: [{ type: "CONTINUOUS", md: value, se }] });
const binary = (tE, tN, cE, cN) => ({ tE, tN, cE, cN });
function exercise(src, trials, second, reversed = false) {
  const panels = [];
  const rd = { b: second };
  trials.forEach((trial, i) => { rd["a" + i] = trial; });
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: { comp: "C", out: "MMSE" },
      comparisons: [
        { t1: reversed ? "C" : "A", t2: reversed ? "A" : "C",
          trials: trials.map((_, i) => "a" + i) },
        { t1: "B", t2: "C", trials: ["b"] },
      ],
    },
    PanelHelper: {
      getRealData() { return rd; },
      fmt(n, digits) { return Number(n).toFixed(digits); },
      buildCollapsiblePanel(panel) { panels.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading", addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected panel timer"); },
  };
  context.window = context;
  vm.runInNewContext(src, context, { timeout: 10000 });
  assert.equal(context.NMASUCRA.render(), true);
  assert.equal(panels.length, 1, "exactly one result or refusal");
  return panels[0];
}
const refused = [
  ["sum of individually finite weights overflows", [md(1, 1e-154), md(2, 1e-154)]],
  ["sum of individually finite squared weights overflows", [md(1, 1e-100), md(2, 1e-100)]],
  ["sum of squared weights underflows", [md(1, 1e154), md(2, 1e154)]],
  ["Q overflows from otherwise valid effects", [md(1e200, 1), md(-1e200, 1)]],
  ["weighted effect sum overflows", [md(1e308, 1), md(1e308, 1)]],
  ["identical effects still overflow total weights", [md(0, 1e-154), md(0, 1e-154)]],
];
const accepted = [
  ["ordinary DL MD", [md(1, 0.5), md(2, 0.6)], md(0.5, 0.3), "MD"],
  ["large but representable MD weights", [md(1, 1e-30), md(2, 1e-30)], md(0.5, 0.3), "MD"],
  ["single high-precision MD", [md(1, 1e-154)], md(0.5, 0.3), "MD"],
  ["ordinary binary OR", [binary(3, 30, 7, 30), binary(4, 40, 8, 40)],
    binary(2, 20, 5, 20), "OR"],
];
let passed = 0;
for (const [i, src] of sources.entries()) {
  for (const [name, rows] of refused) {
    for (const reversed of [false, true]) {
      const panel = exercise(src, rows, md(0.5, 0.3), reversed);
      const label = paths[i] + ": " + name + " reversed=" + reversed;
      assert.match(panel.summary, /^Refused: non-finite inverse-variance pooling intermediates/, label);
      assert.match(panel.bodyHtml, /role="alert"/, label);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      passed++;
    }
  }
  for (const [name, rows, b, scale] of accepted) {
    for (const reversed of [false, true]) {
      const panel = exercise(src, rows, b, reversed);
      const label = paths[i] + ": " + name + " reversed=" + reversed;
      assert.match(panel.summary, new RegExp("^" + scale + " scale"), label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.doesNotMatch(panel.bodyHtml, />NaN<|>Infinity</, label);
      passed++;
    }
  }
}
assert.equal(passed, 60);
console.log("PASS: 60 source-executed SUCRA inverse-variance intermediate guard scenarios; no native R parity claimed.");
