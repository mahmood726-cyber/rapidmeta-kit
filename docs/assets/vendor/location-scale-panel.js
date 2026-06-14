/* location-scale-panel.js — location-scale meta-regression (Viechtbauer &
 * López-López 2022): a meta-regression that ALSO models τ² as a function of a
 * moderator, via a log link  log τ²_i = α₀ + α₁·z_i.
 *
 * Engine: AlmLocationScale.fit (vendored verbatim from allmeta/shared/
 * location-scale.js, verified vs metafor::rma(yi, vi, mods=~x, scale=~z,
 * link="log", method="ML") on dat.bcg to 1e-3/1e-5). Standard meta-regression
 * assumes one residual τ²; here residual heterogeneity itself depends on a scale
 * moderator. Location β is GLS; scale α is ML (Nelder-Mead).
 *
 * The kit's primary data model is one effect per trial with no moderators, so
 * this is a PASTE-INPUT tool. It NEVER reads or fabricates data from the
 * dashboard — computes only on explicit user input.
 *
 * Input format (one study per line):  yi, sei, xMod, zMod
 *   e.g.  -0.94, 0.598, 44, 44
 * yi/sei are the effect and its standard error (vi = sei²); xMod enters the MEAN
 * model (location), zMod enters the SCALE model (heterogeneity). Both designs get
 * an intercept added automatically. Use the same column twice to model the mean
 * and the variance on the same moderator. Needs ≥4 studies.
 */
