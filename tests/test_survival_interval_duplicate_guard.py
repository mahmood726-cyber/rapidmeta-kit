"""Duplicate-window study evidence must not be counted twice in interval-HR pooling.

These are synthetic structural/negative regressions against the *shipped* JS
engine and panel, not native R/metafor numerical parity or clinical validation.
See Cochrane Handbook Ch 6 §6.2 (unit-of-analysis/repeated observations).
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COPIES = ("assets", "template/assets", "docs/assets")
SCRIPT = r"""
const assert = require('node:assert/strict');
const copy = process.argv[1];
const S = require('./' + copy + '/vendor/rapidmeta-survival.js').RapidMetaSurvival;
function interval(t0, t1, HR, lo, hi) {
  return {t0, t1, HR, HR_ci_lo: lo, HR_ci_hi: hi};
}
const a = interval(0, 6, 0.75, 0.60, 0.92);
const b = interval(0, 6, 0.80, 0.65, 0.99);
const c = interval(0, 6, 0.72, 0.55, 0.95);
const baseline = [
  {name: 'A', intervals: [a]},
  {name: 'B', intervals: [b]},
  {name: 'C', intervals: [c]}
];
const result = S.intervalHRPool(baseline, [0, 6]);
assert.equal(result.error, undefined);
assert.equal(result.intervals.length, 1);
assert.equal(result.intervals[0].k, 3);
// Frozen shipped JS pre-fix output only; NOT an independent statistical oracle.
assert.ok(Math.abs(result.intervals[0].HR - 0.7619073821994747) < 1e-11);
assert.ok(Math.abs(result.intervals[0].HR_ci_hi - 1.0167591076481657) < 1e-11);

const duplicated = [{...baseline[0], intervals: [a, {...a}]}, ...baseline.slice(1)];
const duplicateResult = S.intervalHRPool(duplicated, [0, 6]);
assert.deepEqual(duplicateResult.intervals, []);
assert.match(duplicateResult.error, /Repeated interval-HR records for trial 1/);
assert.match(duplicateResult.error, /pooling refused/);

// Distinct reported HRs in the same trial/window are also dependent evidence.
const discordant = [{...baseline[0],
  intervals: [a, interval(0, 6, 1.10, 0.85, 1.42)]}, ...baseline.slice(1)];
assert.match(S.intervalHRPool(discordant, [0, 6]).error,
  /Repeated interval-HR records for trial 1/);

// Do not silently select one complete record when another record is malformed.
const malformed = [{...baseline[0],
  intervals: [a, interval(0, 6, -1, 0, 2)]}, ...baseline.slice(1)];
assert.match(S.intervalHRPool(malformed, [0, 6]).error,
  /Repeated interval-HR records for trial 1/);

// A study CAN contribute to separate, non-overlapping analysis windows.
const distinct = baseline.map(t => ({...t,
  intervals: [...t.intervals, interval(6, 12, 0.9, 0.68, 1.20)]}));
const eligible = S.intervalHRPool(distinct, [0, 6, 12]);
assert.equal(eligible.error, undefined);
assert.deepEqual(eligible.intervals.map(x => x.k), [3, 3]);

// A late duplicate must refuse the WHOLE request, not publish a partial pool.
const late = distinct.map((t, i) => ({...t,
  intervals: i === 1 ? [...t.intervals, interval(6, 12, 1.1, 0.8, 1.5)] : t.intervals}));
const lateResult = S.intervalHRPool(late, [0, 6, 12]);
assert.deepEqual(lateResult.intervals, []);
assert.match(lateResult.error, /Repeated interval-HR records for trial 2/);

// Exercise the actual shipped panel, not only the engine's return value.
// Require before constructing document so its auto-bootstrap remains inactive.
const panel = require('./' + copy + '/vendor/interval-hr-pool.js');
let captured;
panel.PanelHelper = {
  getRealData() { return {a: duplicated[0], b: duplicated[1], c: duplicated[2]}; },
  fmt(value, digits) { return Number(value).toFixed(digits); },
  buildCollapsiblePanel(config) { captured = config; return {}; },
  insertAfterRBadge() {}
};
panel.RapidMetaSurvival = S;
global.document = { getElementById() { return null; } };
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /role="alert"/);
assert.match(captured.bodyHtml, /Interval-HR pooling refused/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);
console.log('PASS interval-HR duplicate refusal and disjoint-window control');
"""


@pytest.mark.parametrize("copy", COPIES)
def test_shipped_interval_hr_avoids_duplicate_study_weights(copy):
    proc = subprocess.run(
        ["node", "-e", SCRIPT, copy],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
        check=False,
    )
    assert proc.returncode == 0, (
        f"{copy}: Node exit {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "PASS interval-HR duplicate refusal" in proc.stdout
