"""verify.py — reproduce the app's number and check it, from the bundle.

Every function is deterministic and offline. `reproduce` is the load-bearing
one: it re-pools the bundled trials with the independent stdlib engine and
compares, field by field, to the frozen reference the app displayed. If they
match, the review reproduces; if not, the harness has proven the app wrong.
"""
from __future__ import annotations

import json
import os

from . import bundle as _bundle
from .pooling import pool
from . import gates as _gates

_REL = 1e-6   # relative tolerance for "reproduces exactly" on the log scale
_ABS = 1e-9


def _close(a, b, rel=_REL, abs_=_ABS) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= abs_ + rel * (1 + abs(b))


def reproduce(bundle: dict, tol_rel: float = _REL) -> dict:
    """Re-pool the bundled trials and compare to the frozen reference.

    Returns a dict with `passed`, the recomputed result, the reference, and a
    per-field diff. `passed` is True iff the pooled point estimate (log scale),
    SE, CI, tau2, Q and I2 all reproduce within tolerance."""
    measure = bundle["measure"]
    method = bundle.get("method", "REML")
    ref = bundle["reference"]
    got = pool(_bundle.studies(bundle, measure), measure=measure, method=method)

    fields = ["estimate_log", "se", "tau2", "Q", "I2_percent", "estimate_ratio"]
    diffs = {}
    ok = True
    for f in fields:
        rv, gv = ref.get(f), got.get(f)
        match = _close(gv, rv, rel=tol_rel)
        diffs[f] = {"reference": rv, "recomputed": gv,
                    "abs_diff": (abs(gv - rv) if (rv is not None and gv is not None) else None),
                    "match": match}
        ok = ok and match
    # CI (log scale) both ends
    for i, side in enumerate(("ci_lo", "ci_hi")):
        rv = ref.get("ci_log", [None, None])[i]
        gv = got.get("ci_log", [None, None])[i]
        match = _close(gv, rv, rel=max(tol_rel, 1e-6))
        diffs[side] = {"reference": rv, "recomputed": gv,
                       "abs_diff": (abs(gv - rv) if (rv is not None and gv is not None) else None),
                       "match": match}
        ok = ok and match

    return {"passed": ok, "measure": measure, "method": method,
            "recomputed": got, "reference": ref, "diffs": diffs}


def add_trial(bundle: dict, trial: dict) -> dict:
    """Re-pool with one hand-added trial and report the estimate move."""
    measure = bundle["measure"]
    method = bundle.get("method", "REML")
    base = pool(_bundle.studies(bundle, measure), measure=measure, method=method)
    new = pool(_bundle.studies(bundle, measure, extra=[trial]), measure=measure, method=method)
    return _move("add", trial.get("name") or trial.get("nct") or "new trial",
                 base, new, measure)


def remove_trial(bundle: dict, name: str) -> dict:
    """Re-pool without a named trial and report the estimate move."""
    measure = bundle["measure"]
    method = bundle.get("method", "REML")
    base = pool(_bundle.studies(bundle, measure), measure=measure, method=method)
    new = pool(_bundle.studies(bundle, measure, drop=name), measure=measure, method=method)
    return _move("remove", name, base, new, measure)


def remeasure(bundle: dict, measure: str) -> dict:
    """Re-derive the pooled estimate under a different effect measure."""
    method = bundle.get("method", "REML")
    base_m = bundle["measure"]
    base = pool(_bundle.studies(bundle, base_m), measure=base_m, method=method)
    new = pool(_bundle.studies(bundle, measure), measure=measure, method=method)
    return {"action": "remeasure", "from": base_m, "to": measure,
            "before": _summ(base, base_m), "after": _summ(new, measure)}


def _move(action, name, base, new, measure) -> dict:
    return {"action": action, "trial": name,
            "before": _summ(base, measure), "after": _summ(new, measure),
            "delta_ratio": (None if new.get("estimate_ratio") is None
                            else new["estimate_ratio"] - base["estimate_ratio"])}


def _summ(r, measure) -> dict:
    return {"measure": measure, "k": r["k"], "estimate_ratio": r.get("estimate_ratio"),
            "ci_ratio": r.get("ci_ratio"), "estimate_log": r["estimate_log"],
            "tau2": r["tau2"], "I2_percent": r["I2_percent"], "Q": r["Q"]}


def run_gates(bundle: dict, bundle_dir: str = ".") -> dict:
    """Run every deterministic gate on the bundle and return a combined report."""
    measure = bundle["measure"]
    method = bundle.get("method", "REML")
    studies = _bundle.studies(bundle, measure)
    got = pool(studies, measure=measure, method=method)
    # provenance rows (yi, vi) for triangulation, in study order
    per_trial = []
    for s in studies:
        if s.yi is not None:
            per_trial.append({"yi": s.yi, "vi": s.vi})
        else:
            from .pooling import _binary_effect
            yi, vi = _binary_effect(s.ai, s.n1, s.ci, s.n2, measure)
            per_trial.append({"yi": yi, "vi": vi})

    table = _load_table(bundle, bundle_dir)
    reports = [
        _gates.counts_imply_effect(bundle["trials"], measure),
        _gates.se_triangulate(bundle["trials"]),
        _gates.triangulate(got, per_trial, measure),
        _gates.plausibility_check(got, measure, table),
    ]
    ok = all(r.ok for r in reports)
    # protocol-hash / pre-registration check
    hash_ok, computed, expected = _bundle.verify_protocol_hash(bundle, bundle_dir)
    return {"passed": ok and (hash_ok is not False),
            "gates": [r.as_dict() for r in reports],
            "protocol_hash": {"ok": hash_ok, "computed": computed, "expected": expected}}


def compare_published(bundle: dict) -> dict:
    """Compare the recomputed pooled estimate to the bundled published-MA value(s)
    (e.g. Cochrane reference). Reports the difference and whether the recomputed
    point falls inside the published CI (and vice versa)."""
    measure = bundle["measure"]
    method = bundle.get("method", "REML")
    got = pool(_bundle.studies(bundle, measure), measure=measure, method=method)
    pubs = bundle.get("published_comparison")
    if pubs is None:
        return {"available": False}
    if isinstance(pubs, dict):
        pubs = [pubs]
    rows = []
    ours = got.get("estimate_ratio")
    our_ci = got.get("ci_ratio") or [None, None]
    for p in pubs:
        pe, pci = p.get("estimate"), p.get("ci") or [None, None]
        inside = (pci[0] is not None and ours is not None and pci[0] <= ours <= pci[1])
        rows.append({"label": p.get("label"), "source": p.get("source"),
                     "published": pe, "published_ci": pci,
                     "ours": ours, "our_ci": our_ci,
                     "abs_diff": (abs(ours - pe) if (ours is not None and pe is not None) else None),
                     "ours_inside_published_ci": inside})
    return {"available": True, "measure": measure, "rows": rows}


def _load_table(bundle: dict, bundle_dir: str) -> dict:
    name = bundle.get("plausibility_table", "plausibility_table.json")
    for cand in (os.path.join(bundle_dir, name),
                 os.path.join(os.path.dirname(__file__), "plausibility_table.json")):
        if os.path.exists(cand):
            with open(cand, "r", encoding="utf-8") as fh:
                return json.load(fh)
    return {}
