/*
 * r_parity_harness.cjs
 *
 * Standalone Node harness for the RapidMeta R-parity validation dossier.
 *
 * The meta-analysis math in RapidMeta is inline inside
 *   template/base_dupilumab_copd.html
 * (the dashboard is a single self-contained HTML file). The functions below are
 * PORTED VERBATIM from that file so this harness exercises the SAME numerical
 * code path the dashboard ships. Source line numbers (as of WORKDIR) are noted
 * at each function so a reviewer can diff against the HTML.
 *
 * Verbatim-ported pieces:
 *   - normalQuantile  (HTML ~L5468)  Acklam inverse-normal
 *   - normalCDF       (HTML ~L5504)  erfc approximation
 *   - lgamma          (HTML ~L5537)  Lanczos
 *   - betaIncomplete  (HTML ~L5567)  continued fraction
 *   - tQuantile       (HTML ~L5639)  Cornish-Fisher + Newton refine (t_{df})
 *   - qchisq          (HTML ~L5711)  chi-square quantile (Wilson-Hilferty for df>=3)
 *   - qProfileTau2CI  (HTML ~L5728)  Viechtbauer 2007 Q-profile tau2 CI
 *   - RR effect + variance, Q, I2, DL tau2, REML Fisher-scoring tau2,
 *     RE pooling, HKSJ, prediction interval (HTML ~L31794-31976)
 *
 * Output: a single JSON object printed on the last stdout line.
 */

'use strict';

/* ============================ verbatim helpers ============================ */

// HTML ~L5468 (Acklam inverse normal CDF)
const normalQuantile = (p) => {
    const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.383577518672690e2, -3.066479806614716e1, 2.506628277459239e0];
    const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
    const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838e0, -2.549732539343734e0, 4.374664141464968e0, 2.938163982698783e0];
    const dd = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996e0, 3.754408661907416e0];
    const pLow = 0.02425, pHigh = 1 - pLow;
    let q, r;
    if (p < pLow) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1); }
    if (p <= pHigh) { q = p - 0.5; r = q*q; return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1); }
    q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1);
};

// HTML ~L5504
const normalCDF = (x) => {
    if (x < -8) return 0;
    if (x > 8) return 1;
    const aa = [0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429];
    const pp = 0.3275911;
    const z = Math.abs(x) / Math.SQRT2;
    const t = 1 / (1 + pp * z);
    const erfc = ((((aa[4]*t + aa[3])*t + aa[2])*t + aa[1])*t + aa[0]) * t * Math.exp(-z*z);
    return x >= 0 ? 1 - 0.5 * erfc : 0.5 * erfc;
};

// HTML ~L5537
const lgamma = (x) => {
    const gc = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * x)) - lgamma(1 - x);
    x -= 1;
    let ag = gc[0];
    const t = x + 7.5;
    for (let i = 1; i < 9; i++) ag += gc[i] / (x + i);
    return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(ag);
};

// HTML ~L5567
const betaIncomplete = (x, a, b) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    if (x > (a + 1) / (a + b + 2)) return 1 - betaIncomplete(1 - x, b, a);
    const lnBeta = lgamma(a) + lgamma(b) - lgamma(a + b);
    const front = Math.exp(a * Math.log(x) + b * Math.log(1 - x) - lnBeta) / a;
    let f = 1, cc = 1, dd = 1 - (a + b) * x / (a + 1);
    if (Math.abs(dd) < 1e-30) dd = 1e-30;
    dd = 1 / dd; f = dd;
    for (let m = 1; m <= 200; m++) {
        let num = m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m));
        dd = 1 + num * dd; if (Math.abs(dd) < 1e-30) dd = 1e-30;
        cc = 1 + num / cc; if (Math.abs(cc) < 1e-30) cc = 1e-30;
        dd = 1 / dd; f *= cc * dd;
        num = -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1));
        dd = 1 + num * dd; if (Math.abs(dd) < 1e-30) dd = 1e-30;
        cc = 1 + num / cc; if (Math.abs(cc) < 1e-30) cc = 1e-30;
        dd = 1 / dd;
        const delta = cc * dd; f *= delta;
        if (Math.abs(delta - 1) < 1e-10) break;
    }
    return front * f;
};

