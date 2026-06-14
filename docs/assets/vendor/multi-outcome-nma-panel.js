/* multi-outcome-nma-panel.js — multivariate NMA over two correlated outcomes
 * (Achana et al. 2014), paste-input tool.
 *
 * Engine: AlmMultiOutcomeNMA.fit (vendored verbatim from allmeta/shared/
 * multi-outcome-nma.js). A standard NMA analyses one outcome at a time; when two
 * outcomes are correlated, jointly modelling them borrows strength across the
 * outcomes (and across the multi-arm structure). The combined random-effects
 * covariance is Σ_RE^outcomes ⊗ G_arm (G_arm = 1 on the diagonal, ½ off — the
 * multi-arm contrast structure); Σ_RE^outcomes is seeded by per-outcome DL + the
 * sample correlation of residuals, then β is solved by GLS.
 *
 * The kit carries no per-outcome network, so this is a PASTE-INPUT tool. It NEVER
 * reads or fabricates dashboard data — computes only on explicit user input.
 *
 * Input format (one contrast per line):  study, trtA, trtB, y1, se1, y2, se2
 *   e.g.  S1, A, B, -0.40, 0.12, -0.50, 0.15
 * Each row is a treatment contrast (trtB vs trtA) within a study, reporting two
 * correlated outcomes (y1/se1, y2/se2). Rows sharing a study id are treated as a
 * multi-arm study (shared-control ½ off-diagonal). First treatment seen is the
 * reference. Use NA for an unreported outcome on a row. Needs ≥2 treatments and
 * enough contrasts to connect the network.
 */
