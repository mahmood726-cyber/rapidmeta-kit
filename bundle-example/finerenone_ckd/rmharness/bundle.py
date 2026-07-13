"""Load a RapidMeta review bundle and turn its trials into poolable studies.

A bundle is a self-describing JSON manifest (schema `rapidmeta-bundle/v1`) that
ships alongside the app. It carries the exact trial data the app pooled, the
frozen reference result (the number the app DISPLAYS, computed by the app's own
engine), the protocol + its SHA-256, the git commit, per-value provenance, and
the published-MA comparison values. Everything the harness needs to reproduce
and check the review is in this one file — no network, no model.
"""
from __future__ import annotations

import hashlib
import json
import os

from .pooling import Study

SCHEMA = "rapidmeta-bundle/v1"


class BundleError(ValueError):
    pass


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        b = json.load(fh)
    if b.get("schema") != SCHEMA:
        raise BundleError(f"expected schema {SCHEMA!r}, got {b.get('schema')!r}")
    for key in ("measure", "trials", "reference"):
        if key not in b:
            raise BundleError(f"bundle missing required key {key!r}")
    return b


def study_from_trial(trial: dict, measure: str) -> Study:
    """Build a Study from a trial dict. For RR/OR use the raw 2x2 (tE/tN/cE/cN);
    otherwise fall back to a published effect + CI (logHR, SE-from-CI)."""
    label = trial.get("name") or trial.get("nct") or "?"
    tE, tN = trial.get("tE"), trial.get("tN")
    cE, cN = trial.get("cE"), trial.get("cN")
    if measure in ("RR", "OR") and None not in (tE, tN, cE, cN):
        return Study(label=label, ai=int(tE), n1=int(tN), ci=int(cE), n2=int(cN))
    if measure == "RD" and None not in (tE, tN, cE, cN) and tN > 0 and cN > 0:
        import math
        p1, p2 = tE / tN, cE / cN
        yi = p1 - p2
        vi = p1 * (1 - p1) / tN + p2 * (1 - p2) / cN
        if vi <= 0 or not math.isfinite(vi):
            raise BundleError(f"trial {label!r} has degenerate risk-difference variance")
        return Study(label=label, yi=yi, vi=vi)
    hr, lo, hi = trial.get("publishedHR"), trial.get("hrLCI"), trial.get("hrUCI")
    if None not in (hr, lo, hi) and hr > 0 and lo > 0 and hi > 0:
        import math
        yi = math.log(hr)
        se = (math.log(hi) - math.log(lo)) / (2 * 1.959964)
        return Study(label=label, yi=yi, vi=se * se)
    raise BundleError(f"trial {label!r} has neither a usable 2x2 nor a published effect+CI "
                      f"for measure {measure!r}")


def studies(bundle: dict, measure: str | None = None, extra: list | None = None,
            drop: str | None = None) -> list:
    """Studies for the bundle, optionally with one added (`extra`, list of trial
    dicts) or one removed (`drop`, matched on name/nct)."""
    measure = measure or bundle["measure"]
    trials = list(bundle["trials"])
    if extra:
        trials = trials + list(extra)
    out = []
    for t in trials:
        name = t.get("name") or t.get("nct")
        if drop and name and drop.lower() in str(name).lower():
            continue
        out.append(study_from_trial(t, measure))
    return out


def verify_protocol_hash(bundle: dict, bundle_dir: str) -> tuple:
    """Recompute sha256 of the bundled protocol file and compare to the manifest.
    Returns (ok, computed, expected). This is the content-addressed pre-registration
    check: change one character of the question and the hash no longer matches."""
    proto = bundle.get("protocol") or {}
    fname, expected = proto.get("file"), proto.get("sha256")
    if not fname or not expected:
        return (None, None, None)
    fpath = os.path.join(bundle_dir, fname)
    if not os.path.exists(fpath):
        return (False, None, expected)
    with open(fpath, "rb") as fh:
        computed = hashlib.sha256(fh.read()).hexdigest()
    return (computed == expected, computed, expected)