// HTML ~L5639  (Student-t quantile, t_{df})
const tQuantile = (p, df) => {
    if (df <= 0) return normalQuantile(p);
    if (df === 1) return Math.tan(Math.PI * (p - 0.5));
    if (df === 2) { const sign = p >= 0.5 ? 1 : -1; const alpha = 2 * Math.min(p, 1-p); return sign * Math.sqrt(2 / (alpha * (2 - alpha)) - 2); }
    const z = normalQuantile(p), z2 = z * z;
    let t = z + (z2 + 1)*z/(4*df) + ((5*z2 + 16)*z2 + 3)*z/(96*df*df) + (((3*z2 + 19)*z2 + 17)*z2 - 15)*z/(384*df*df*df);
    if (df <= 8) {
        for (let _nr = 0; _nr < 6; _nr++) {
            const cdf = 0.5 + 0.5 * (1 - betaIncomplete(df / (df + t * t), df / 2, 0.5)) * (t >= 0 ? 1 : -1);
            const pdf = Math.exp(lgamma((df + 1) / 2) - lgamma(df / 2) - 0.5 * Math.log(Math.PI * df) - (df + 1) / 2 * Math.log(1 + t * t / df));
            if (pdf < 1e-15) break;
            t -= (cdf - p) / pdf;
        }
    }
    return t;
};

// HTML ~L5711
const qchisq = (p, df) => {
    if (df <= 0 || p <= 0) return 0;
    if (p >= 1) return Infinity;
    if (df === 1) { const z = normalQuantile((1 + p) / 2); return z * z; }
    if (df === 2) return -2 * Math.log(1 - p);
    const z = normalQuantile(p);
    const v = 1 - 2/(9*df) + z * Math.sqrt(2/(9*df));
    return Math.max(0, df * v * v * v);
};

// HTML ~L5728  (Viechtbauer 2007 Q-profile tau2 CI)
const qProfileTau2CI = (yi, vi, df, alpha) => {
    if (df < 1 || yi.length < 2) return { tau2_lo: NaN, tau2_hi: NaN };
    const qGen = (tau2) => {
        let sW = 0, sWY = 0, sW_Y2 = 0;
        for (let i = 0; i < yi.length; i++) {
            const w = 1 / (vi[i] + tau2);
            sW += w;
            sWY += w * yi[i];
            sW_Y2 += w * yi[i] * yi[i];
        }
        if (sW === 0) return 0;
        return Math.max(0, sW_Y2 - (sWY * sWY) / sW);
    };
    const cutHi = qchisq(1 - alpha/2, df);
    const cutLo = qchisq(alpha/2, df);
    const Q0 = qGen(0);
    const bisect = (target) => {
        if (Q0 <= target) return 0;
        let lo = 0, hi = 100;
        for (let _e = 0; _e < 30 && qGen(hi) > target && hi < 1e8; _e++) hi *= 2;
        for (let _i = 0; _i < 60; _i++) {
            const mid = (lo + hi) / 2;
            if (qGen(mid) > target) lo = mid; else hi = mid;
        }
        return (lo + hi) / 2;
    };
    return { tau2_lo: bisect(cutHi), tau2_hi: bisect(cutLo) };
};

/* ===================== core RE meta-analysis (ported) ===================== */
/*
 * Mirrors the dashboard's RR engine block (HTML ~L31794-31976).
 * Inputs:
 *   studies: array of { logEff, vi }   (already on the log scale)
 *   confLevel: e.g. 0.95
 *   measure: "RR"/"OR"/"logRR" (cosmetic; pooling is on the log scale)
 * Returns pooled estimate (log scale) + SE + CI, tau2 (REML), tau2 (DL),
 * tau2 Q-profile CI, Q, I2, I2 Q-profile CI, HKSJ CI, prediction interval.
 */
