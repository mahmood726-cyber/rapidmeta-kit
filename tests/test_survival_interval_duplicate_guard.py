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

// A malformed record from a fourth independent study must not silently
// vanish while three valid studies are pooled as if all data were usable.
const invalidRows = [
  {label: 'negative HR', iv: interval(0, 6, -1, 0.5, 1.2)},
  {label: 'missing upper CI', iv: {t0: 0, t1: 6, HR: 0.8, HR_ci_lo: 0.6}},
  {label: 'reversed CI bounds', iv: interval(0, 6, 0.8, 1.2, 0.6)},
  // A reported HR outside its own 95% CI is an internally inconsistent input.
  {label: 'point HR above CI', iv: interval(0, 6, 2.0, 0.7, 1.2)},
  {label: 'point HR below CI', iv: interval(0, 6, 0.4, 0.6, 1.2)},
  {label: 'nonfinite limit', iv: interval(0, 6, 0.8, 0.6, Infinity)}
];
for (const {label, iv} of invalidRows) {
  const bad = S.intervalHRPool([...baseline, {name: 'D', intervals: [iv]}], [0, 6]);
  assert.deepEqual(bad.intervals, [], label);
  assert.match(bad.error, /Invalid interval-HR effect/, label);
}

// Multiple objects with the same canonical NCT are still ONE study; the
// pre-fix engine falsely reported k=4 with a 95% CI excluding the null.
const labelled = baseline.map((t, i) => ({...t,
  nct: ['NCT00000001', 'NCT00000002', 'NCT00000003'][i]}));
assert.equal(S.intervalHRPool(labelled, [0, 6]).intervals[0].k, 3);
const separated = [...labelled, {
  name: 'Different display name / same trial', nct: '  nct00000001 ',
  intervals: [a]
}];
const repeatedIdentity = S.intervalHRPool(separated, [0, 6]);
assert.deepEqual(repeatedIdentity.intervals, []);
assert.match(repeatedIdentity.error, /Repeated interval-HR records for trial 4/);
// A first, unrelated alias must not hide a shared canonical NCT.
const maskedAlias = [...labelled, {
  name: 'Repeat via another alias', studyId: 'distinct-local-code',
  nct_id: ' nct00000002 ', intervals: [b]
}];
assert.match(S.intervalHRPool(maskedAlias, [0, 6]).error,
  /Repeated interval-HR records for trial 4/);
// All recognized study-id aliases, not only NCT, must be considered.
const studyAlias = [...baseline.map((t, i) => ({...t,
  studyId: 'site-study-' + i})), {
    name: 'B duplicate', study_id: 'SITE-STUDY-1', intervals: [b]
  }];
assert.match(S.intervalHRPool(studyAlias, [0, 6]).error,
  /Repeated interval-HR records for trial 4/);
// Separate, disjoint follow-up analyses may contain the same NCT as long as
// no study contributes twice to any individual pooled window.
const separatedWindows = [
  ...labelled,
  ...labelled.map(t => ({...t, intervals: [interval(6, 12, 0.90, 0.68, 1.20)]}))
];
const acceptedWindows = S.intervalHRPool(separatedWindows, [0, 6, 12]);
assert.equal(acceptedWindows.error, undefined);
assert.deepEqual(acceptedWindows.intervals.map(w => w.k), [3, 3]);
// A duplicate ID that appears only in the second window must invalidate the
// WHOLE requested synthesis; never publish the first-window analysis alone.
const laterRepeatedIdentity = [...separatedWindows, {
  nct: 'nct00000001', name: 'Duplicated later study report',
  intervals: [interval(6, 12, 1.10, 0.85, 1.42)]
}];
const refusedLate = S.intervalHRPool(laterRepeatedIdentity, [0, 6, 12]);
assert.deepEqual(refusedLate.intervals, []);
assert.match(refusedLate.error, /Repeated interval-HR records for trial 7/);

// Extremely separated but finite source HRs can produce an overflowed upper
// and an underflowed zero lower CI. Previously the engine returned a
// superficially valid k=2 pool; JSON turned its Infinity into null.
const unrepresentable = [
  {name: 'Extreme', intervals: [interval(0, 6, 1e308, 1e307, 1.79e308)]},
  {name: 'Reference', intervals: [interval(0, 6, 0.8, 0.6, 1.0)]}
];
const refusedRange = S.intervalHRPool(unrepresentable, [0, 6]);
assert.deepEqual(refusedRange.intervals, []);
assert.match(refusedRange.error, /Unrepresentable interval-HR pooled estimate or confidence limits/);

