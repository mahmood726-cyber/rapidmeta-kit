/* NNT-from-HR panel (survival topic packs).
 *
 * Reads window.RapidMeta.realData; pools log-HR via window.RapidMetaSurvival.fit;
 * converts pooled HR to NNT via Altman 2002 at a baseline-risk slider.
 *
 * Distinct from vendor/nnt-panel.js (which pools risk-difference from binary 2x2).
 * This panel is the right NNT lens for time-to-event meta-analyses.
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'hr-nnt-panel-expanded';

  function hasOwn(row, key) {
    return Object.prototype.hasOwnProperty.call(row, key);
  }

  function finiteDecimal(value) {
    if (typeof value === 'number') return isFinite(value) ? value : null;
    if (typeof value !== 'string') return null;
    var raw = value.trim();
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw)) return null;
    var numeric = Number(raw);
    return isFinite(numeric) ? numeric : null;
  }

  function sourceValue(row, primary, alias) {
    // Explicitly invalid/missing primary data must not silently fall back.
    return hasOwn(row, primary) ? row[primary] : row[alias];
  }

  function extractSurvivalTrials(rd) {
    if (!rd || typeof rd !== 'object') return { trials: [] };
    var out = [], error = null;
    Object.values(rd).forEach(function (t, i) {
      if (!t || typeof t !== 'object' || Array.isArray(t)) return;
      // RR, OR and other estimands are not HR and must never enter HR/NNT.
      if (t.estimandType != null &&
          String(t.estimandType).trim().toUpperCase() !== 'HR') return;
      var hasEffect = ['HR', 'HR_ci_lo', 'HR_ci_hi',
                       'publishedHR', 'hrLCI', 'hrUCI'].some(function (key) {
        return hasOwn(t, key);
      });
      if (!hasEffect && String(t.estimandType || '').trim().toUpperCase() !== 'HR') return;
      var HR = finiteDecimal(sourceValue(t, 'HR', 'publishedHR'));
      var lo = finiteDecimal(sourceValue(t, 'HR_ci_lo', 'hrLCI'));
      var hi = finiteDecimal(sourceValue(t, 'HR_ci_hi', 'hrUCI'));
      if (HR === null || lo === null || hi === null ||
          !(0 < lo && lo <= HR && HR <= hi && lo < hi)) {
        if (error === null) error = 'Invalid summary-HR effect or 95% CI in source row ' + (i + 1);
        return;
      }
      out.push({
        studlab: String(t.name || t.studlab || '?'),
        HR: HR, HR_ci_lo: lo, HR_ci_hi: hi,
        events_ctl: finiteDecimal(sourceValue(t, 'events_ctl', 'cE')),
        n_ctl: finiteDecimal(sourceValue(t, 'n_ctl', 'cN'))
      });
    });
    return { trials: out, error: error };
  }

  function inferBaselineRisk(trials) {
    // This is only a crude-risk, exploratory proxy, NOT fixed-time survival.
    // Missing/malformed comparator arms cannot justify an invented 10% risk.
    var rates = [];
    for (var i = 0; i < trials.length; i++) {
      var e = trials[i].events_ctl, n = trials[i].n_ctl;
      if (!Number.isSafeInteger(e) || !Number.isSafeInteger(n) ||
          n <= 0 || e < 0 || e > n) return null;
      rates.push(e / n);
    }
    if (!rates.length) return null;
    rates.sort(function (a, b) { return a - b; });
    var mid = Math.floor(rates.length / 2);
    var median = rates.length % 2 ? rates[mid] : 0.5 * (rates[mid - 1] + rates[mid]);
    // A zero/one baseline makes an HR-based finite NNT non-identifiable.
    return isFinite(median) && median > 0 && median < 1 ? median : null;
  }

  function buildBody(P, trials, fit, baselineRisk, nnt, nntCiLo, nntCiHi) {
    var fmt = P.fmt;
    var html = '<div role="note">Exploratory HR-to-NNT conversion only: crude control-arm event rates ' +
               'do not establish a common fixed follow-up time or Kaplan–Meier baseline survival. ' +
               'No clinically validated time-specific NNT is claimed.</div>';

    if (nnt.nnt == null) {
      html += '<div style="background:#3a2a0a;border:1px solid #92400e;color:#fbbf24;padding:8px 10px;border-radius:6px;margin-bottom:10px;font-size:11.5px;">'
            + '⚠ <strong>NNT undefined</strong> — pooled HR is at or near 1.0, or baseline-risk × HR conversion is degenerate.'
            + '</div>';
    } else {
      var verb = nnt.direction === 'NNTB' ? 'benefit' : 'harm';
      html += '<div style="background:#0b1220;border:1px solid #1e293b;border-radius:6px;padding:9px 10px;margin-bottom:10px;font-size:12px;">'
            + '<strong style="color:#34d399;">' + nnt.direction + ' = ' + Math.ceil(nnt.nnt) + '</strong> '
            + (nntCiLo != null && nntCiHi != null ?
                '<span style="color:#cbd5e1;">(95% CI ' + Math.ceil(nntCiLo) + '–' + Math.ceil(nntCiHi) + ')</span> ' : '')
            + '<span style="color:#94a3b8;">at baseline risk ' + fmt(baselineRisk * 100, 1) + '% — treat ' + Math.ceil(nnt.nnt) + ' to ' + verb + ' 1.</span>'
            + '</div>';
    }

    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:10px;">';
    function cell(label, value, sub) {
      return '<div style="background:#0b1220;border:1px solid #1e293b;border-radius:6px;padding:6px 8px;">'
           + '<div style="font-size:9.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">' + label + '</div>'
           + '<div style="font-size:13px;color:#f1f5f9;font-weight:700;font-family:JetBrains Mono,monospace;margin-top:2px;">' + value + '</div>'
           + (sub ? '<div style="font-size:10px;color:#94a3b8;margin-top:1px;">' + sub + '</div>' : '')
           + '</div>';
    }
    html += cell('Pooled HR', fmt(fit.pooled_HR, 2),
                'CI ' + fmt(fit.pooled_HR_ci_lo, 2) + '–' + fmt(fit.pooled_HR_ci_hi, 2));
    html += cell('Baseline risk', fmt(baselineRisk * 100, 1) + '%', trials.length + ' trials');
    html += cell('Tx risk', nnt.tx_risk != null ? fmt(nnt.tx_risk * 100, 1) + '%' : '—');
    html += cell('ARR', nnt.arr != null ? fmt(Math.abs(nnt.arr) * 100, 2) + 'pp' : '—');
    html += '</div>';

    html += '<div style="font-size:10.5px;color:#94a3b8;margin-top:8px;line-height:1.5;">'
          + 'Method: NNT for time-to-event meta-analyses (Altman & Andersen 1999). '
          + 'ARR = R_ctl − (1 − (1 − R_ctl)^HR); NNT = 1/|ARR|. '
          + 'Baseline risk inferred as the median crude control-arm event rate across trials. '
          + 'Confidence bounds derived by applying the formula to the pooled HR CI limits. '
          + 'NNTB = number to benefit, NNTH = number to harm.'
          + '</div>';

    return html;
  }

  function showRefusal(P, reason) {
    var panel = P.buildCollapsiblePanel({
      id: 'hr-nnt-panel',
      badge: 'NNT (HR)',
      summary: 'Refused: summary-HR/NNT evidence invalid',
      bodyHtml: '<div role="alert">Summary-HR/NNT pooling refused: ' +
                reason + '. No pooled HR or NNT has been calculated.</div>',
      storageKey: STORAGE_KEY
    });
    var existing = document.getElementById('hr-nnt-panel');
    if (existing) existing.replaceWith(panel);
    else P.insertAfterRBadge(panel);
    return true;
  }

  function render() {
    var P = global.PanelHelper;
    var SURV = global.RapidMetaSurvival;
    if (!P || !SURV) return false;
    var rd = P.getRealData();
    if (!rd) return false;
    var extracted = extractSurvivalTrials(rd);
    if (extracted.error) return showRefusal(P, extracted.error);
    var trials = extracted.trials;
    if (trials.length < 2) return false;

    var fit;
    try { fit = SURV.fit(trials); }
    catch (e) {
      return showRefusal(P, 'The summary-HR estimator rejected these records');
    }
    if (!fit || fit.error) {
      return showRefusal(P, 'Invalid or numerically unrepresentable summary-HR evidence');
    }

    var baseline = inferBaselineRisk(trials);
    if (baseline === null) {
      return showRefusal(P, 'Missing or invalid comparator-arm event counts; no source-based baseline risk');
    }
    var nnt = SURV.nntForHR(fit.pooled_HR, baseline);
    var nntCiLo = null, nntCiHi = null;
    if (fit.pooled_HR_ci_lo > 0 && fit.pooled_HR_ci_hi > 0) {
      var a = SURV.nntForHR(fit.pooled_HR_ci_lo, baseline);
      var b = SURV.nntForHR(fit.pooled_HR_ci_hi, baseline);
      if (a.nnt != null && b.nnt != null && a.direction === b.direction) {
        nntCiLo = Math.min(a.nnt, b.nnt);
        nntCiHi = Math.max(a.nnt, b.nnt);
      }
    }

    var fmt = P.fmt;
    var summary;
    if (nnt.nnt == null) {
      summary = 'NNT undefined · pooled HR ' + fmt(fit.pooled_HR, 2);
    } else {
      summary = 'Exploratory ' + nnt.direction + ' ' + Math.ceil(nnt.nnt) +
                (nntCiLo != null ? ' [' + Math.ceil(nntCiLo) + '–' + Math.ceil(nntCiHi) + ']' : '') +
                ' · baseline ' + fmt(baseline * 100, 1) + '% · k=' + trials.length;
    }

    var panel = P.buildCollapsiblePanel({
      id: 'hr-nnt-panel',
      badge: 'NNT (HR)',
      summary: summary,
      bodyHtml: buildBody(P, trials, fit, baseline, nnt, nntCiLo, nntCiHi),
      storageKey: STORAGE_KEY
    });

    var existing = document.getElementById('hr-nnt-panel');
    if (existing) existing.replaceWith(panel);
    else P.insertAfterRBadge(panel);
    return true;
  }

  function bootstrap() {
    if (typeof document === 'undefined') return;
    var tries = 0;
    var tick = function () {
      if (render()) return;
      if (++tries < 20) setTimeout(tick, 250);
    };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { setTimeout(tick, 300); });
    } else {
      setTimeout(tick, 300);
    }
  }

  global.HRNNTPanel = { render: render };
  bootstrap();
})(typeof window !== 'undefined' ? window : this);