function reMetaAnalysis(studies, confLevel) {
    const plotData = studies.map(s => ({ logOR: s.logEff, vi: s.vi, w_fixed: 1 / s.vi }));
    const k = plotData.length;
    const df = k - 1;
    const zCrit = normalQuantile(1 - (1 - confLevel) / 2);

    // fixed-effect accumulators
    let sW = 0, sWY = 0, sW_y2 = 0, sW2 = 0;
    plotData.forEach(d => { sW += d.w_fixed; sWY += d.w_fixed * d.logOR; sW_y2 += d.w_fixed * d.logOR * d.logOR; sW2 += Math.pow(d.w_fixed, 2); });

    const Q = Math.max(0, sW_y2 - (Math.pow(sWY, 2) / sW));
    const I2 = (Q > df) ? ((Q - df) / Q) * 100 : 0;

    // DL tau2 (HTML ~L31813)
    const tau2_dl = (Q > df) ? (Q - df) / (sW - (sW2 / sW)) : 0;

    // REML tau2 via Fisher scoring (HTML ~L31820-31877)
    let tau2_reml = tau2_dl;
    if (k >= 2) {
        const _yi = plotData.map(d => d.logOR);
        const _vi = plotData.map(d => d.vi);
        for (let _it = 0; _it < 100; _it++) {
            const _w = _vi.map(v => 1 / (v + tau2_reml));
            const _sW = _w.reduce((a, b) => a + b, 0);
            const _mu = _w.reduce((a, wi, i) => a + wi * _yi[i], 0) / _sW;
            const _sW2 = _w.reduce((a, wi) => a + wi * wi, 0);
            const _sW3 = _w.reduce((a, wi) => a + wi * wi * wi, 0);
            const _trP = _sW - _sW2 / _sW;
            const _yP2y = _w.reduce((a, wi, i) => a + wi * wi * Math.pow(_yi[i] - _mu, 2), 0);
            const _trP2 = _sW2 - 2 * _sW3 / _sW + _sW2 * _sW2 / (_sW * _sW);
            if (_trP2 < 1e-15) break;
            const _delta = (_yP2y - _trP) / _trP2;
            const _new = Math.max(0, tau2_reml + _delta);
            if (Math.abs(_new - tau2_reml) < 1e-10) { tau2_reml = _new; break; }
            tau2_reml = _new;
        }
    }

    const tau2 = (k >= 2) ? tau2_reml : tau2_dl;

    // Q-profile tau2 CI (HTML ~L31884-31886)
    const _qpYi = plotData.map(d => d.logOR);
    const _qpVi = plotData.map(d => d.vi);
    const { tau2_lo: tau2Lo, tau2_hi: tau2Hi } = qProfileTau2CI(_qpYi, _qpVi, df, 1 - confLevel);

    // I2 Q-profile CI (HTML ~L31889-31900)
    let I2_lo_qp = 0, I2_hi_qp = 0;
    if (k >= 2) {
        const _wfx = _qpVi.map(v => 1 / v);
        const _sWfx = _wfx.reduce((a, b) => a + b, 0);
        const _sWfx2 = _wfx.reduce((a, w) => a + w * w, 0);
        const _denom = (_sWfx * _sWfx) - _sWfx2;
        const _s2 = (_denom > 0) ? ((k - 1) * _sWfx) / _denom : 0;
        if (_s2 > 0) {
            I2_lo_qp = Number.isFinite(tau2Lo) ? Math.max(0, 100 * tau2Lo / (tau2Lo + _s2)) : 0;
            I2_hi_qp = Number.isFinite(tau2Hi) ? Math.min(100, 100 * tau2Hi / (tau2Hi + _s2)) : 0;
        }
    }

    // RE pooling (HTML ~L31903-31924)
    let sWR = 0, sWRY = 0;
    plotData.forEach(d => { const wr = 1 / (d.vi + tau2); d.w_random = wr; sWR += wr; sWRY += wr * d.logOR; });
    const pLogOR = sWRY / sWR;
    const pSE = Math.sqrt(1 / sWR);
    const lci = pLogOR - zCrit * pSE;   // log scale
    const uci = pLogOR + zCrit * pSE;

    // HKSJ (HTML ~L31930-31960) -- note floor is max(1, qStar)
    let hksjLCI = NaN, hksjUCI = NaN, hksjAdj = NaN;
    if (k >= 2) {
        let qStar = 0;
        plotData.forEach(d => { qStar += d.w_random * Math.pow(d.logOR - pLogOR, 2); });
        qStar = qStar / df;
        hksjAdj = Math.max(1, qStar);
        const hksjSE = Math.sqrt(hksjAdj / sWR);
        const tCritHKSJ = tQuantile(1 - (1 - confLevel) / 2, df);
        hksjLCI = pLogOR - tCritHKSJ * hksjSE;   // log scale
        hksjUCI = pLogOR + tCritHKSJ * hksjSE;
    }

    // Prediction interval, t_{k-1} (HTML ~L31963-31976)
    const piSE = Math.sqrt(tau2 + pSE * pSE);
    const tCritPI = (k >= 2) ? tQuantile(1 - (1 - confLevel) / 2, k - 1) : NaN;
    const piLCI = (k >= 2) ? (pLogOR - tCritPI * piSE) : NaN;   // log scale
    const piUCI = (k >= 2) ? (pLogOR + tCritPI * piSE) : NaN;

    return {
        k, df, Q, I2, I2_lo_qp, I2_hi_qp,
        tau2_dl, tau2_reml, tau2, tau2Lo, tau2Hi,
        pLogOR, pSE, lci, uci, zCrit,
        hksjAdj, hksjLCI, hksjUCI,
        piSE, piLCI, piUCI,
    };
}