// A study CAN contribute to separate, non-overlapping analysis windows.
const distinct = baseline.map(t => ({...t,
  intervals: [...t.intervals, interval(6, 12, 0.9, 0.68, 1.20)]}));
const eligible = S.intervalHRPool(distinct, [0, 6, 12]);
assert.equal(eligible.error, undefined);
assert.deepEqual(eligible.intervals.map(x => x.k), [3, 3]);

// Invalid evidence in a later window must also suppress earlier pooled windows.
const laterInvalid = [...distinct, {name: 'D',
  intervals: [interval(6, 12, -1, 0.5, 1.2)]}];
const laterInvalidResult = S.intervalHRPool(laterInvalid, [0, 6, 12]);
assert.deepEqual(laterInvalidResult.intervals, []);
assert.match(laterInvalidResult.error, /Invalid interval-HR effect/);

// A late duplicate must refuse the WHOLE request, not publish a partial pool.
const late = distinct.map((t, i) => ({...t,
  intervals: i === 1 ? [...t.intervals, interval(6, 12, 1.1, 0.8, 1.5)] : t.intervals}));
const lateResult = S.intervalHRPool(late, [0, 6, 12]);
assert.deepEqual(lateResult.intervals, []);
assert.match(lateResult.error, /Repeated interval-HR records for trial 2/);

// Union-of-breakpoints regression: [0,6] is NOT interchangeable with
// shorter [0,3] and [3,6] study estimates. The previous engine silently
// discarded the spanning study and showed k=2 pools for the other studies.
const mixedWindows = [
  {name: 'Long study', nct: 'NCTA',
    intervals: [interval(0, 6, 1.90, 1.50, 2.50)]},
  {name: 'Short study B', nct: 'NCTB',
    intervals: [interval(0, 3, 0.80, 0.60, 1.05),
                interval(3, 6, 0.90, 0.68, 1.20)]},
  {name: 'Short study C', nct: 'NCTC',
    intervals: [interval(0, 3, 0.78, 0.59, 1.04),
                interval(3, 6, 0.88, 0.66, 1.17)]}
];
const nonAligned = S.intervalHRPool(mixedWindows, [0, 3, 6]);
assert.deepEqual(nonAligned.intervals, []);
assert.match(nonAligned.error, /Non-aligned interval-HR time window for trial 1/);
// Positive control: studies with exactly corresponding intervals still pool.
const alignedOnly = S.intervalHRPool(mixedWindows.slice(1), [0, 3, 6]);
assert.equal(alignedOnly.error, undefined);
assert.deepEqual(alignedOnly.intervals.map(w => w.k), [2, 2]);
// Explicitly requested follow-up range can exclude unrelated later records.
const outOfScope = S.intervalHRPool([
  mixedWindows[0], {name: 'Later follow-up',
    intervals: [interval(6, 12, 0.82, 0.65, 1.03)]}
], [0, 6]);
assert.equal(outOfScope.error, undefined);
assert.deepEqual(outOfScope.intervals.map(w => w.k), [1]);
// A source time of null/blank must NOT be fabricated as month zero by
// JavaScript Number(null)/Number('') coercion. No clinical data are involved.
for (const [label, start] of [
  ['blank', ''], ['whitespace', '   '], ['null', null],
  ['boolean', false], ['negative', -1]
]) {
  const malformedTime = S.intervalHRPool([
    {name:'A', intervals:[interval(start, 6, 0.75, 0.60, 0.92)]},
    baseline[1], baseline[2]
  ], [0, 6]);
  assert.deepEqual(malformedTime.intervals, [], label);
  assert.match(malformedTime.error, /Invalid interval-HR time boundaries/, label);
}
// Nonblank, nonnegative numeric source boundaries retain existing behaviour.
const numericTextTime = S.intervalHRPool([
  {name:'A', intervals:[interval('0', '6', 0.75, 0.60, 0.92)]},
  baseline[1], baseline[2]
], [0, 6]);
assert.equal(numericTextTime.error, undefined);
assert.equal(numericTextTime.intervals[0].k, 3);

