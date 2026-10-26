"use strict";
// Exercises actual shipped SUCRA panels; fixtures are structural, NOT external R validation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.join(__dirname, "..");
const copies = [
  "assets/vendor/nma-sucra.js",
  "docs/assets/vendor/nma-sucra.js",
  "template/assets/vendor/nma-sucra.js",
];
const source = fs.readFileSync(path.join(root, copies[0]), "utf8");
for (const copy of copies.slice(1)) {
  assert.equal(fs.readFileSync(path.join(root, copy), "utf8"), source,
               "shipped SUCRA copies must remain byte-identical: " + copy);
}

function makeTrial(effectType) {
  if (effectType === "OR") return {tE: 4, tN: 100, cE: 8, cN: 100};
  if (effectType === "MD") return {allOutcomes: [{type: "CONTINUOUS", md: -2, se: 0.5}]};
  throw Error("unknown fixture effect type");
}
function exercise(code, kindA, kindB) {
  const evidence = {};
  kindA.forEach((kind, i) => { evidence["A" + i] = makeTrial(kind); });
  kindB.forEach((kind, i) => { evidence["B" + i] = makeTrial(kind); });
  const captured = [];
  const context = {
    NMA_CONFIG: {
      treatments: ["A", "B", "C"],
      protocol: {comp: "C", out: "mortality"},
      comparisons: [
        {t1: "A", t2: "C", trials: kindA.map((_, i) => "A" + i)},
        {t1: "B", t2: "C", trials: kindB.map((_, i) => "B" + i)},
      ],
    },
    PanelHelper: {
      getRealData() { return evidence; },
      fmt(value, places) { return Number(value).toFixed(places); },
      buildCollapsiblePanel(panel) { captured.push(panel); return {}; },
      insertAfterRBadge() {},
    },
    document: {
      readyState: "loading",
      addEventListener() {}, // do not schedule an auto-bootstrap run
      getElementById() { return null; },
    },
    setTimeout() { throw Error("unexpected timer in test"); },
  };
  context.window = context;
  vm.runInNewContext(code, context);
  const rendered = context.NMASUCRA.render();
  assert.equal(rendered, true);
  assert.equal(captured.length, 1);
  return captured[0];
}
const cases = [
  {name: "OR and MD across treatments", a: ["OR"], b: ["MD"], refuse: true},
  {name: "MD and OR reversed treatment order", a: ["MD"], b: ["OR"], refuse: true},
  {name: "OR and MD within one treatment", a: ["OR", "MD"], b: ["OR"], refuse: true},
  {name: "OR-only baseline", a: ["OR"], b: ["OR"], refuse: false, scale: "OR"},
  {name: "MD-only baseline", a: ["MD"], b: ["MD"], refuse: false, scale: "MD"},
];
for (const copy of copies) {
  const code = fs.readFileSync(path.join(root, copy), "utf8");
  for (const test of cases) {
    const panel = exercise(code, test.a, test.b);
    const context = copy + " / " + test.name;
    if (test.refuse) {
      assert.match(panel.summary, /^Refused: incompatible OR and MD/, context);
      assert.match(panel.bodyHtml, /role="alert"/, context);
      assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result/, context);
      assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:/, context);
      assert.doesNotMatch(panel.bodyHtml, /Top-ranked:/, context);
    } else {
      assert.match(panel.summary, new RegExp("^" + test.scale + " scale"), context);
      assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, context);
      assert.doesNotMatch(panel.summary, /Refused/, context);
    }
  }
}
console.log("PASS: 15 actual-panel scenarios across 3 shipped copies (3 refusals + 2 controls per copy).");
