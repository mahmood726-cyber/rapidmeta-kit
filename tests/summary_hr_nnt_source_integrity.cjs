'use strict';
// Original, synthetic, fail-closed summary-HR and NNT-source tests.
// Not a native R/metafor parity test or clinical validation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const dirs = ['assets/vendor', 'docs/assets/vendor', 'template/assets/vendor'];
const root = path.resolve(__dirname, '..');
function engine(source) {
  const w = {};
  new Function('window', source)(w);
  return w.RapidMetaSurvival;
}
function panel(source, surv, data) {
  let record = null;
  let inserted = 0;
  const P = {
    getRealData: () => data,
    fmt: (v, n) => Number(v).toFixed(n),
    buildCollapsiblePanel: o => { record = o; return {replaceWith(){inserted++;}}; },
    insertAfterRBadge(){inserted++;}
  };
  const w = {PanelHelper: P, RapidMetaSurvival: surv};
  const d = {getElementById:()=>null, readyState:'loading', addEventListener(){}};
  new Function('window', 'document', 'setTimeout', 'console', source)(w, d, ()=>{}, {warn(){}});
  const rendered = w.HRNNTPanel.render();
  return {rendered, inserted, ...record};
}
const a = {HR:0.80, HR_ci_lo:0.60, HR_ci_hi:1.05, events_ctl:20, n_ctl:100, estimandType:'HR'};
const b = {HR:'0.75', HR_ci_lo:'6e-1', HR_ci_hi:'9e-1', events_ctl:20, n_ctl:100, estimandType:'HR'};
const bad = [
  ['boolean', {HR:true}],
  ['array', {HR:[0.75]}],
  ['null', {HR:null}],
  ['blank', {HR:''}],
  ['hex', {HR:'0x1'}],
  ['binary', {HR:'0b1'}],
  ['octal', {HR:'0o1'}],
  ['negative', {HR:-1}],
  ['central effect outside CI', {HR:2}],
  ['inverted CI', {HR_ci_lo:2}],
  ['malformed upper CI', {HR_ci_hi:true}],
  ['missing upper CI', {HR_ci_hi:undefined}],
  ['not a hazard ratio', {estimandType:'RR'}]
];
let count = 0;
for (const dir of dirs) {
  const s = fs.readFileSync(path.join(root,dir,'rapidmeta-survival.js'), 'utf8');
  const p = fs.readFileSync(path.join(root,dir,'hr-nnt-panel.js'), 'utf8');
  const surv = engine(s);
  const fit = surv.fit([a,b]);
  assert.ok(fit && fit.k === 2 && Number.isFinite(fit.pooled_HR), dir+' valid fit');
  count++;
  const r = panel(p,surv,{A:a,B:b});
  assert.ok(r.rendered && r.inserted === 1 && r.summary.includes('k=2') &&
            !r.bodyHtml.includes('role="alert"'),dir+' valid NNT panel');
  count++;
  for (const [name, mutation] of bad) {
    const changed = {...a,...mutation};
    assert.equal(surv.fit([b,changed]),null,dir+' low-level must refuse '+name);
    count++;
    const displayed = panel(p,surv,{A:b,B:changed});
    if (name === 'not a hazard ratio') {
      assert.ok(!displayed.rendered || displayed.bodyHtml.includes('role="alert"'),
                dir+' must not pool RR/OR as HR');
    } else {
      assert.ok(displayed.rendered && displayed.inserted===1 &&
                displayed.bodyHtml.includes('role="alert"') &&
                !displayed.summary.includes('NNTB'),dir+' panel must visibly refuse '+name);
    }
    count++;
  }
  for (const [kind, badType] of [
    ['false', false], ['zero', 0], ['null', null], ['array', []],
    ['blank', '   ']
  ]) {
    const typed = {...a, estimandType:badType};
    assert.equal(surv.fit([b,typed]),null,dir+' engine rejects '+kind+' effect type');
    count++;
    const refused = panel(p,surv,{A:b,B:typed});
    assert.ok(refused.rendered && refused.bodyHtml.includes('role="alert"'),
              dir+' visible refusal for '+kind+' effect type');
    count++;
  }
  for (const [kind, broken] of [['null',null],['array',[]],['string','broken']]) {
    const refused = panel(p,surv,{A:a,B:b,C:broken});
    assert.ok(refused.rendered && refused.bodyHtml.includes('role="alert"'),
              dir+' rejects malformed '+kind+' record without silently reducing k');
    count++;
  }
  let displayed = panel(p,surv,{A:a,B:{...a,HR:-1},C:b});
  assert.ok(displayed.rendered && displayed.bodyHtml.includes('role="alert"'),
            dir+' cannot silently shrink k=3 to k=2');
  count++;
  displayed = panel(p,surv,{A:a,B:{...b,HR:true,publishedHR:0.75}});
  assert.ok(displayed.rendered && displayed.bodyHtml.includes('role="alert"'),
            dir+' cannot fall back from malformed primary HR');
  count++;
  displayed = panel(p,surv,{A:a,B:{...b,HR_ci_lo:null,hrLCI:0.6}});
  assert.ok(displayed.rendered && displayed.bodyHtml.includes('role="alert"'),
            dir+' cannot fall back from malformed primary CI');
  count++;
  displayed = panel(p,surv,{A:a,B:{...b,events_ctl:22.5}});
  assert.ok(displayed.rendered && displayed.bodyHtml.includes('role="alert"'),
            dir+' must reject malformed explicit comparator baseline');
  count++;
}
console.log('SUMMARY-HR/NNT SOURCE GUARD PASS: '+count+' assertions across '+dirs.length+' shipped copies');
