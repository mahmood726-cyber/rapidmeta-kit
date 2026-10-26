"use strict";
// Synthesis | Hourly Statistical Parity — double-zero/double-all relative-OR safeguard.
// Cochrane Handbook current Ch 10 §10.4.4.2 and Ch 6 §6.4.1.2.
// These are synthetic, source-executed UI safeguards; NOT independent R parity.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const paths = ["assets/vendor/nma-sucra.js", "docs/assets/vendor/nma-sucra.js", "template/assets/vendor/nma-sucra.js"];
const sources = paths.map(p => fs.readFileSync(path.join(root,p),"utf8"));
assert.equal(sources[1],sources[0],"docs copy must be identical");
assert.equal(sources[2],sources[0],"template copy must be identical");
const ordinary = {tE:3,tN:40,cE:7,cN:40};
const cases = [
 {name:"double-zero unequal allocation",a:{tE:0,tN:100,cE:0,cN:20},refuse:true},
 {name:"double-zero balanced allocation",a:{tE:0,tN:50,cE:0,cN:50},refuse:true},
 {name:"double-all unequal allocation",a:{tE:100,tN:100,cE:20,cN:20},refuse:true},
 {name:"double-all balanced allocation",a:{tE:50,tN:50,cE:50,cN:50},refuse:true},
 {name:"double-zero in second comparison",a:ordinary,b:{tE:0,tN:100,cE:0,cN:20},refuse:true},
 {name:"double-all in second comparison",a:ordinary,b:{tE:100,tN:100,cE:20,cN:20},refuse:true},
 {name:"double-zero cannot masquerade as MD",a:{tE:0,tN:100,cE:0,cN:20,allOutcomes:[{type:"CONTINUOUS",md:1,se:0.2}]},refuse:true},
 {name:"double-all cannot masquerade as MD",a:{tE:100,tN:100,cE:20,cN:20,allOutcomes:[{type:"CONTINUOUS",md:1,se:0.2}]},refuse:true},
 {name:"single-zero intervention positive control",a:{tE:0,tN:100,cE:5,cN:20},scale:"OR"},
 {name:"single-zero comparator positive control",a:{tE:5,tN:100,cE:0,cN:20},scale:"OR"},
 {name:"single-all intervention positive control",a:{tE:100,tN:100,cE:5,cN:20},scale:"OR"},
 {name:"ordinary OR positive control",a:ordinary,scale:"OR"},
 {name:"independent MD positive control",a:{allOutcomes:[{type:"CONTINUOUS",md:1,se:0.5}]},b:{allOutcomes:[{type:"CONTINUOUS",md:2,se:0.5}]},scale:"MD"},
];
function exercise(source,c,reversed){
 const panels=[];
 const rd={a:c.a,b:c.b||{...ordinary}};
 const context={
   NMA_CONFIG:{
     treatments:["Placebo","A","B"],
     protocol:{comp:"Placebo",out:"mortality"},
     comparisons:["A","B"].map((t,i)=>({
       t1:reversed?"Placebo":t, t2:reversed?t:"Placebo",
       trials:[i?"b":"a"],
     })),
   },
   PanelHelper:{
     getRealData(){return rd;},
     fmt(x,n){return Number(x).toFixed(n);},
     buildCollapsiblePanel(p){panels.push(p);return {};},
     insertAfterRBadge(){},
   },
   document:{readyState:"loading",addEventListener(){},getElementById(){return null;}},
   setTimeout(){throw Error("unexpected timer");},
 };
 context.window=context;
 vm.runInNewContext(source,context,{timeout:10000});
 assert.equal(context.NMASUCRA.render(),true,c.name+": render must produce visible outcome");
 assert.equal(panels.length,1,c.name+": expected one panel");
 return panels[0];
}
let passed=0;
for(const [i,source] of sources.entries()){
 for(const c of cases)for(const reversed of [false,true]){
   const p=exercise(source,c,reversed);
   const label=paths[i]+" "+c.name+" reversed="+reversed;
   if(c.refuse){
     assert.match(p.summary,/^Refused: double-zero or double-all-event studies lack relative OR information/,label);
     assert.match(p.bodyHtml,/role="alert"/,label);
     assert.match(p.bodyHtml,/No SUCRA, treatment hierarchy or pooled result was computed/,label);
     assert.doesNotMatch(p.bodyHtml,/Per-treatment ranking summaries:|Top-ranked:/,label);
   }else{
     assert.match(p.summary,new RegExp("^"+c.scale+" scale"),label);
     assert.match(p.bodyHtml,/Per-treatment ranking summaries:/,label);
     assert.doesNotMatch(p.summary,/^Refused:/,label);
   }
   passed++;
 }
}
assert.equal(passed,78);
console.log("PASS: 78 source-executed double-zero/double-all OR refusal/positive-control scenarios (not R parity).");