// Invalid source time bounds are not silently discarded either.
const invalidWindow = S.intervalHRPool([
  mixedWindows[1], {name: 'Malformed', intervals: [
    interval('unknown', 3, 0.82, 0.65, 1.03)]}
], [0, 3, 6]);
assert.deepEqual(invalidWindow.intervals, []);
assert.match(invalidWindow.error, /Invalid interval-HR time boundaries/);

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
// Actual panel must also reject separately materialized duplicate study IDs.
panel.PanelHelper.getRealData = () => ({
  a: labelled[0], b: labelled[1], c: labelled[2], d: separated[3]
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Repeated interval-HR records/);
assert.match(captured.bodyHtml, /role="alert"/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);
// The actual panel must expose invalid-input refusal, not a partial result.
panel.PanelHelper.getRealData = () => ({
  a: baseline[0], b: baseline[1], c: baseline[2],
  d: {name: 'D', intervals: [interval(0, 6, -1, 0.5, 1.2)]}
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Invalid interval-HR effect/);
assert.match(captured.bodyHtml, /role="alert"/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);
// The panel must also fail closed on an inconsistent HR/CI, not show a pool.
panel.PanelHelper.getRealData = () => ({
  a: baseline[0], b: baseline[1], c: baseline[2],
  d: {name: 'D', intervals: [interval(0, 6, 2.0, 0.7, 1.2)]}
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Invalid interval-HR effect/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);
// Exercise defaultBreakpoints -> engine -> visible refusal for non-aligned
// original source windows; the panel must not show a partial subset as pooled.
panel.PanelHelper.getRealData = () => ({
  a: mixedWindows[0], b: mixedWindows[1], c: mixedWindows[2]
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Non-aligned interval-HR time window/);
assert.match(captured.bodyHtml, /role="alert"/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);

// Real panel must visibly refuse an empty follow-up start rather than
// presenting it as a valid observed month-zero record.
panel.PanelHelper.getRealData = () => ({
  a: {name:'A', intervals:[interval('', 6, 0.75, 0.60, 0.92)]},
  b: baseline[1], c: baseline[2]
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Invalid interval-HR time boundaries/);
assert.match(captured.bodyHtml, /role="alert"/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);

// The panel must expose an explicit refusal instead of a zero/Infinity CI.
panel.PanelHelper.getRealData = () => ({
  a: unrepresentable[0], b: unrepresentable[1]
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.summary, /^Refused:/);
assert.match(captured.bodyHtml, /Unrepresentable interval-HR pooled estimate/);
assert.doesNotMatch(captured.bodyHtml, /<th[^>]*>Pooled HR<\/th>/);

// Method/interpretation correctness: the engine actually uses REML+HKSJ
// for k=2, rather than the panel's former false "fixed-effect if k<5" claim.
const single = S.fit([{HR: a.HR, HR_ci_lo: a.HR_ci_lo, HR_ci_hi: a.HR_ci_hi}]);
assert.equal(single.method, 'FE');
const two = S.fit([
  {HR: a.HR, HR_ci_lo: a.HR_ci_lo, HR_ci_hi: a.HR_ci_hi},
  {HR: b.HR, HR_ci_lo: b.HR_ci_lo, HR_ci_hi: b.HR_ci_hi}
]);
assert.equal(two.k, 2);
assert.equal(two.method, 'REML+HKSJ');
// Force visibly different early/late point estimates. The panel may describe
// the spread but cannot infer non-PH or claim that an overall HR was pooled.
const contrasting = baseline.map((t, i) => ({...t,
  intervals: [t.intervals[0], interval(6, 12, 1.40 - i * 0.05,
    1.02 - i * 0.05, 1.78 - i * 0.05)]}));
panel.PanelHelper.getRealData = () => ({
  a: contrasting[0], b: contrasting[1], c: contrasting[2]
});
assert.equal(panel.IntervalHRPoolPanel.render(), true);
assert.match(captured.bodyHtml, /Descriptive interval-HR spread/);
assert.match(captured.bodyHtml, /not a proportional-hazards test/);
assert.match(captured.bodyHtml, /REML random-effects/);
assert.match(captured.bodyHtml, /floored HKSJ/);
assert.match(captured.bodyHtml, /k≥2/);
assert.match(captured.bodyHtml, /k=1/);
assert.match(captured.bodyHtml, /descriptive only/);
assert.doesNotMatch(captured.bodyHtml, /fixed-effect if k&lt;5/);
assert.doesNotMatch(captured.bodyHtml, /direct evidence of non-PH/);
assert.doesNotMatch(captured.bodyHtml, /favours treatment/);
assert.doesNotMatch(captured.bodyHtml, /overall HR averages/);
console.log('PASS interval-HR method-label accuracy and non-PH claim negatives');

console.log('PASS interval-HR duplicate refusal, invalid-input refusal and disjoint-window control');
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
