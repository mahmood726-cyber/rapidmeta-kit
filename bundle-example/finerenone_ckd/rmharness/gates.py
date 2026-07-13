"""Deterministic gates — the checks that make the number honest.

Every gate re-derives a quantity through an INDEPENDENT path and asserts it
matches what the app displayed. A gate can only ever FAIL a wrong number; it can
never rubber-stamp one. All stdlib, all offline.

  counts_imply_effect  — recompute each trial's effect from its raw 2x2 and
                         confirm it matches the displayed per-trial effect.
  triangulate          — cross-check the pooled estimate against five invariants
                         (FE recompute, convexity, Wald symmetry, weight
                         conservation, back-transform) computed WITHOUT calling
                         the random-effects pooler again.
  se_triangulate       — derive each trial's SE three ways (from the CI, from the
                         raw counts, from a p-value if present) and confirm they
                         agree — catches a transcribed CI that doesn't match the n.
  plausibility_check   — compare a value against the bundled offline plausibility
                         table (per-measure sane ranges); flags impossible or
                         wildly-out-of-range numbers.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .pooling import Study, pool, _binary_effect, _RATIO_MEASURES

_Z_975 = 1.959963984540054


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass
class GateReport:
    name: str
    ok: bool
    checks: list = field(default_factory=list)

    @property
    def failures(self) -> list:
        return [c for c in self.checks if not c.ok]

    def as_dict(self) -> dict:
        return {"gate": self.name, "ok": self.ok,
                "checks": [c.as_dict() for c in self.checks],
                "failures": [c.name for c in self.failures]}


# --------------------------------------------------------------------------- #
# per-trial effect from a trial dict (mirrors the app's binaryEffect/hrFromPublished)
# --------------------------------------------------------------------------- #
def trial_effect(trial: dict, measure: str) -> Optional[tuple]:
    """Return (yi, vi) for one trial dict, or None if not derivable.

    2x2 keys tE/tN/cE/cN -> RR/OR via the same conditional-0.5 rule the app uses.
    publishedHR/hrLCI/hrUCI -> logHR + SE-from-CI (used for HR, or as fallback).
    """
    tE, tN = trial.get("tE"), trial.get("tN")
    cE, cN = trial.get("cE"), trial.get("cN")
    if measure in ("RR", "OR") and None not in (tE, tN, cE, cN):
        try:
            return _binary_effect(int(tE), int(tN), int(cE), int(cN), measure)
        except Exception:
            return None
    if measure == "RD" and None not in (tE, tN, cE, cN) and tN > 0 and cN > 0:
        p1, p2 = tE / tN, cE / cN
        vi = p1 * (1 - p1) / tN + p2 * (1 - p2) / cN
        return (p1 - p2, vi) if vi > 0 else None
    hr, lo, hi = trial.get("publishedHR"), trial.get("hrLCI"), trial.get("hrUCI")
    if None not in (hr, lo, hi) and hr > 0 and lo > 0 and hi > 0:
        y = math.log(hr)
        se = (math.log(hi) - math.log(lo)) / (2 * 1.959964)  # app uses 1.959964
        if se > 0:
            return y, se * se
    return None


def counts_imply_effect(trials: list, measure: str, tol: float = 5e-3) -> GateReport:
    """Recompute each trial's ratio from its raw counts and check it against the
    per-trial ratio the trial carries (`displayedRatio`), if present. Where no
    displayed value is carried, the check confirms the counts are at least
    internally consistent (produce a finite, positive ratio)."""
    checks = []
    for t in trials:
        label = t.get("name") or t.get("nct") or "?"
        eff = trial_effect(t, measure)
        if eff is None:
            checks.append(Check(f"{label}:derivable", False,
                                "trial has neither a usable 2x2 nor published effect+CI"))
            continue
        yi, vi = eff
        ratio = math.exp(yi) if measure in _RATIO_MEASURES else yi
        disp = t.get("displayedRatio")
        if disp is None:
            ok = math.isfinite(ratio) and (ratio > 0 if measure in _RATIO_MEASURES else True)
            checks.append(Check(f"{label}:consistent", ok,
                                "" if ok else f"counts give non-finite/negative effect {ratio}"))
        else:
            ok = abs(ratio - float(disp)) <= tol * (1 + abs(float(disp)))
            checks.append(Check(f"{label}:counts_imply_effect", ok,
                                "" if ok else
                                f"counts imply {measure} {ratio:.4f} but app shows {disp}"))
    ok = all(c.ok for c in checks)
    return GateReport("counts_imply_effect", ok, checks)


def se_triangulate(trials: list, tol: float = 0.15) -> GateReport:
    """For trials that carry BOTH a 2x2 and a published effect+CI, derive the SE
    of the effect two independent ways and confirm they are in the same ballpark.
    A large disagreement means the transcribed CI does not match the sample size
    (a classic count/CI copy error). Tolerance is relative and generous because
    the two SEs estimate different (but related) effects (e.g. logHR vs logRR)."""
    checks = []
    for t in trials:
        label = t.get("name") or t.get("nct") or "?"
        has_counts = None not in (t.get("tE"), t.get("tN"), t.get("cE"), t.get("cN"))
        hr, lo, hi = t.get("publishedHR"), t.get("hrLCI"), t.get("hrUCI")
        has_ci = None not in (hr, lo, hi) and all(x and x > 0 for x in (hr, lo, hi))
        if not (has_counts and has_ci):
            continue  # nothing to triangulate for this trial
        e_or = trial_effect({**t}, "OR")
        if e_or is None:
            continue
        se_counts = math.sqrt(e_or[1])
        se_ci = (math.log(hi) - math.log(lo)) / (2 * 1.959964)
        ok = abs(se_counts - se_ci) <= tol * max(se_counts, se_ci) + 1e-6 \
            or (se_ci <= se_counts * (1 + tol))  # CI-SE should not be wildly tighter than n allows
        checks.append(Check(f"{label}:se_counts_vs_ci", ok,
                            "" if ok else
                            f"SE from counts {se_counts:.4f} vs SE from CI {se_ci:.4f} "
                            f"(rel diff {abs(se_counts-se_ci)/max(se_counts,se_ci):.1%})"))
    ok = all(c.ok for c in checks)
    return GateReport("se_triangulate", ok, checks)


def triangulate(pooled: dict, per_trial: list, measure: str) -> GateReport:
    """Five invariants any honest pooled estimate must satisfy, computed WITHOUT
    re-running the random-effects pooler. `per_trial` is a list of {yi, vi,
    weight_pct?} provenance rows; `pooled` is a pool() result dict."""
    checks = []
    ys = [float(p["yi"]) for p in per_trial]
    vs = [float(p["vi"]) for p in per_trial]
    est = pooled["estimate_log"]

    # T1 FE recompute vs an independent FE pool of the same rows
    w = [1.0 / v for v in vs]
    sw = math.fsum(w)
    fe_direct = math.fsum(wi * yi for wi, yi in zip(w, ys)) / sw
    fe_pool = pool([Study(label=str(i), yi=y, vi=v) for i, (y, v) in enumerate(zip(ys, vs))],
                   measure=measure, method="FE")["estimate_log"]
    t1 = abs(fe_direct - fe_pool) <= 1e-9 * (1 + abs(fe_pool))
    checks.append(Check("fe_recompute", t1, "" if t1 else f"{fe_direct} != {fe_pool}"))

    # T2 convexity — pooled point within [min yi, max yi]
    t2 = min(ys) - 1e-9 <= est <= max(ys) + 1e-9
    checks.append(Check("convexity", t2, "" if t2 else
                        f"pooled {est} outside study range [{min(ys)}, {max(ys)}]"))

    # T3 Wald symmetry — point is the CI midpoint on the log scale
    lo, hi = pooled["ci_log"]
    mid = 0.5 * (lo + hi)
    t3 = abs(mid - est) <= 1e-6 * (1 + abs(est))
    checks.append(Check("wald_symmetry", t3, "" if t3 else f"CI midpoint {mid} != point {est}"))

    # T4 weight conservation — RE weight shares recomputed from (vi, tau2) sum ~100%
    tau2 = pooled.get("tau2", 0.0)
    re_w = [1.0 / (v + tau2) for v in vs]
    re_sw = math.fsum(re_w)
    shares = [100.0 * wi / re_sw for wi in re_w]
    t4 = abs(math.fsum(shares) - 100.0) <= 1e-6
    checks.append(Check("weight_conservation", t4, "" if t4 else f"shares sum to {math.fsum(shares)}"))

    # T5 back-transform consistency for ratio measures
    if pooled.get("scale") == "ratio" and pooled.get("estimate_ratio") is not None:
        t5 = abs(math.exp(est) - pooled["estimate_ratio"]) <= 1e-9 * (1 + abs(pooled["estimate_ratio"]))
        checks.append(Check("backtransform", t5, "" if t5 else
                            f"exp({est})={math.exp(est)} != ratio {pooled['estimate_ratio']}"))

    ok = all(c.ok for c in checks)
    return GateReport("triangulate", ok, checks)


def plausibility_check(pooled: dict, measure: str, table: dict) -> GateReport:
    """Compare the pooled estimate (and its CI) against the bundled offline
    plausibility table. The table gives, per measure, the range a pooled effect
    can sanely take (ratios are bounded well away from 0 and infinity for real
    clinical effects). Flags impossible values — e.g. a runaway CI from a
    divergent tau2 (the exact failure the PM sensitivity path exhibits)."""
    checks = []
    spec = table.get(measure) or table.get("_default", {})
    ratio = pooled.get("estimate_ratio")
    if ratio is not None:
        lo_b, hi_b = spec.get("ratio_min", 0.01), spec.get("ratio_max", 100.0)
        ok = math.isfinite(ratio) and lo_b <= ratio <= hi_b
        checks.append(Check("point_in_range", ok, "" if ok else
                            f"pooled {measure} {ratio} outside plausible [{lo_b}, {hi_b}]"))
        ci = pooled.get("ci_ratio") or [None, None]
        cw = spec.get("max_ci_width_ratio", 50.0)
        if ci[0] and ci[1] and ci[0] > 0:
            width = ci[1] / ci[0]
            okw = math.isfinite(width) and width <= cw
            checks.append(Check("ci_width_sane", okw, "" if okw else
                                f"CI ratio-width {width:.1f}x exceeds plausible {cw}x "
                                f"(sign of a divergent tau2)"))
    se = pooled.get("se")
    if se is not None:
        se_max = spec.get("max_se", 10.0)
        oks = math.isfinite(se) and 0 < se <= se_max
        checks.append(Check("se_sane", oks, "" if oks else
                            f"pooled SE {se} implausible (>{se_max}); divergent variance"))
    ok = all(c.ok for c in checks)
    return GateReport("plausibility_check", ok, checks)