/* RR effect + variance from a 2x2 table (HTML ~L31752-31764).
 * a=tE+adj, b=tN-tE+adj, c=cE+adj, d=cN-cE+adj
 * logRR = log( (a/(a+b)) / (c/(c+d)) )
 * vi    = b/(a*(a+b)) + d/(c*(c+d))
 * Zero-cell correction (+0.5) only when a cell is zero/complete (matches HTML). */
function rrFromCounts(tE, tN, cE, cN) {
    const hasZero = (tE === 0 || cE === 0 || tE === tN || cE === cN);
    const adj = hasZero ? 0.5 : 0;
    const a = tE + adj, b = tN - tE + adj, c = cE + adj, d = cN - cE + adj;
    const logEff = Math.log((a / (a + b)) / (c / (c + d)));
    const vi = b / (a * (a + b)) + d / (c * (c + d));
    return { logEff, vi };
}

/* ================================ datasets ================================ */

// metafor dat.bcg (Colditz et al. 1994). Columns: trial, tpos, tneg, cpos, cneg.
// tpos = vaccinated TB+, tneg = vaccinated TB-, cpos = control TB+, cneg = control TB-.
const dat_bcg = [
    { trial: 1,  tpos: 4,   tneg: 119,   cpos: 11,  cneg: 128 },
    { trial: 2,  tpos: 6,   tneg: 300,   cpos: 29,  cneg: 274 },
    { trial: 3,  tpos: 3,   tneg: 228,   cpos: 11,  cneg: 209 },
    { trial: 4,  tpos: 62,  tneg: 13536, cpos: 248, cneg: 12619 },
    { trial: 5,  tpos: 33,  tneg: 5036,  cpos: 47,  cneg: 5761 },
    { trial: 6,  tpos: 180, tneg: 1361,  cpos: 372, cneg: 1079 },
    { trial: 7,  tpos: 8,   tneg: 2537,  cpos: 10,  cneg: 619 },
    { trial: 8,  tpos: 505, tneg: 87886, cpos: 499, cneg: 87892 },
    { trial: 9,  tpos: 29,  tneg: 7470,  cpos: 45,  cneg: 7232 },
    { trial: 10, tpos: 17,  tneg: 1699,  cpos: 65,  cneg: 1600 },
    { trial: 11, tpos: 186, tneg: 50448, cpos: 141, cneg: 27197 },
    { trial: 12, tpos: 5,   tneg: 2493,  cpos: 3,   cneg: 2338 },
    { trial: 13, tpos: 27,  tneg: 16886, cpos: 29,  cneg: 17825 },
];

