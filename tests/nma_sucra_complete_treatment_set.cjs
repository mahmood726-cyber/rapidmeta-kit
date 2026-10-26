"use strict";
// Synthesis | Hourly Statistical Parity — complete treatment-set integrity.
// Cochrane Handbook Chapter 11, §§11.4.3.3 and 11.6.4.1:
// https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-11
// Browser behavior/negative tests, NOT independent method-matched R parity.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const paths = ["assets/vendor/nma-sucra.js", "docs/assets/vendor/nma-sucra.js", "template/assets/vendor/nma-sucra.js"];
const sources = paths.map(p => fs.readFileSync(path.join(root, p), "utf8"));
assert.equal(sources[1], sources[0], "docs implementation differs from canonical");
assert.equal(sources[2], sources[0], "template implementation differs from canonical");

const scenarios = [
  {name:"configured C comparison absent", noComparison:"C", expected:"missing"},
  {name:"configured C has empty trials", emptyTrials:"C", expected:"missing"},
  {name:"configured C has no typed outcome", missingEffect:"C", expected:"missing"},
  {name:"configured C has empty outcome array", emptyOutcomes:"C", expected:"missing"},
  {name:"three treatments, only A evaluable", treatments:["Placebo","A","C"], missingEffect:"C", expected:"missing"},
  {name:"four-treatment valid MD star", expected:"validMD"},
  {name:"four-treatment valid OR star with zero events", binary:true, expected:"validOR"},
  {name:"invalid continuous still gets specific refusal", invalidContinuous:"C", expected:"invalidContinuous"},
  {name:"invalid binary still gets specific refusal", invalidBinary:"C", expected:"invalidBinary"},
  {name:"unresolved study reference still gets specific refusal", unresolved:"C", expected:"unresolved"},
  {name:"unmatched comparator still gets specific refusal", badComp:"not a treatment", expected:"comparator"},
];
function exercise(source, fx, reversed) {
  const panels = [], rd = {}, comparisons = [];
  const treatments = fx.treatments || ["Placebo","A","B","C"];
  for (const T of treatments) {
    if (T === "Placebo" || fx.noComparison === T) continue;
    const id = "trial_" + T;
    if (fx.unresolved !== T) {
      rd[id] = fx.invalidContinuous === T
        ? {allOutcomes:[{type:"CONTINUOUS",md:1,se:-1}]}
        : fx.invalidBinary === T
        ? {tE:-1,tN:20,cE:3,cN:20}
        : fx.missingEffect === T
        ? {allOutcomes:[{type:"PRIMARY",shortLabel:"MMSE",pubMean:3}]}
        : fx.emptyOutcomes === T
        ? {allOutcomes:[]}
        : fx.binary
        ? {tE:T === "A" ? 0 : 2,tN:20,cE:4,cN:20}
        : {allOutcomes:[{type:"CONTINUOUS",md:1,se:0.5}]};
    }
    comparisons.push({t1:reversed ? "Placebo" : T, t2:reversed ? T : "Placebo",
      trials:fx.emptyTrials === T ? [] : [id]});
  }
  const ctx = {
    NMA_CONFIG:{treatments,protocol:{comp:fx.badComp || "Placebo",out:"MMSE"},comparisons},
    PanelHelper:{
      getRealData(){return rd;},
      fmt(x,n){return Number(x).toFixed(n);},
      buildCollapsiblePanel(panel){panels.push(panel);return {};},
      insertAfterRBadge(){},
    },
    document:{readyState:"loading",addEventListener(){},getElementById(){return null;}},
    setTimeout(){throw Error("Unexpected timer");},
  };
  ctx.window=ctx;
  vm.runInNewContext(source,ctx,{timeout:10000});
  assert.equal(ctx.NMASUCRA.render(),true,fx.name+": did not render");
  assert.equal(panels.length,1,fx.name+": unexpected panel count");
  return panels[0];
}
let passed=0;
for(let copy=0;copy<sources.length;copy++){
  for(const fx of scenarios)for(const reversed of [false,true]){
    const panel=exercise(sources[copy],fx,reversed);
    const label=paths[copy]+": "+fx.name+": reversed="+reversed;
    if(fx.expected==="missing"){
      assert.match(panel.summary,/^Refused: configured treatments lack usable direct effects/,label);
      assert.match(panel.bodyHtml,/No SUCRA, treatment hierarchy or pooled result was computed/,label);
      assert.match(panel.bodyHtml,/role="alert"/,label);
      assert.doesNotMatch(panel.bodyHtml,/Per-treatment ranking summaries:|Top-ranked:/,label);
    }else{
      const prefix={
        validMD:"MD scale",validOR:"OR scale",
        invalidContinuous:"Refused: invalid continuous",
        invalidBinary:"Refused: invalid binary",
        unresolved:"Refused: unresolved trial references",
        comparator:"Refused: protocol comparator",
      }[fx.expected];
      assert.ok(panel.summary.startsWith(prefix),label+": "+panel.summary);
      if(fx.expected==="validMD"||fx.expected==="validOR"){
        assert.match(panel.summary,/4 treatments/,label);
        assert.match(panel.bodyHtml,/Per-treatment ranking summaries:/,label);
        assert.match(panel.bodyHtml,/>C</,label);
      }
    }
    passed++;
  }
}
assert.equal(passed,66);
console.log("PASS: 66 complete-treatment-set source-executed regression/negative scenarios (no R parity).");