(function (global) {
  'use strict';
  const STORAGE_KEY = 'multi-outcome-nma-panel-expanded';

  function _num(s) {
    if (s == null) return NaN;
    const t = String(s).trim();
    if (t === '' || t.toLowerCase() === 'na' || t.toLowerCase() === 'nan') return NaN;
    return Number(t);
  }

  function parseRows(text) {
    const rows = [], errors = [];
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i].trim();
      if (!raw || raw.charAt(0) === '#') continue;
      const parts = raw.split(/[,\t]/).map(s => s.trim());
      if (parts.length < 7) { errors.push('Line ' + (i + 1) + ': need study, trtA, trtB, y1, se1, y2, se2'); continue; }
      const study = parts[0], a = parts[1], b = parts[2];
      const y1 = _num(parts[3]), s1 = _num(parts[4]), y2 = _num(parts[5]), s2 = _num(parts[6]);
      if (!study) { errors.push('Line ' + (i + 1) + ': empty study id'); continue; }
      if (!a || !b) { errors.push('Line ' + (i + 1) + ': empty treatment label'); continue; }
      if (a === b) { errors.push('Line ' + (i + 1) + ': trtA and trtB must differ'); continue; }
      const has1 = isFinite(y1) && isFinite(s1), has2 = isFinite(y2) && isFinite(s2);
      if (!has1 && !has2) { errors.push('Line ' + (i + 1) + ': no complete (y, se) pair for either outcome'); continue; }
      if (isFinite(s1) && s1 <= 0) { errors.push('Line ' + (i + 1) + ': se1 must be > 0'); continue; }
      if (isFinite(s2) && s2 <= 0) { errors.push('Line ' + (i + 1) + ': se2 must be > 0'); continue; }
      rows.push({ study, trtA: a, trtB: b, o1: has1 ? { yi: y1, sei: s1 } : null, o2: has2 ? { yi: y2, sei: s2 } : null });
    }
    return { rows, errors };
  }

  function _build(rows) {
    const treatments = [];
    rows.forEach(r => { [r.trtA, r.trtB].forEach(t => { if (treatments.indexOf(t) < 0) treatments.push(t); }); });
    const byStudy = Object.create(null), order = [];
    rows.forEach(r => { if (!byStudy[r.study]) { byStudy[r.study] = []; order.push(r.study); } byStudy[r.study].push(r); });
    const studies = order.map(id => ({
      id,
      contrasts: byStudy[id].map(r => ({
        trtA: r.trtA, trtB: r.trtB,
        outcomes: [r.o1 || { yi: NaN, sei: NaN }, r.o2 || { yi: NaN, sei: NaN }],
      })),
    }));
    return { treatments, studies };
  }

  function compute(P, resultEl, text) {
    const fmt = P.fmt;
    const parsed = parseRows(text);
    if (parsed.errors.length) {
      resultEl.innerHTML = '<div style="background:#3a0a0a;border:1px solid #7f1d1d;color:#fca5a5;padding:8px 10px;border-radius:6px;font-size:11px;">⚠ '
        + parsed.errors.length + ' problem(s):<br>' + parsed.errors.map(P.escapeHtml).join('<br>') + '</div>';
      return;
    }
    const built = _build(parsed.rows);
    if (built.treatments.length < 2) {
      resultEl.innerHTML = '<div style="background:#3a2a0a;border:1px solid #92400e;color:#fbbf24;padding:8px 10px;border-radius:6px;font-size:11px;">⚠ Need ≥2 treatments in the network.</div>';
      return;
    }
    let f;
    try { f = global.AlmMultiOutcomeNMA.fit(built.studies, built.treatments, { K: 2 }); }
    catch (e) { resultEl.innerHTML = '<div style="background:#3a2a0a;border:1px solid #92400e;color:#fbbf24;padding:8px 10px;border-radius:6px;font-size:11px;">⚠ ' + P.escapeHtml(String(e.message || e)) + '</div>'; return; }
    if (!f || !f.ok) {
      resultEl.innerHTML = '<div style="background:#3a2a0a;border:1px solid #92400e;color:#fbbf24;padding:8px 10px;border-radius:6px;font-size:11px;">⚠ '
        + P.escapeHtml(f && f.error ? f.error : 'multi-outcome NMA not identifiable on this input') + '</div>';
      return;
    }
    const ref = f.reference;
    function leagueTable(o) {
      let t = '<table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:4px;">'
        + '<tr style="color:#64748b;text-align:left;"><th style="padding:3px 6px;">vs ' + P.escapeHtml(ref) + '</th><th style="padding:3px 6px;">Effect</th><th style="padding:3px 6px;">SE</th><th style="padding:3px 6px;">95% CI</th></tr>';
      f.treatments.forEach(tr => {
        if (tr === ref) return;
        const e = f.effects[o][tr];
        t += '<tr style="border-top:1px solid #1e293b;color:#e2e8f0;font-family:JetBrains Mono,monospace;">'
          + '<td style="padding:3px 6px;color:#7dd3fc;">' + P.escapeHtml(tr) + '</td>'
          + '<td style="padding:3px 6px;">' + fmt(e.estimate, 3) + '</td>'
          + '<td style="padding:3px 6px;">' + fmt(e.se, 3) + '</td>'
          + '<td style="padding:3px 6px;color:#94a3b8;">' + fmt(e.ci_lo, 2) + ' – ' + fmt(e.ci_hi, 2) + '</td></tr>';
      });
      return t + '</table>';
    }
    const sig = f.Sigma_RE_outcomes;
    const tau1 = Math.sqrt(Math.max(0, sig[0][0])), tau2 = Math.sqrt(Math.max(0, sig[1][1]));
    const rho = (tau1 > 0 && tau2 > 0) ? sig[0][1] / (tau1 * tau2) : 0;
    resultEl.innerHTML = '<div style="font-size:11px;color:#94a3b8;margin-bottom:4px;">'
      + f.n_studies + ' studies · ' + f.n_contrasts + ' contrasts · ' + f.treatments.length + ' treatments · '
      + 'between-study τ = (' + fmt(tau1, 3) + ', ' + fmt(tau2, 3) + ') · outcome ρ = ' + fmt(rho, 3) + '</div>'
      + '<div style="font-size:10px;color:#64748b;margin:6px 0 2px;">Outcome 1 league</div>' + leagueTable(0)
      + '<div style="font-size:10px;color:#64748b;margin:8px 0 2px;">Outcome 2 league</div>' + leagueTable(1);
  }

  function buildNode(P) {
    const wrap = document.createElement('div');
    wrap.innerHTML = '<div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">'
      + 'Multivariate NMA over <strong>two correlated outcomes</strong> (Achana 2014) — joint modelling borrows strength across outcomes. '
      + 'Paste contrasts: <code style="color:#7dd3fc;">study, trtA, trtB, y1, se1, y2, se2</code>. Computes only on your input.</div>';
    const fmtHint = document.createElement('div');
    fmtHint.style.cssText = 'font-size:10px;color:#64748b;margin-bottom:6px;';
    fmtHint.innerHTML = 'format: <code style="color:#7dd3fc;">study, trtA, trtB, y1, se1, y2, se2</code> — one contrast per line; rows sharing a study id form a multi-arm study; NA for an unreported outcome.';
    wrap.appendChild(fmtHint);
    const ta = document.createElement('textarea');
    ta.rows = 6;
    ta.placeholder = 'S1, A, B, -0.40, 0.12, -0.50, 0.15\nS2, A, C, -0.55, 0.16, -0.62, 0.18\nS3, B, C, -0.20, 0.18, -0.25, 0.20\nS4, A, B, -0.30, 0.14, -0.38, 0.16';
    ta.style.cssText = 'width:100%;box-sizing:border-box;background:#0b1220;border:1px solid #1e293b;border-radius:6px;color:#e2e8f0;font-family:JetBrains Mono,monospace;font-size:11px;padding:8px;resize:vertical;';
    wrap.appendChild(ta);
    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'margin:8px 0;display:flex;gap:8px;';
    const example = document.createElement('button');
    example.type = 'button';
    example.textContent = 'Load example';
    example.style.cssText = 'background:#0b1220;color:#94a3b8;border:1px solid #334155;border-radius:6px;padding:6px 12px;font-size:11px;cursor:pointer;';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = 'Fit multi-outcome NMA';
    btn.style.cssText = 'background:#1e3a5f;color:#7dd3fc;border:1px solid #334155;border-radius:6px;padding:6px 12px;font-size:11px;cursor:pointer;font-weight:600;';
    btnRow.appendChild(example); btnRow.appendChild(btn);
    wrap.appendChild(btnRow);
    const result = document.createElement('div');
    result.style.cssText = 'margin-top:6px;';
    wrap.appendChild(result);
    const note = document.createElement('div');
    note.style.cssText = 'font-size:10.5px;color:#64748b;line-height:1.5;border-top:1px solid #1e293b;padding-top:8px;margin-top:10px;';
    note.innerHTML = '<strong>Multi-outcome NMA (Achana 2014 §3.2):</strong> the combined random-effects covariance is Σ_RE^outcomes ⊗ G_arm, where '
      + 'G_arm carries the multi-arm shared-control ½ off-diagonal and Σ_RE^outcomes the between-study correlation across the two outcomes; β is solved '
      + 'by GLS. Σ_RE^outcomes is seeded by per-outcome DL + the sample correlation of residuals (a non-iterative analytic approximation; for complex '
      + 'multi-arm × multi-outcome networks use a full Bayesian WinBUGS fit). When the outcome correlation vanishes (τ → 0) each outcome’s league '
      + 'reduces to the single-outcome NMA. Needs a connected network of ≥2 treatments.';
    wrap.appendChild(note);
    const EXAMPLE = 'S1, A, B, -0.40, 0.12, -0.50, 0.15\nS2, A, C, -0.55, 0.16, -0.62, 0.18\nS3, B, C, -0.20, 0.18, -0.25, 0.20\nS4, A, B, -0.30, 0.14, -0.38, 0.16';
    example.addEventListener('click', () => { ta.value = EXAMPLE; });
    btn.addEventListener('click', () => compute(P, result, ta.value));
    return wrap;
  }

  function render() {
    const P = global.PanelHelper;
    if (!P || !global.AlmMultiOutcomeNMA) return false;
    if (document.getElementById('multi-outcome-nma-panel')) return true;
    const panel = P.buildCollapsiblePanel({
      id: 'multi-outcome-nma-panel', badge: 'Multi-outcome NMA (Achana)',
      summary: 'Multivariate NMA over two correlated outcomes (Achana 2014) — paste-input tool',
      bodyNode: buildNode(P), storageKey: STORAGE_KEY,
    });
    P.insertAfterRBadge(panel);
    return true;
  }

  function bootstrap() {
    if (typeof document === 'undefined') return;
    let tries = 0;
    const tick = () => { if (render()) return; if (++tries < 20) setTimeout(tick, 250); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(tick, 1550));
    else setTimeout(tick, 1550);
  }

  global.MultiOutcomeNMAPanel = { render, parseRows };
  bootstrap();
})(typeof window !== 'undefined' ? window : this);