(function (global) {
  'use strict';
  const STORAGE_KEY = 'location-scale-panel-expanded';

  function parseRows(text) {
    const rows = [], errors = [];
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i].trim();
      if (!raw || raw.charAt(0) === '#') continue;
      const parts = raw.split(/[,\t]/).map(s => s.trim());
      if (parts.length < 4) { errors.push('Line ' + (i + 1) + ': need yi, sei, xMod, zMod'); continue; }
      const y = Number(parts[0]), se = Number(parts[1]), x = Number(parts[2]), z = Number(parts[3]);
      if (!isFinite(y)) { errors.push('Line ' + (i + 1) + ': yi "' + parts[0] + '" not numeric'); continue; }
      if (!isFinite(se) || se <= 0) { errors.push('Line ' + (i + 1) + ': sei "' + parts[1] + '" must be > 0'); continue; }
      if (!isFinite(x)) { errors.push('Line ' + (i + 1) + ': xMod "' + parts[2] + '" not numeric'); continue; }
      if (!isFinite(z)) { errors.push('Line ' + (i + 1) + ': zMod "' + parts[3] + '" not numeric'); continue; }
      rows.push({ y, se, x, z });
    }
    return { rows, errors };
  }

  function compute(P, resultEl, text) {
    const fmt = P.fmt;
    const parsed = parseRows(text);
    if (parsed.errors.length) {
      resultEl.innerHTML = '<div style="background:#3a0a0a;border:1px solid #7f1d1d;color:#fca5a5;padding:8px 10px;border-radius:6px;font-size:11px;">⚠ '
        + parsed.errors.length + ' problem(s):<br>' + parsed.errors.map(P.escapeHtml).join('<br>') + '</div>';
      return;
    }
    if (parsed.rows.length < 4) { resultEl.innerHTML = '<div style="color:#94a3b8;font-size:11px;">Enter at least 4 rows (location + scale slopes need residual df).</div>'; return; }
    const zVals = new Set(parsed.rows.map(r => r.z));
    if (zVals.size < 2) {
      resultEl.innerHTML = '<div style="background:#3a2a0a;border:1px solid #92400e;color:#fbbf24;padding:8px 10px;border-radius:6px;font-size:11px;">'
        + '⚠ The scale moderator zMod is constant — a location-scale model needs a VARYING zMod to identify α₁. With a constant zMod use ordinary meta-regression.</div>';
      return;
    }
    const yi = parsed.rows.map(r => r.y);
    const vi = parsed.rows.map(r => r.se * r.se);
    const X = parsed.rows.map(r => [1, r.x]);
    const Z = parsed.rows.map(r => [1, r.z]);
    let f;
    try { f = global.AlmLocationScale.fit(yi, vi, X, Z); }
    catch (e) { resultEl.innerHTML = '<div style="background:#3a0a0a;border:1px solid #7f1d1d;color:#fca5a5;padding:8px 10px;border-radius:6px;font-size:11px;">Computation failed: ' + P.escapeHtml(String(e.message || e)) + '</div>'; return; }
    if (!f || !isFinite(f.beta[0]) || !isFinite(f.alpha[0])) { resultEl.innerHTML = '<div style="color:#fca5a5;font-size:11px;">ML did not converge on this input.</div>'; return; }
    const zc = 1.959963984540054;
    function cell(label, value, sub) {
      return '<div style="background:#0b1220;border:1px solid #1e293b;border-radius:6px;padding:6px 8px;">'
        + '<div style="font-size:9.5px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">' + label + '</div>'
        + '<div style="font-size:13px;color:#f1f5f9;font-weight:700;font-family:JetBrains Mono,monospace;margin-top:2px;">' + value + '</div>'
        + (sub ? '<div style="font-size:10px;color:#94a3b8;margin-top:1px;">' + sub + '</div>' : '') + '</div>';
    }
    const t2 = f.tau2;
    const t2min = Math.min.apply(null, t2), t2max = Math.max.apply(null, t2);
    const scaleZ = isFinite(f.alphaSE[1]) && f.alphaSE[1] > 0 ? f.alpha[1] / f.alphaSE[1] : NaN;
    const scaleP = isFinite(scaleZ) ? 2 * (1 - _phi(Math.abs(scaleZ))) : NaN;
    resultEl.innerHTML = '<div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">'
      + f.k + ' studies · ML logLik = ' + fmt(f.logLik, 3) + ' · location β + scale α (log link)</div>'
      + '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;">'
      + cell('Location intercept β₀', fmt(f.beta[0], 3), '95% CI ' + fmt(f.beta[0] - zc * f.betaSE[0], 3) + ' – ' + fmt(f.beta[0] + zc * f.betaSE[0], 3))
      + cell('Location slope β₁ (xMod)', fmt(f.beta[1], 4), 'SE ' + fmt(f.betaSE[1], 4))
      + cell('Scale intercept α₀', fmt(f.alpha[0], 3), 'log τ² at zMod = 0')
      + cell('Scale slope α₁ (zMod)', fmt(f.alpha[1], 4), 'p = ' + (isFinite(scaleP) ? fmt(scaleP, 3) : 'n/a') + (isFinite(scaleP) && scaleP < 0.05 ? ' (τ² varies)' : ''))
      + cell('τ²_i range', fmt(t2min, 4) + ' – ' + fmt(t2max, 4), 'per-study residual heterogeneity')
      + '</div>';
  }

  function _phi(x) { // standard normal CDF (Abramowitz-Stegun)
    const t = 1 / (1 + 0.2316419 * Math.abs(x));
    const d = 0.3989422804014327 * Math.exp(-x * x / 2);
    let p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return x > 0 ? 1 - p : p;
  }

  function buildNode(P) {
    const wrap = document.createElement('div');
    wrap.innerHTML = '<div style="font-size:11px;color:#cbd5e1;margin-bottom:6px;">'
      + 'Location-scale meta-regression — model the <strong>mean effect AND τ²</strong> on moderators (Viechtbauer-López 2022). '
      + 'Paste rows: <code style="color:#7dd3fc;">yi, sei, xMod, zMod</code> (xMod = mean model, zMod = scale/heterogeneity model). Computes only on your input.</div>';
    const fmtHint = document.createElement('div');
    fmtHint.style.cssText = 'font-size:10px;color:#64748b;margin-bottom:6px;';
    fmtHint.innerHTML = 'format: <code style="color:#7dd3fc;">yi, sei, xMod, zMod</code> — one study per line. Intercepts added automatically; zMod must vary.';
    wrap.appendChild(fmtHint);
    const ta = document.createElement('textarea');
    ta.rows = 6;
    ta.placeholder = '-0.94, 0.598, 44, 44\n-1.67, 0.456, 55, 55\n-1.39, 0.658, 42, 42\n-0.22, 0.228, 13, 13';
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
    btn.textContent = 'Fit location-scale';
    btn.style.cssText = 'background:#1e3a5f;color:#7dd3fc;border:1px solid #334155;border-radius:6px;padding:6px 12px;font-size:11px;cursor:pointer;font-weight:600;';
    btnRow.appendChild(example); btnRow.appendChild(btn);
    wrap.appendChild(btnRow);
    const result = document.createElement('div');
    result.style.cssText = 'margin-top:6px;';
    wrap.appendChild(result);
    const note = document.createElement('div');
    note.style.cssText = 'font-size:10.5px;color:#64748b;line-height:1.5;border-top:1px solid #1e293b;padding-top:8px;margin-top:10px;';
    note.innerHTML = '<strong>Location-scale model (metafor::rma scale=~z, link=log):</strong> the residual heterogeneity τ²_i = exp(α₀ + α₁·zᵢ) '
      + 'is allowed to depend on a moderator, so studies with different zMod get different τ². Location β is GLS given the per-study τ²; α is ML '
      + '(Nelder-Mead on the profile log-likelihood). A significant α₁ means heterogeneity itself is moderated. Reduces to ordinary ML meta-regression '
      + 'when zMod is constant — which the panel rejects (α₁ unidentifiable). Needs ≥4 studies with a varying zMod.';
    wrap.appendChild(note);
    // dat.bcg worked example (the engine's own metafor oracle: ablat moderator in both models).
    const EXAMPLE = '-0.94, 0.598, 44, 44\n-1.67, 0.456, 55, 55\n-1.39, 0.658, 42, 42\n-1.46, 0.143, 52, 52\n-0.22, 0.228, 13, 13\n-0.96, 0.100, 44, 44\n-1.63, 0.476, 19, 19\n0.01, 0.063, 13, 13\n-0.47, 0.239, 27, 27\n-1.40, 0.275, 42, 42\n-0.34, 0.112, 18, 18\n0.45, 0.731, 33, 33\n-0.02, 0.268, 33, 33';
    example.addEventListener('click', () => { ta.value = EXAMPLE; });
    btn.addEventListener('click', () => compute(P, result, ta.value));
    return wrap;
  }

  function render() {
    const P = global.PanelHelper;
    if (!P || !global.AlmLocationScale) return false;
    if (document.getElementById('location-scale-panel')) return true;
    const panel = P.buildCollapsiblePanel({
      id: 'location-scale-panel', badge: 'Location-scale meta-regression',
      summary: 'Meta-regression that also models τ² on a moderator (Viechtbauer-López) — paste-input tool',
      bodyNode: buildNode(P), storageKey: STORAGE_KEY,
    });
    P.insertAfterRBadge(panel);
    return true;
  }

  function bootstrap() {
    if (typeof document === 'undefined') return;
    let tries = 0;
    const tick = () => { if (render()) return; if (++tries < 20) setTimeout(tick, 250); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(tick, 1350));
    else setTimeout(tick, 1350);
  }

  global.LocationScalePanel = { render, parseRows };
  bootstrap();
})(typeof window !== 'undefined' ? window : this);
