"use strict";
// Synthesis | Hourly Statistical Parity: explicit protocol reference integrity.
// Cochrane Handbook Ch.3: synthesis comparator definitions are prespecified.
// Behavioral fixtures, NOT fitted NMA or independent native R statistical parity.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const paths = ["assets/vendor/nma-sucra.js", "docs/assets/vendor/nma-sucra.js", "template/assets/vendor/nma-sucra.js"];
const sources = paths.map(p => fs.readFileSync(path.join(root, p), "utf8"));
assert.equal(sources[1], sources[0], "docs source differs");
assert.equal(sources[2], sources[0], "template source differs");
const cases = [
  {name:"unavailable explicit comparator", comp:"Control unavailable", center:"Placebo", refuse:true},
  {name:"partial comparator", comp:"Plac", center:"Placebo", refuse:true},
  {name:"free-text PICO comparator", comp:"Placebo plus usual care", center:"Placebo", refuse:true},
  {name:"whitespace-only comparator", comp:"   ", center:"Placebo", refuse:true},
  {name:"numeric comparator", comp:12, center:"Placebo", refuse:true},
  {name:"object comparator", comp:{name:"Placebo"}, center:"Placebo", refuse:true},
  {name:"duplicate normalized labels", comp:"PLACEBO", center:"Placebo", refuse:true,
   treatments:["Placebo", "placebo", "A"]},
  {name:"exact non-placebo reference", comp:"A", center:"A", refuse:false},
  {name:"case and whitespace normalized", comp:" pLaCeBo ", center:"Placebo", refuse:false},
  {name:"empty field legacy default", comp:"", center:"Placebo", refuse:false},
  {name:"missing field legacy default", omit:true, center:"Placebo", refuse:false},
  {name:"binary invalid reference", comp:"Not a treatment", center:"Placebo", refuse:true, binary:true},
  {name:"binary valid zero-cell", comp:"Placebo", center:"Placebo", refuse:false, binary:true},
];
function exercise(src, scenario, reversed) {
  const treatments = scenario.treatments || ["Placebo", "A", "B"];
  const realData = {}, comparisons = [], panels = []; let i = 0;
  for (const treatment of treatments) {
    if (treatment === scenario.center) continue;
    const id = "trial_" + i;
    realData[id] = scenario.binary
      ? {tE:i === 0 ? 0 : 3, tN:20, cE:2, cN:20}
      : {allOutcomes:[{type:"CONTINUOUS", md:0.3 + 0.2 * i, se:0.35}]};
    comparisons.push({t1:reversed?scenario.center:treatment, t2:reversed?treatment:scenario.center, trials:[id]});
    i++;
  }
  const protocol = {out:"MMSE"};
  if (!scenario.omit) protocol.comp = scenario.comp;
  const ctx = {
    NMA_CONFIG:{treatments, protocol, comparisons},
    PanelHelper:{
      getRealData() {return realData;},
      fmt(v,n) {return Number(v).toFixed(n);},
      buildCollapsiblePanel(p) {panels.push(p); return {};},
      insertAfterRBadge() {},
    },
    document:{readyState:"loading",addEventListener() {},getElementById() {return null;}},
    setTimeout() {throw Error("Unexpected timer");},
  };
  ctx.window = ctx;
  vm.runInNewContext(src, ctx, {timeout:10000});
  assert.equal(ctx.NMASUCRA.render(), true, "expected result or refusal");
  assert.equal(panels.length, 1);
  return panels[0];
}
let passed = 0;
for (let i = 0; i < sources.length; i++) {
  for (const c of cases) {
    for (const reversed of [false, true]) {
      const panel = exercise(sources[i], c, reversed);
      const label = paths[i] + ": " + c.name + ": reversed=" + reversed;
      if (c.refuse) {
        assert.match(panel.summary, /^Refused: protocol comparator does not uniquely match a treatment/, label);
        assert.match(panel.bodyHtml, /role="alert"/, label);
        assert.match(panel.bodyHtml, /No SUCRA, treatment hierarchy or pooled result was computed/, label);
        assert.doesNotMatch(panel.bodyHtml, /Per-treatment ranking summaries:|Top-ranked:/, label);
      } else {
        assert.match(panel.summary, new RegExp("^" + (c.binary ? "OR" : "MD") + " scale"), label);
        assert.match(panel.bodyHtml, /Per-treatment ranking summaries:/, label);
        assert.ok(panel.bodyHtml.includes("Reference: <code>" + c.center + "</code>"), label);
      }
      passed++;
    }
  }
}
assert.equal(passed, 78);
console.log("PASS: 78 source-executed protocol comparator identification cases (behavioral; no R parity).");
