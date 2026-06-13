/* paper-figures-synthesis.js — Synthēsis-journal-styled figures for Paper Studio.
 *
 * Bespoke offline SVG (no Plotly) reproducing the premium typeset look of the
 * Synthēsis metapaper PDF: forest-green weight-proportional squares, raw event
 * counts beneath each study, STUDY / OR (95% CI) / WEIGHT columns, a maroon
 * pooled diamond, a red 95%-prediction-interval bracket, a dotted no-effect
 * line, a log x-axis, and the signature hand-drawn curved-arrow annotation
 * callout. This is the DEFAULT forest renderer whenever the Synthēsis theme is
 * active; the writer can edit the callout text, toggle it, and set the x-range.
 * paper-figures.js (Plotly) remains the fallback for the plain/other themes.
 *
 * Palette matched to paper-synthesis.css:
 *   green #2f7d34 (markers) · brand green #054f16 · maroon #9c2b27 (pooled)
 *   ink #1d1d1b · grey #6f6f6a · rule #d6d8d1 · rose band rgba(156,43,39,.10)
 *
 * Pure string-building — no DOM needed to GENERATE the SVG (testable in node);
 * render*() helpers inject it into an element.
 */
(function () {
  "use strict";
  window.PaperStudio = window.PaperStudio || {};
  var PS = window.PaperStudio;

  var C = {
    green: "#2f7d34", greenDk: "#054f16", maroon: "#9c2b27", ink: "#1d1d1b",
    inkSoft: "#39413a", grey: "#6f6f6a", rule: "#d6d8d1", rose: "rgba(156,43,39,0.10)",
    serif: "Palatino Linotype, Palatino, Book Antiqua, Georgia, serif",
    sans: "Segoe UI, Helvetica Neue, Arial, sans-serif"
  };

  // --- minimal inverse-normal (Acklam) for CI bounds at the chosen level ---
  function normInv(p) {
    if (p <= 0) return -Infinity; if (p >= 1) return Infinity;
    var a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    var b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    var c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    var d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    var pl = 0.02425, ph = 1 - pl, q, r;
    if (p < pl) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    if (p <= ph) { q = p - 0.5; r = q * q; return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1); }
    q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  function num(v) { var n = Number(v); return (v === "" || v == null || !isFinite(n)) ? null : n; }
  function zFor(res) { var cl = Number(res && res.confLevel); if (!isFinite(cl) || cl <= 0) cl = 95; if (cl > 1) cl /= 100; return normInv(1 - (1 - cl) / 2); }
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function f2(x) { return (Math.round(x * 100) / 100).toFixed(2); }

  // Per-study natural-scale points, counts sub-label, and RE weight.
  function studyRows(res) {
    var z = zFor(res), cont = !!res.isContinuous, pd = res.plotData || [];
    var tau2 = num(res.tau2) || 0;
    var rows = [];
    pd.forEach(function (d) {
      var se = num(d.se); if (se == null || se <= 0) return;
      var center = cont ? num(d.md != null ? d.md : d.logOR) : num(d.logOR);
      if (center == null) return;
      var eff, lo, hi;
      if (cont) { eff = center; lo = center - z * se; hi = center + z * se; }
      else { eff = Math.exp(center); lo = Math.exp(center - z * se); hi = Math.exp(center + z * se); }
      var vi = num(d.vi) != null ? num(d.vi) : se * se;
      var w = 1 / (vi + tau2);
      var sub = "";
      var tE = num(d.tE), tN = num(d.tN), cE = num(d.cE), cN = num(d.cN);
      if (tN != null && tN > 0 && cN != null && cN > 0) sub = tE + "/" + tN + " vs " + cE + "/" + cN;
      rows.push({ name: d.id || d.name || "Study", sub: sub, eff: eff, lo: lo, hi: hi, w: w });
    });
    var sw = rows.reduce(function (a, r) { return a + r.w; }, 0) || 1;
    rows.forEach(function (r) { r.wp = r.w / sw; });
    return rows;
  }

  function niceTicks(lo, hi, cont) {
    if (cont) {
      // linear: ~6 round ticks
      var span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / 5)));
      var err = (span / 5) / step;
      if (err >= 7.5) step *= 10; else if (err >= 3.5) step *= 5; else if (err >= 1.5) step *= 2;
      var t = [], start = Math.ceil(lo / step) * step;
      for (var v = start; v <= hi + 1e-9; v += step) t.push(v);
      return t;
    }
    var cand = [0.1, 0.2, 0.25, 0.33, 0.5, 0.67, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50];
    return cand.filter(function (v) { return v >= lo * 0.999 && v <= hi * 1.001; });
  }

  /* Build the Synthēsis forest plot as an SVG string.
   * res: results-like {plotData, isContinuous, confLevel, or, lci, uci,
   *      piLCI, piUCI, k, effectMeasure, tau2}
   * opts: {xMin, xMax, label, annotation (string|false to hide), width} */
  PS.synthesisForestSVG = function (res, opts) {
    opts = opts || {};
    var cont = !!res.isContinuous;
    var rows = studyRows(res);
    var pEff = num(res.or), pLo = num(res.lci), pHi = num(res.uci);
    if (!rows.length && pEff == null) return "";
    var piLo = (res.piLCI != null && res.piLCI !== "--") ? num(res.piLCI) : null;
    var piHi = (res.piUCI != null && res.piUCI !== "--") ? num(res.piUCI) : null;
    var nullX = cont ? 0 : 1;
    var measure = res.effectMeasure || (cont ? "Mean difference" : "Odds ratio");

    // ---- geometry ----
    var W = num(opts.width) || 760;
    var labelR = 188;            // right edge of the study-label column
    var plotL = 212, plotR = W - 232;
    var orX = plotR + 26, wtX = W - 16;
    var rowH = 46, topPad = 44;
    var nStudy = rows.length;
    var yStudy0 = topPad + 18;
    var pooledY = yStudy0 + nStudy * rowH + 18;
    var piY = pooledY + 30;
    var axisY = (piLo != null ? piY : pooledY) + 40;
    var H = axisY + 52;

    // ---- x scale (log for ratio, linear for MD) ----
    var allLo = rows.map(function (r) { return r.lo; }).concat(pLo != null ? [pLo] : [], piLo != null ? [piLo] : []);
    var allHi = rows.map(function (r) { return r.hi; }).concat(pHi != null ? [pHi] : [], piHi != null ? [piHi] : []);
    var dataLo = Math.min.apply(null, allLo.concat([nullX]));
    var dataHi = Math.max.apply(null, allHi.concat([nullX]));
    var domLo = num(opts.xMin), domHi = num(opts.xMax);
    if (domLo == null || domHi == null || domLo >= domHi) {
      if (cont) { var pad = (dataHi - dataLo) * 0.12 || 1; domLo = dataLo - pad; domHi = dataHi + pad; }
      else { domLo = Math.min(nullX, dataLo) * 0.92; domHi = dataHi * 1.08; if (domLo <= 0) domLo = dataLo * 0.92; }
    }
    var tx = cont
      ? function (v) { return plotL + (v - domLo) / (domHi - domLo) * (plotR - plotL); }
      : function (v) { return plotL + (Math.log(v) - Math.log(domLo)) / (Math.log(domHi) - Math.log(domLo)) * (plotR - plotL); };

    var S = [];
    S.push('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" font-family="' + C.sans + '" width="100%" style="max-width:' + W + 'px;height:auto;background:#fff">');
    // defs: arrowhead for the annotation callout
    S.push('<defs><marker id="synArrow" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="' + C.maroon + '"/></marker></defs>');

    // ---- column headers ----
    var hdr = 'font-size="10" letter-spacing="0.10em" fill="' + C.grey + '"';
    S.push('<text x="0" y="' + topPad + '" ' + hdr + '>STUDY</text>');
    S.push('<text x="' + orX + '" y="' + topPad + '" ' + hdr + '>' + (cont ? "MD" : "OR") + ' (95% CI)</text>');
    S.push('<text x="' + wtX + '" y="' + topPad + '" text-anchor="end" ' + hdr + '>WEIGHT</text>');

    // ---- no-effect dotted line ----
    var xNull = tx(nullX);
    S.push('<line x1="' + xNull.toFixed(1) + '" y1="' + (topPad + 6) + '" x2="' + xNull.toFixed(1) + '" y2="' + (axisY) + '" stroke="' + C.grey + '" stroke-width="1" stroke-dasharray="2 3" opacity="0.7"/>');

    // ---- per-study rows ----
    var maxWp = Math.max.apply(null, rows.map(function (r) { return r.wp; }).concat([1e-6]));
    rows.forEach(function (r, i) {
      var yc = yStudy0 + i * rowH + rowH / 2 - 6;
      // label + counts
      S.push('<text x="' + labelR + '" y="' + (yc + 1) + '" text-anchor="end" font-size="12.5" font-weight="700" fill="' + C.ink + '">' + esc(r.name) + '</text>');
      if (r.sub) S.push('<text x="' + labelR + '" y="' + (yc + 15) + '" text-anchor="end" font-size="10" fill="' + C.grey + '">' + esc(r.sub) + '</text>');
      // CI line
      var xl = tx(r.lo), xh = tx(r.hi), xe = tx(r.eff);
      S.push('<line x1="' + xl.toFixed(1) + '" y1="' + yc + '" x2="' + xh.toFixed(1) + '" y2="' + yc + '" stroke="' + C.grey + '" stroke-width="1.3"/>');
      // weight-proportional square (area ∝ weight)
      var side = Math.max(6, 20 * Math.sqrt(r.wp / maxWp));
      S.push('<rect x="' + (xe - side / 2).toFixed(1) + '" y="' + (yc - side / 2).toFixed(1) + '" width="' + side.toFixed(1) + '" height="' + side.toFixed(1) + '" fill="' + C.green + '"/>');
      // right columns
      var ci = f2(r.eff) + ' (' + f2(r.lo) + '–' + f2(r.hi) + ')';
      S.push('<text x="' + orX + '" y="' + (yc + 1) + '" font-size="11.5" fill="' + C.ink + '">' + ci + '</text>');
      S.push('<text x="' + wtX + '" y="' + (yc + 1) + '" text-anchor="end" font-size="11" fill="' + C.grey + '">' + Math.round(r.wp * 100) + '%</text>');
    });

    // ---- pooled diamond ----
    if (pEff != null && pLo != null && pHi != null) {
      S.push('<text x="' + labelR + '" y="' + (pooledY + 1) + '" text-anchor="end" font-size="12.5" font-weight="700" fill="' + C.maroon + '">Pooled estimate</text>');
      S.push('<text x="' + labelR + '" y="' + (pooledY + 15) + '" text-anchor="end" font-size="9.5" fill="' + C.grey + '">random effects · ' + (num(res.k) || rows.length) + ' trials</text>');
      var dxl = tx(pLo), dxr = tx(pHi), dxe = tx(pEff), dh = 8;
      S.push('<polygon points="' + dxl.toFixed(1) + ',' + pooledY + ' ' + dxe.toFixed(1) + ',' + (pooledY - dh) + ' ' + dxr.toFixed(1) + ',' + pooledY + ' ' + dxe.toFixed(1) + ',' + (pooledY + dh) + '" fill="' + C.maroon + '"/>');
      S.push('<text x="' + orX + '" y="' + (pooledY + 1) + '" font-size="12.5" font-weight="700" fill="' + C.maroon + '">' + f2(pEff) + ' (' + f2(pLo) + '–' + f2(pHi) + ')</text>');
    }

    // ---- prediction-interval bracket ----
    if (piLo != null && piHi != null && pEff != null) {
      var bl = tx(piLo), br = tx(piHi);
      S.push('<line x1="' + bl.toFixed(1) + '" y1="' + piY + '" x2="' + br.toFixed(1) + '" y2="' + piY + '" stroke="' + C.maroon + '" stroke-width="1.4"/>');
      S.push('<line x1="' + bl.toFixed(1) + '" y1="' + (piY - 4) + '" x2="' + bl.toFixed(1) + '" y2="' + (piY + 4) + '" stroke="' + C.maroon + '" stroke-width="1.4"/>');
      S.push('<line x1="' + br.toFixed(1) + '" y1="' + (piY - 4) + '" x2="' + br.toFixed(1) + '" y2="' + (piY + 4) + '" stroke="' + C.maroon + '" stroke-width="1.4"/>');
      S.push('<text x="' + (br + 8).toFixed(1) + '" y="' + (piY + 3) + '" font-size="10.5" font-style="italic" fill="' + C.maroon + '">95% prediction interval ' + f2(piLo) + '–' + f2(piHi) + '</text>');
    }

    // ---- x-axis ----
    S.push('<line x1="' + plotL + '" y1="' + axisY + '" x2="' + plotR + '" y2="' + axisY + '" stroke="' + C.inkSoft + '" stroke-width="1"/>');
    niceTicks(domLo, domHi, cont).forEach(function (v) {
      var x = tx(v);
      if (x < plotL - 1 || x > plotR + 1) return;
      S.push('<line x1="' + x.toFixed(1) + '" y1="' + axisY + '" x2="' + x.toFixed(1) + '" y2="' + (axisY + 4) + '" stroke="' + C.inkSoft + '" stroke-width="1"/>');
      S.push('<text x="' + x.toFixed(1) + '" y="' + (axisY + 16) + '" text-anchor="middle" font-size="10.5" fill="' + C.inkSoft + '">' + (cont ? (Math.round(v * 100) / 100) : v) + '</text>');
    });
    S.push('<text x="' + ((plotL + plotR) / 2).toFixed(1) + '" y="' + (axisY + 34) + '" text-anchor="middle" font-size="11" fill="' + C.inkSoft + '">' + esc(measure) + (cont ? '' : ' (log scale)') + '</text>');

    // ---- annotation callout (default-on, editable) ----
    var ann = opts.annotation;
    if (ann !== false && pEff != null) {
      if (ann == null || ann === true) ann = PS.defaultForestAnnotation(res);
      if (ann) {
        // Sit in the empty wedge left of the diamond, at the pooled-row height,
        // so it never crosses a study CI. Wrap narrow to stay in that column.
        var lines = wrapText(ann, 30);
        var ax = plotL + 4;
        var blockH = lines.length * 13;
        var ay = pooledY - blockH - 6;                    // block ends just above the diamond
        if (ay < yStudy0 + 8) ay = yStudy0 + 8;           // never collide with row 1
        S.push('<text x="' + ax + '" y="' + ay + '" font-size="10.5" font-style="italic" fill="' + C.inkSoft + '">');
        lines.forEach(function (ln, j) { S.push('<tspan x="' + ax + '" dy="' + (j === 0 ? 0 : 13) + '">' + esc(ln) + '</tspan>'); });
        S.push('</text>');
        // short curved arrow from the block to the diamond's left vertex
        var ty = ay + blockH - 6;
        var dxl2 = tx(pLo != null ? pLo : pEff);
        var sx = Math.min(ax + 150, dxl2 - 30);
        S.push('<path d="M' + sx.toFixed(0) + ',' + ty.toFixed(0) + ' Q' + ((sx + dxl2) / 2).toFixed(0) + ',' + (pooledY - 2) + ' ' + (dxl2 - 4).toFixed(0) + ',' + pooledY + '" fill="none" stroke="' + C.maroon + '" stroke-width="1.1" marker-end="url(#synArrow)" opacity="0.85"/>');
      }
    }

    S.push('</svg>');
    return S.join("");
  };

  // The default narrative callout, in the PDF's voice.
  PS.defaultForestAnnotation = function (res) {
    var pEff = num(res.or), pLo = num(res.lci), pHi = num(res.uci), k = num(res.k);
    if (pEff == null) return "";
    var cont = !!res.isContinuous, nullX = cont ? 0 : 1;
    var measure = cont ? "mean difference" : "odds ratio";
    var excludes = (pLo != null && pHi != null) && (pLo > nullX || pHi < nullX);
    var s = "Pooled " + measure + " " + f2(pEff);
    if (pLo != null && pHi != null) s += " (95% CI " + f2(pLo) + "–" + f2(pHi) + ")";
    s += "; ";
    if (k) s += "all " + k + " trials point the same way and the ";
    s += "interval " + (excludes ? "excludes" : "includes") + " no effect.";
    return s;
  };

  function wrapText(s, n) {
    var words = String(s).split(/\s+/), lines = [], cur = "";
    words.forEach(function (w) {
      if ((cur + " " + w).trim().length > n) { if (cur) lines.push(cur); cur = w; }
      else cur = (cur ? cur + " " : "") + w;
    });
    if (cur) lines.push(cur);
    return lines;
  }

  // DOM render helper.
  PS.renderForestSynthesis = function (el, res, opts) {
    if (!el || !res) return false;
    var svg = PS.synthesisForestSVG(res, opts);
    if (!svg) return false;
    el.innerHTML = svg;
    return true;
  };

  // True when the Synthēsis theme is the active paper skin (it is the default).
  PS.isSynthesisTheme = function () {
    if (typeof document === "undefined") return false;
    var c = document.getElementById("paperCanvas");
    return !!(c && c.classList && c.classList.contains("paper-synthesis"));
  };
})();
