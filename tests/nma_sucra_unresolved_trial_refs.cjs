"use strict";
// Synthesis | Hourly Statistical Parity: missing study references must not
// silently shrink the analysed evidence set (Cochrane Handbook 10.12).
// These source-executed browser-gate cases are NOT native R numerical parity.
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
  assert.equal(sources[i], sources[0], paths[i] + ": JS source drift");
}
function exercise(src, scenario, reversed) {
  const md = effect => ({allOutcomes: [{type: "CONTINUOUS", md: effect, se: 0.25}]});
  const binary = events => ({tE: events, tN: 20, cE: 2, cN: 20});
  const rd = {
    trial_A: scenario.binary ? binary(0) : md(0.4),
    trial_B: scenario.binary ? binary(3) : md(0.8),
    ...(scenario.extraData || {}),
  };
  const refsA = [scenario.inline ? rd.trial_A : "trial_A", ...(scenario.extraA || [])];
  const refsB = [scenario.inline ? rd.trial_B : "trial_B", ...(scenario.extraB || [])];
  const panels = [];
  const ctx = {
    NMA_CONFIG: {
      treatments: ["Placebo", "A", "B"],
      protocol: {comp: "Placebo", out: "MMSE"},
      comparisons: [
        {t1: reversed ? "Placebo" : "A", t2: reversed ? "A" : "Placebo", trials: refsA},
        {t1: reversed ? "Placebo" : "B", t2: reversed ? "B" : "Placebo", trials: refsB},
      ],
    },
    PanelHelper: {
      getRealData() {return rd;},
      fmt(v, n) {return Number(v).toFixed(n);},
      buildCollapsiblePanel(panel) {panels.push(panel); return {};},
      insertAfterRBadge() {},
    },
    document: {readyState: "loading", addEventListener() {}, getElementById() {return null;}},
    setTimeout() {throw Error("Unexpected timer in isolated render");},
  };
  ctx.window = ctx;
  vm.runInNewContext(src, ctx, {timeout: 10000});
  assert.equal(ctx.NMASUCRA.render(), true, scenario.name + ": panel must render");
  assert.equal(panels.length, 1, scenario.name + ": exactly one panel");
  return panels[0];
}
const scenarios = [
  {name: "missing A reference", extraA: ["UNKNOWN_A"], refuse: true},
  {name: "missing B reference", extraB: ["UNKNOWN_B"], refuse: true},
  {name: "missing both", extraA: ["UNKNOWN_A"], extraB: ["UNKNOWN_B"], refuse: true},
  {name: "lookup resolves to null", extraA: ["null_record"], extraData: {null_record: null}, refuse: true},
  {name: "lookup resolves to primitive", extraA: ["primitive"], extraData: {primitive: 3}, refuse: true},
  {name: "inline null is invalid", extraB: [null], refuse: true},
  {name: "inline false is invalid", extraB: [false], refuse: true},
  {name: "complete references preserve MD ranking", refuse: false},
  {name: "complete inline records preserve MD ranking", inline: true, refuse: false},
  {name: "valid binary zero events preserve OR ranking", binary: true, refuse: false},
];
let passed = 0;
for (let i = 0; i < sources.length; i++) {
  for (const scenario of scenarios) {
    for (const reversed of [false, true]) {
      const panel = exercise(sources[i], scenario, reversed);
      const label = paths[i] + " " + scenario.name + " reversed=" + reversed;
      if (scenario.refuse) {
        assert.match(panel.summary, /^Refused: unresolved trial references in direct comparisons/, label);
        assert.match(panel.bodyHtml, /role="alert"/, label);
        assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
        assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      } else {
        assert.match(panel.summary, new RegExp("^" + (scenario.binary ? "OR" : "MD") + " scale"), label);
        assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
      }
      passed++;
    }
  }
}
assert.equal(passed, 60);
console.log("PASS: 60 source-executed unresolved-reference gate scenarios (synthetic; no R parity).");