// Map dat.bcg to (tE,tN,cE,cN): tN = tpos+tneg, cN = cpos+cneg.
const bcgStudies = dat_bcg.map(r => {
    const tE = r.tpos, tN = r.tpos + r.tneg, cE = r.cpos, cN = r.cpos + r.cneg;
    return rrFromCounts(tE, tN, cE, cN);
});

const bcg = reMetaAnalysis(bcgStudies, 0.95);

/* Hand-exact fixed-effect inverse-variance case.
 * Three studies with hand-chosen logEff/vi so the FE pool is exact by hand:
 *   y = [0.20, 0.40, 0.60],  v = [0.04, 0.01, 0.04]  (=> w = 25, 100, 25)
 *   sumW   = 150
 *   sumWY  = 25*0.20 + 100*0.40 + 25*0.60 = 5 + 40 + 15 = 60
 *   muFE   = 60 / 150 = 0.40            (exact)
 *   seFE   = sqrt(1/150) = 0.081649658092772615...
 *   Q      = sumW*y^2 - (sumWY)^2/sumW
 *          = (25*0.04 + 100*0.16 + 25*0.36) - 60^2/150
 *          = (1 + 16 + 9) - 3600/150 = 26 - 24 = 2   (exact)
 * These are derived purely by hand here; no metafor needed. We expose the FE
 * pool directly (RE collapses to FE only when tau2=0; here tau2>0, so we report
 * the FE quantities separately, computed independently).
 */
function fixedEffectPool(y, v) {
    let sumW = 0, sumWY = 0, sumWY2 = 0;
    for (let i = 0; i < y.length; i++) {
        const w = 1 / v[i];
        sumW += w; sumWY += w * y[i]; sumWY2 += w * y[i] * y[i];
    }
    const mu = sumWY / sumW;
    const se = Math.sqrt(1 / sumW);
    const Q = sumWY2 - (sumWY * sumWY) / sumW;
    return { mu, se, Q, sumW };
}

const feY = [0.20, 0.40, 0.60];
const feV = [0.04, 0.01, 0.04];
const feExact = fixedEffectPool(feY, feV);

/* ================================ output ================================ */

const out = {
    bcg: {
        k: bcg.k, df: bcg.df,
        Q: bcg.Q, I2: bcg.I2,
        pooled_logRR: bcg.pLogOR,
        pooled_SE: bcg.pSE,
        ci_lo_logRR: bcg.lci,
        ci_hi_logRR: bcg.uci,
        pooled_RR: Math.exp(bcg.pLogOR),
        ci_lo_RR: Math.exp(bcg.lci),
        ci_hi_RR: Math.exp(bcg.uci),
        tau2_reml: bcg.tau2_reml,
        tau2_dl: bcg.tau2_dl,
        tau2_qprofile_lo: bcg.tau2Lo,
        tau2_qprofile_hi: bcg.tau2Hi,
        I2_qprofile_lo: bcg.I2_lo_qp,
        I2_qprofile_hi: bcg.I2_hi_qp,
        pi_lo_logRR: bcg.piLCI,
        pi_hi_logRR: bcg.piUCI,
        pi_lo_RR: Math.exp(bcg.piLCI),
        pi_hi_RR: Math.exp(bcg.piUCI),
        hksj_adj: bcg.hksjAdj,
        hksj_lo_logRR: bcg.hksjLCI,
        hksj_hi_logRR: bcg.hksjUCI,
        per_study: bcgStudies.map((s, i) => ({ trial: dat_bcg[i].trial, logRR: s.logEff, vi: s.vi })),
    },
    fixed_effect_exact: {
        y: feY, v: feV,
        mu: feExact.mu,
        se: feExact.se,
        Q: feExact.Q,
        sumW: feExact.sumW,
    },
};

console.log(JSON.stringify(out));
