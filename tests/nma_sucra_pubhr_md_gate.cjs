"use strict";
// Synthesis | Hourly Statistical Parity
// Refusal of unverified pubHR -> MD conversion, Cochrane Handbook ch. 6.
// This tests the browser gate with synthetic fixtures, NOT native R parity.
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
  assert.equal(src, sources[0], "Shipped SUCRA sources must remain byte-identical: " + paths[i+1]));

const md = { allOutcomes: [{ type: "CONTINUOUS", md: -2, se: 0.6 }] };
const hr = { allOutcomes: [{ type: "PRIMARY", shortLabel: "MMSE",
  pubHR: 0.80, pubHR_LCI: 0.70, pubHR_UCI: 0.90 }] };
const incompleteHr = { allOutcomes: [{ type: "PRIMARY", shortLabel: "MMSE", pubHR: 0.80 }] };
const mdPlusHr = { allOutcomes: [...md.allOutcomes, ...hr.allOutcomes] };
const or = { tE: 3, tN: 20, cE: 7, cN: 20 };

function render(code, first, second, reversed = false) {
  const panels = [];
  const config = {
    treatments: ["A", "B", "C"],
    protocol: { comp: "C", out: "MMSE" },
    comparisons: [
      { t1: reversed ? "C" : "A", t2: reversed ? "A" : "C", trials: ["a"] },
      { t1: "B", t2: "C", trials: ["b"] },
    ],
  };
  const data = { a: JSON.parse(JSON.stringify(first)), b: JSON.parse(JSON.stringify(second)) };
  const context = {
    NMA_CONFIG: config,
    PanelHelper: {
      getRealData() { return data; },
      fmt(n, places) { return Number(n).toFixed(places); },
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
  vm.runInNewContext(code, context);
  assert.equal(context.NMASUCRA.render(), true);
  assert.equal(panels.length, 1);
  return panels[0];
}
const cases = [
  ["two legacy pubHR records", hr, hr, true],
  ["ratio fields mixed with explicit MD", hr, md, true],
  ["ratio fields mixed with OR", hr, or, true],
  ["incomplete ratio fields", incompleteHr, md, true],
  ["reversed edge orientation", hr, md, true, true],
  ["explicit continuous MD", md, md, false],
  ["explicit MD overrides ambiguous legacy fallback", mdPlusHr, md, false],
  ["valid binary OR", or, or, false],
];
let passed = 0;
for (const [copyIndex, source] of sources.entries()) {
  for (const [name, first, second, refusal, reversed] of cases) {
    const panel = render(source, first, second, reversed);
    const label = paths[copyIndex] + ": " + name;
    if (refusal) {
      assert.match(panel.summary, /^Refused: published HR fields cannot be treated as mean differences/, label);
      assert.match(panel.bodyHtml, /role="alert"/, label);
      assert.match(panel.bodyHtml, /No SUCRA, hierarchy or pooled result was computed/, label);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
    } else {
      assert.match(panel.summary, /^(OR|MD) scale/, label);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      assert.doesNotMatch(panel.summary, /^Refused:/, label);
    }
    passed++;
  }
}
assert.equal(passed, cases.length * paths.length);
console.log("PASS: " + passed + " source-executed pubHR/MD refusal scenarios; no native R parity claimed.");
