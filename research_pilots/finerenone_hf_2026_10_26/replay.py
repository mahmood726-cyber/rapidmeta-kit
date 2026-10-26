"""Safeguarded *numerical* reconstruction of one published finerenone forest plot.

No inference of clinical combinability or independent scientific certification.
This script deliberately does not provide a general-purpose way to pool
incompatible effects as a valid clinical endpoint.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

REFERENCE = Path(__file__).with_name("reference.json")


class IncompatibleEstimandsError(ValueError):
    """The records cannot legitimately form one clinical effect estimate."""


def load_reference(path: Path = REFERENCE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assert_compatible(trials: list[dict]) -> None:
    """Fail closed on different populations, endpoints, effects or count units."""
    if not trials:
        raise ValueError("No trials supplied")
    fields = ("population_id", "endpoint_id", "effect_type", "event_count_unit")
    for field in fields:
        values = {trial[field] for trial in trials}
        if len(values) != 1:
            raise IncompatibleEstimandsError(f"INCOMPATIBLE_ESTIMANDS: {field}: {sorted(values)}")
    for trial in trials:
        if trial["event_count_unit"] != "PATIENTS_WITH_FIRST_EVENT":
            raise IncompatibleEstimandsError("INCOMPATIBLE_ESTIMANDS: recurrent counts cannot be 2x2 person-events")


def _inverse_variance(trials: list[dict]) -> dict:
    """DL random-effects on log(estimates) from *rounded* published 95% CIs.

    Returns a computational check, not an independent method-matched R oracle.
    """
    if not trials:
        raise ValueError("No trials supplied")
    effects = []
    variances = []
    for trial in trials:
        val, lo, hi = (float(trial[k]) for k in ("effect", "ci_lower", "ci_upper"))
        if not all(math.isfinite(v) for v in (val, lo, hi)) or not 0 < lo < val < hi:
            raise ValueError(f"Invalid estimate or CI for {trial['trial_id']}")
        if trial["effect_type"] not in {"HAZARD_RATIO", "EVENT_RATE_RATIO"}:
            raise ValueError("Unsupported effect type")
        # Published 95% intervals, not event-count-based binary risks.
        effects.append(math.log(val))
        variances.append(((math.log(hi) - math.log(lo)) / (2 * 1.96)) ** 2)
    weights = [1 / v for v in variances]
    total_weight = sum(weights)
    common_log = sum(w * e for w, e in zip(weights, effects)) / total_weight
    q_statistic = sum(w * (e - common_log) ** 2 for w, e in zip(weights, effects))
    c = total_weight - sum(w * w for w in weights) / total_weight
    # k=1: no heterogeneity degrees of freedom or random-effect estimate.
    tau_squared = max(0.0, (q_statistic - (len(trials) - 1)) / c) if len(trials) > 1 and c > 0 else 0.0
    random_weights = [1 / (v + tau_squared) for v in variances]
    log_pooled = sum(w * e for w, e in zip(random_weights, effects)) / sum(random_weights)
    se_pooled = (1 / sum(random_weights)) ** .5
    return {
        "k": len(trials),
        "estimate": math.exp(log_pooled),
        "ci_lower": math.exp(log_pooled - 1.96 * se_pooled),
        "ci_upper": math.exp(log_pooled + 1.96 * se_pooled),
        "q_statistic": q_statistic,
        "tau_squared_DL_from_rounded_CI": tau_squared,
        "source_interval_precision": "ROUNDED_PUBLISHED_CI",
        "external_R_parity": "NOT_RUN",
    }


def clinical_pool(trials: list[dict]) -> dict:
    """Only count genuinely comparable, first-event HR trials."""
    assert_compatible(trials)
    if trials[0]["effect_type"] != "HAZARD_RATIO":
        raise IncompatibleEstimandsError("Clinical comparison limited to first-event hazard ratios")
    result = _inverse_variance(trials)
    result["status"] = "HOMOGENEOUS_ESTIMAND_NUMERICAL_SENSITIVITY_NOT_CLINICALLY_VALIDATED"
    return result


def historical_paper_reconstruction(reference: dict) -> dict:
    """Deliberately named exception: reconstruct *arithmetic*, not a clinical pool."""
    trials = reference["trials"]
    try:
        assert_compatible(trials)
    except IncompatibleEstimandsError:
        pass
    else:
        raise ValueError("Historical test no longer contains mismatched estimands; review scope changed")
    result = _inverse_variance(trials)
    result["status"] = "EXPLORATORY_MIXED_ESTIMAND_NUMERICAL_RECONSTRUCTION_ONLY"
    result["clinical_pooling_permitted"] = False
    result["reported_paper_method"] = reference["target_review"]["reported_analysis_method"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-reconstruction", action="store_true", help="Explicitly reconstruct the published, scientifically heterogeneous numerical combination")
    parser.add_argument("--dkd-only", action="store_true", help="Two-trial first-event HR sensitivity, not clinical certification")
    args = parser.parse_args()
    ref = load_reference()
    if args.paper_reconstruction and args.dkd_only:
        parser.error("Choose only one analysis")
    if args.paper_reconstruction:
        result = historical_paper_reconstruction(ref)
    elif args.dkd_only:
        result = clinical_pool([t for t in ref["trials"] if t["population_id"] == "T2D_CKD"])
    else:
        # Intentional default: a mixed-estimand dataset is never pooled silently.
        assert_compatible(ref["trials"])
        result = clinical_pool(ref["trials"])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
