/* Deeks' funnel asymmetry test for DTA — publication-bias diagnostic.
 *
 * Deeks JJ, Macaskill P, Irwig L. The performance of tests of publication
 * bias and other sample size effects in systematic reviews of diagnostic
 * test accuracy was assessed. J Clin Epidemiol 2005;58:882–93.
 *
 * Test: regress ln(DOR) on 1/√EffectiveSampleSize, where ESS is
 *   ESS_i = (4 × n1_i × n2_i) / (n1_i + n2_i)
 * with n1 = TP+FN (diseased), n2 = TN+FP (healthy).
 *
 * The intercept is approximately zero under no asymmetry; significant
 * intercept → small-study effect / publication bias.
 *
 * Auto-bootstrap; collapsed by default.
 */
(function (global) {
  'use strict';
  // t_{df} two-sided tail via regularized incomplete beta (audit bugs 5): the WLS
  // intercept uses an ESTIMATED dispersion so alpha/se is t_{k-2}, not z.
  function _lg(x){var c=[76.18009172947146,-86.50532032941677,24.01409824083091,-1.231739572450155,0.1208650973866179e-2,-0.5395239384953e-5];var y=x,t=x+5.5;t-=(x+0.5)*Math.log(t);var s=1.000000000190015;for(var j=0;j<6;j++){y++;s+=c[j]/y;}return -t+Math.log(2.5066282746310005*s/x);}
  function _bcf(a,b,x){var FPMIN=1e-300,qab=a+b,qap=a+1,qam=a-1,c=1,d=1-qab*x/qap;if(Math.abs(d)<FPMIN)d=FPMIN;d=1/d;var h=d;for(var m=1;m<=200;m++){var m2=2*m,aa=m*(b-m)*x/((qam+m2)*(a+m2));d=1+aa*d;if(Math.abs(d)<FPMIN)d=FPMIN;c=1+aa/c;if(Math.abs(c)<FPMIN)c=FPMIN;d=1/d;h*=d*c;aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2));d=1+aa*d;if(Math.abs(d)<FPMIN)d=FPMIN;c=1+aa/c;if(Math.abs(c)<FPMIN)c=FPMIN;d=1/d;var del=d*c;h*=del;if(Math.abs(del-1)<3e-12)break;}return h;}
  function _betai(a,b,x){if(x<=0)return 0;if(x>=1)return 1;var bt=Math.exp(_lg(a+b)-_lg(a)-_lg(b)+a*Math.log(x)+b*Math.log(1-x));return x<(a+1)/(a+b+2)?bt*_bcf(a,b,x)/a:1-bt*_bcf(b,a,1-x)/b;}
  function _tTail2(t,df){if(!(df>0))return NaN;return _betai(df/2,0.5,df/(df+t*t));}
  const STORAGE_KEY = 'dta-funnel-expanded';

  function parseCellsFromText(text) {
    if (!text) return null;
    const stripCommas = s => +String(s).replace(/,/g, '');
    const re = (label) => new RegExp('\\b' + label + '\\s*=\\s*(\\d{1,3}(?:,\\d{3})*|\\d+)', 'i');
    const grab = (label) => { const m = text.match(re(label)); return m ? stripCommas(m[1]) : null; };
    const TP = grab('TP'), FP = grab('FP'), FN = grab('FN'), TN = grab('TN');
    if (TP !== null && FP !== null && FN !== null && TN !== null) return { TP, FP, FN, TN };
    return null;
  }

  function pickDTATrials(rd) {
    const out = [];
    const ss = global._screeningStudies;
    if (Array.isArray(ss)) {
      ss.forEach(s => {
        if (!s || s.decision !== 'included') return;
        const cells = parseCellsFromText(s.rationale || '');
        if (cells && (cells.TP + cells.FN) > 0 && (cells.TN + cells.FP) > 0) {
          out.push({ name: s.studlab || '?', ...cells });
        }
      });
    }
    if (rd && out.length === 0) {
      Object.values(rd).forEach(t => {
        if (!t) return;
        const TP = +t.TP, FP = +t.FP, FN = +t.FN, TN = +t.TN;
        if ([TP,FP,FN,TN].every(v => Number.isFinite(v) && v >= 0) && (TP+FN) > 0 && (TN+FP) > 0) {
          out.push({ name: t.name || '?', TP, FP, FN, TN });
        }
      });
    }
    return out;
  }

  function deeksTest(trials) {
    if (trials.length < 4) return null;  // Power inadequate below k=4
    // Continuity correction for zero cells
    const points = trials.map(t => {
      let TP = t.TP, FP = t.FP, FN = t.FN, TN = t.TN;
      if (TP === 0 || FP === 0 || FN === 0 || TN === 0) {
        TP += 0.5; FP += 0.5; FN += 0.5; TN += 0.5;
      }
      const n1 = TP + FN, n2 = TN + FP;
      const lnDOR = Math.log((TP * TN) / (FP * FN));
      const varLnDOR = 1/TP + 1/FP + 1/FN + 1/TN;
      const ess = (4 * n1 * n2) / (n1 + n2);
      return { lnDOR, varLnDOR, ess, x: 1 / Math.sqrt(ess), name: t.name };
    });
    // Weighted regression: lnDOR = α + β × (1/√ESS)
    // Weights = ESS (Deeks 2005): 1/Var(lnDOR) would re-introduce the effect-
    // precision correlation the test is built to avoid (audit bug 3).
    const w = points.map(p => p.ess);
    let Sw = 0, Swx = 0, Swy = 0, Swxx = 0, Swxy = 0;
    for (let i = 0; i < points.length; i++) {
      Sw += w[i];
      Swx += w[i] * points[i].x;
      Swy += w[i] * points[i].lnDOR;
      Swxx += w[i] * points[i].x * points[i].x;
      Swxy += w[i] * points[i].x * points[i].lnDOR;
    }
    const xbar = Swx / Sw, ybar = Swy / Sw;
    const Sxx = Swxx - Sw * xbar * xbar;
    const Sxy = Swxy - Sw * xbar * ybar;
    if (Sxx === 0) return null;
    const beta = Sxy / Sxx;
    const alpha = ybar - beta * xbar;
    // Residual variance
    let rss = 0;
    for (let i = 0; i < points.length; i++) {
      const fitted = alpha + beta * points[i].x;
      rss += w[i] * Math.pow(points[i].lnDOR - fitted, 2);
    }
    const sigma2 = rss / Math.max(1, points.length - 2);
    const se_alpha = Math.sqrt(sigma2 * (1/Sw + xbar*xbar/Sxx));
    const t_stat = alpha / se_alpha;
    // Two-sided p via Acklam approximation (not exact for small df, but close)
    const df = points.length - 2;
    const p_two = _tTail2(Math.abs(t_stat), df);  // t_{k-2}, not normal (audit bug 5)
    return { alpha, se_alpha, t_stat, p: p_two, beta, k: points.length, points, df };
  }

  function buildBody(P, trials, deeks) {
    const fmt = P.fmt;
    let html = '';
    let toneCol, toneBg, toneBorder, verdict;
    if (deeks.p < 0.05) {
      toneCol = '#fbbf24'; toneBg = '#3a2a0a'; toneBorder = '#92400e';
      verdict = '⚠ Deeks\' test rejects symmetry: intercept α̂ = ' + fmt(deeks.alpha, 3)
              + ' (t = ' + fmt(deeks.t_stat, 2) + ', p = ' + fmt(deeks.p, 3)
              + ', df = ' + deeks.df + '). Funnel asymmetry suggests publication bias / small-study effects.';
    } else {
      toneCol = '#34d399'; toneBg = '#0e3a1f'; toneBorder = '#34d399';
      verdict = '✓ Deeks\' test does not reject symmetry: α̂ = ' + fmt(deeks.alpha, 3)
              + ' (p = ' + fmt(deeks.p, 3) + '). No evidence of small-study effects.';
    }
    html += '<div style="background:' + toneBg + ';border:1px solid ' + toneBorder + ';color:' + toneCol + ';padding:8px 10px;border-radius:6px;margin-bottom:10px;font-size:11.5px;">'
          + verdict + '</div>';

    // Funnel scatter
    const W = 720, H = 320, margin = { l: 60, r: 30, t: 30, b: 50 };
    const innerW = W - margin.l - margin.r, innerH = H - margin.t - margin.b;
    const xs = deeks.points.map(p => p.x);
    const ys = deeks.points.map(p => p.lnDOR);
    const xMin = Math.min(...xs) * 0.9, xMax = Math.max(...xs) * 1.1;
    const yMin = Math.min(...ys) - 0.5, yMax = Math.max(...ys) + 0.5;
    const x = v => margin.l + (v - xMin) / (xMax - xMin) * innerW;
    const y = v => margin.t + innerH - (v - yMin) / (yMax - yMin) * innerH;
    let svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="background:#0b1220;border-radius:6px;font-family:Inter,system-ui,sans-serif;">';
    svg += '<line x1="' + margin.l + '" x2="' + (W - margin.r) + '" y1="' + (H - margin.b) + '" y2="' + (H - margin.b) + '" stroke="#475569" />';
    svg += '<line x1="' + margin.l + '" x2="' + margin.l + '" y1="' + margin.t + '" y2="' + (H - margin.b) + '" stroke="#475569" />';
    // Regression line
    const xL = xMin, xR = xMax;
    const yL = deeks.alpha + deeks.beta * xL, yR = deeks.alpha + deeks.beta * xR;
    svg += '<line x1="' + x(xL) + '" y1="' + y(yL) + '" x2="' + x(xR) + '" y2="' + y(yR) + '" stroke="#fbbf24" stroke-width="2" />';
    // Points
    deeks.points.forEach(p => {
      svg += '<circle cx="' + x(p.x) + '" cy="' + y(p.lnDOR) + '" r="5" fill="#7dd3fc" fill-opacity="0.6" stroke="#0b1220" stroke-width="1"><title>' + (p.name || '?') + ': lnDOR=' + p.lnDOR.toFixed(2) + ', 1/√ESS=' + p.x.toFixed(3) + '</title></circle>';
    });
    svg += '<text x="' + (margin.l + innerW/2) + '" y="' + (H - margin.b + 32) + '" fill="#cbd5e1" font-size="11" text-anchor="middle">1 / √ESS (small studies right)</text>';
    svg += '<text transform="translate(' + (margin.l - 38) + ',' + (margin.t + innerH/2) + ') rotate(-90)" fill="#cbd5e1" font-size="11" text-anchor="middle">ln(DOR)</text>';
    svg += '<text x="' + margin.l + '" y="20" fill="#cbd5e1" font-size="11" font-weight="600">Deeks\' funnel — DTA publication bias</text>';
    svg += '</svg>';
    html += svg;

    // Method note
    html += '<div style="font-size:10.5px;color:#64748b;margin-top:8px;line-height:1.5;border-top:1px solid #1e293b;padding-top:8px;">'
          + '<strong>Method:</strong> regress ln(DOR) on 1/√ESS where ESS = 4·n₁·n₂/(n₁+n₂). '
          + 'Weights = 1/Var(ln DOR). The intercept α̂ tests funnel symmetry — α̂≠0 ⇒ small-study effect or publication bias. '
          + 'Deeks JJ et al. <em>J Clin Epidemiol</em> 2005;58:882–93. <br>'
          + '<strong>Limitations:</strong> low power for k<10; spurious positives possible when studies share threshold. '
          + 'Two-sided p approximated via z = |t|·√(df/(df+t²)) → normal CDF.'
          + '</div>';

    return html;
  }

  function render() {
    const P = global.PanelHelper;
    if (!P) return false;
    const trials = pickDTATrials(P.getRealData());
    if (trials.length < 4) return false;
    const deeks = deeksTest(trials);
    if (!deeks) return false;
    const summary = (deeks.p < 0.05 ? '⚠ ' : '✓ ')
                  + 'Deeks\' p = ' + P.fmt(deeks.p, 3)
                  + ' · α̂ = ' + P.fmt(deeks.alpha, 3)
                  + ' · k=' + deeks.k;
    const panel = P.buildCollapsiblePanel({
      id: 'dta-funnel-panel', badge: 'Deeks\' funnel', summary,
      bodyHtml: buildBody(P, trials, deeks), storageKey: STORAGE_KEY,
    });
    const existing = document.getElementById('dta-funnel-panel');
    if (existing) existing.replaceWith(panel); else P.insertAfterRBadge(panel);
    return true;
  }

  function bootstrap() {
    if (typeof document === 'undefined') return;
    let tries = 0;
    const tick = () => { if (render()) return; if (++tries < 20) setTimeout(tick, 250); };
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => setTimeout(tick, 1400));
    } else { setTimeout(tick, 1400); }
  }

  global.DTAFunnel = { render };
  bootstrap();
})(typeof window !== 'undefined' ? window : this);
