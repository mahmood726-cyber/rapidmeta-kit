"""Effect-type safety for the experimental interval-HR pool.

Synthetic source-executed positive/negative regressions across three shipped
JavaScript copies. Not an external R oracle or a clinical-data validation.
Cochrane Handbook Ch 6 (effect measure consistency):
https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-06
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NODE = r"""
'use strict';
const fs = require('fs');
const assert = require('node:assert/strict');
const path = require('path');
const copies = ['assets/vendor', 'docs/assets/vendor', 'template/assets/vendor'];
function trial(id, type) {
  return {studyId: id, estimandType: type,
    intervals: [{t0: 0, t1: 6, HR: 0.8, HR_ci_lo: 0.6, HR_ci_hi: 1.1}]};
}
let cases = 0;
for (const dir of copies) {
  const code = fs.readFileSync(path.join(process.cwd(), dir, 'rapidmeta-survival.js'), 'utf8');
  const sandbox = {};
  new Function('window', code)(sandbox);
  const pool = sandbox.RapidMetaSurvival.intervalHRPool;
  const ok = pool([trial('s1', 'HR'), trial('s2', ' hr ')], [0, 6]);
  assert.equal(ok.intervals.length, 1, dir + ': declared HR input');
  assert.equal(ok.intervals[0].k, 2, dir + ': two independent studies');
  assert.ok(Math.abs(ok.intervals[0].HR - 0.8) < 1e-12, dir + ': point HR');
  cases++;
  const absent = trial('s1', 'HR');
  delete absent.estimandType;
  const legacy = pool([absent, trial('s2', 'HR')], [0, 6]);
  assert.equal(legacy.intervals.length, 1, dir + ': legacy absent type');
  assert.equal(legacy.intervals[0].k, 2, dir + ': legacy k');
  cases++;
  for (const value of ['RR', 'OR', null, false, [], 0, '']) {
    const x = trial('s1', value);
    const res = pool([x, trial('s2', 'HR')], [0, 6]);
    assert.deepEqual(res.intervals, [], dir + ': reject trial type ' + String(value));
    assert.match(res.error || '', /estimand|effect.type|non.hr/i, dir + ': explicit refusal');
    cases++;
  }
  for (const value of ['RR', 'OR', null, false, [], 0, '']) {
    const x = trial('s1', 'HR');
    x.intervals[0].estimandType = value;
    const res = pool([x, trial('s2', 'HR')], [0, 6]);
    assert.deepEqual(res.intervals, [], dir + ': reject interval type ' + String(value));
    assert.match(res.error || '', /estimand|effect.type|non.hr/i, dir + ': explicit refusal');
    cases++;
  }
  // A present but falsy interval-list field is malformed source evidence, not
  // an absent (legacy) field. It must never silently remove a declared study.
  for (const [label, badList] of [
    ['explicit null', null], ['explicit false', false],
    ['explicit zero', 0], ['explicit empty text', '']
  ]) {
    const declared = trial('bad', 'HR');
    declared.intervals = badList;
    const res = pool([trial('s1', 'HR'), trial('s2', 'HR'), declared], [0, 6]);
    assert.deepEqual(res.intervals, [], dir + ': refuse ' + label);
    assert.match(res.error || '', /malformed.*interval.*record/i,
                 dir + ': explanation of ' + label);
    cases++;
  }
  const unreported = trial('no-interval-record', 'HR');
  delete unreported.intervals;
  const skippedLegacy = pool([trial('s1', 'HR'), trial('s2', 'HR'), unreported], [0, 6]);
  assert.equal(skippedLegacy.intervals.length, 1, dir + ': genuinely absent legacy list');
  assert.equal(skippedLegacy.intervals[0].k, 2, dir + ': preserve legacy independent trials');
  cases++;
  const explicitHR = trial('s1', 'HR');
  explicitHR.intervals[0].estimandType = ' HR ';
  const typed = pool([explicitHR, trial('s2', 'HR')], [0, 6]);
  assert.equal(typed.intervals.length, 1, dir + ': valid nested type');
  cases++;
}
console.log('INTERVAL_HR_ESTIMAND_GUARD_PASS ' + cases + ' synthetic checks');
"""

def test_interval_hr_rejects_bad_types_and_explicit_malformed_lists_in_all_copies():
    result = subprocess.run(
        ["node", "-e", NODE], cwd=ROOT, text=True,
        capture_output=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "INTERVAL_HR_ESTIMAND_GUARD_PASS 66 synthetic checks" in result.stdout
