"use strict";
// Synthesis | Hourly Statistical Parity: protocol reference priority.
// Cochrane Handbook 11.4.1: relative treatment effects use a chosen reference.
// Synthetic browser source-execution tests; NOT version-pinned native R parity.
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
function exercise(src, treatments, comp, center, reversed) {
  const panels = [];
  const trials = {};
  const comparisons = [];
  let n = 0;
  for (const name of treatments) {
    if (name === center) continue;
    const id = "trial_" + n;
    trials[id] = { allOutcomes: [{ type: "CONTINUOUS", md: 0.3 + n * 0.2, se: 0.4 }] };
    comparisons.push({
      t1: reversed ? center : name,
      t2: reversed ? name : center,
      trials: [id],
    });
    n++;
  }
  const ctx = {
    NMA_CONFIG: {
      treatments,
      protocol: { comp, out: "MMSE" },
      comparisons,
    },
    PanelHelper: {
      getRealData() { return trials; },
      fmt(value, digits) { return Number(value).toFixed(digits); },
      buildCollapsiblePanel(panel) { panels.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading", addEventListener() {},
      getElementById() { return null; },
    },
    setTimeout() { throw Error("Unexpected timer"); },
  };
  ctx.window = ctx;
  vm.runInNewContext(src, ctx, { timeout: 10000 });
  assert.equal(ctx.NMASUCRA.render(), true, "render should show a result or refusal");
  assert.equal(panels.length, 1, "exactly one result or refusal");
  return panels[0];
}
const scenarios = [
  // Negative controls: the old code incorrectly used the first placebo,
  // overriding an explicitly named *different* comparator in the protocol.
  ["named C wins over first placebo: non-reference edge must be refused",
    ["Placebo", "A", "C"], "C", "Placebo", true],
  ["named Control wins over first placebo: omitted edge must be refused",
    ["Placebo", "Control", "A"], "Control", "Placebo", true],
  // Positive controls: after choosing the specified reference all edges are direct.
  ["named C wins over first placebo: C-star can be analysed",
    ["Placebo", "A", "C"], "C", "C", false],
  ["named Control wins over first placebo: Control-star can be analysed",
    ["Placebo", "Control", "A"], "Control", "Control", false],
  ["case and outer whitespace are irrelevant to exact reference matching",
    ["Placebo", "A", "C"], " c ", "C", false],
  ["explicit placebo remains a valid reference",
    ["Placebo", "A", "C"], "Placebo", "Placebo", false],
  ["missing protocol comparator preserves the existing placebo heuristic",
    ["Placebo", "A", "C"], "", "Placebo", false],
];
let passed = 0;
for (const [i, src] of sources.entries()) {
  for (const [name, ts, comp, center, refused] of scenarios) {
    for (const reversed of [false, true]) {
      const panel = exercise(src, ts, comp, center, reversed);
      const label = paths[i] + ": " + name + " reversed=" + reversed;
      if (refused) {
        assert.match(panel.summary, /^Refused: network comparisons omitted by direct-only ranking/, label);
        assert.match(panel.bodyHtml, /role="alert"/, label);
        assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled estimate was computed/, label);
        assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      } else {
        assert.match(panel.summary, /^MD scale/, label);
        assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
        assert.ok(panel.bodyHtml.includes("Reference: <code>" + center + "</code>"), label);
      }
      passed++;
    }
  }
}
assert.equal(passed, 42);
console.log("PASS: 42 source-executed explicit reference comparator scenarios; no native R parity claimed.");
