"""Fail-closed checks against published numbers plus separately supplied manual extraction.

PASS here is numerical/provenance fixture verification, not study eligibility,
clinical combinability, blinded adjudication, or version-pinned R parity.
"""

import copy
import importlib.util
from pathlib import Path

import pytest

PILOT = Path(__file__).resolve().parents[1] / "research_pilots" / "finerenone_hf_2026_10_26"
spec = importlib.util.spec_from_file_location("finerenone_hf_replay", PILOT / "replay.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def reference():
    return module.load_reference(PILOT / "reference.json")


def test_workbook_is_tracked_by_hash_but_not_republished():
    doc = reference()["human_reference"]
    assert doc["workbook_sha256"] == "5cbc23255023bf293b0b9e5a604b026f7fa19464a4a2595e555d89ffb4538fc7"
    assert doc["workbook_distribution"].startswith("NOT_PUBLISHED")
    assert not (PILOT / doc["workbook_filename"]).exists()


def test_published_primary_source_anchors_and_event_count_units():
    trial = {t["trial_id"]: t for t in reference()["trials"]}
    names = ["FIDELIO-DKD", "FIGARO-DKD", "FINEARTS-HF"]
    assert set(trial) == set(names)
    assert [(trial[n]["finerenone_events"], trial[n]["placebo_events"]) for n in names] == [(139, 162), (117, 163), (842, 1024)]
    assert [trial[n]["effect"] for n in names] == [0.86, 0.71, 0.82]
    assert trial["FINEARTS-HF"]["event_count_unit"] == "TOTAL_FIRST_AND_RECURRENT_EVENTS_NOT_NUMBER_OF_PATIENTS"
    assert trial["FINEARTS-HF"]["effect_type"] == "EVENT_RATE_RATIO"
    assert all(t["primary_source"].startswith("https://doi.org/10.") for t in trial.values())


def test_ordinary_mixed_endpoint_pool_fails_closed():
    with pytest.raises(module.IncompatibleEstimandsError, match="INCOMPATIBLE_ESTIMANDS"):
        module.clinical_pool(reference()["trials"])


def test_count_unit_can_never_be_silently_changed_into_binary_events():
    trial = copy.deepcopy(reference()["trials"])
    for t in trial:
        t["population_id"] = "T2D_CKD"
        t["endpoint_id"] = "FIRST_HF_HOSPITALISATION"
        t["effect_type"] = "HAZARD_RATIO"
    with pytest.raises(module.IncompatibleEstimandsError, match="INCOMPATIBLE_ESTIMANDS"):
        module.clinical_pool(trial)


def test_published_paper_says_random_effects_not_fixed_effects():
    paper = reference()["target_review"]
    assert "random-effects" in paper["reported_analysis_method"]
    assert paper["reported_tau_squared"] == 0
    assert paper["reported_i_squared_percent"] == 0


def test_explicit_historical_numerical_reconstruction_matches_published_rounding():
    result = module.historical_paper_reconstruction(reference())
    assert result["k"] == 3
    assert result["clinical_pooling_permitted"] is False
    assert result["status"] == "EXPLORATORY_MIXED_ESTIMAND_NUMERICAL_RECONSTRUCTION_ONLY"
    assert result["external_R_parity"] == "NOT_RUN"
    assert result["estimate"] == pytest.approx(.80446175016, abs=1e-9)
    assert result["ci_lower"] == pytest.approx(.72279056203, abs=1e-9)
    assert result["ci_upper"] == pytest.approx(.89536131414, abs=1e-9)
    assert result["tau_squared_DL_from_rounded_CI"] == 0


def test_dkd_first_event_random_effects_sensitivity_only():
    trials = [t for t in reference()["trials"] if t["population_id"] == "T2D_CKD"]
    result = module.clinical_pool(trials)
    assert result["k"] == 2
    assert result["status"] == "HOMOGENEOUS_ESTIMAND_NUMERICAL_SENSITIVITY_NOT_CLINICALLY_VALIDATED"
    assert result["estimate"] == pytest.approx(.7828815085, abs=1e-9)
    assert result["ci_lower"] == pytest.approx(.6488382999, abs=1e-9)
    assert result["ci_upper"] == pytest.approx(.9446166425, abs=1e-9)


def test_invalid_confidence_interval_never_replays():
    trials = copy.deepcopy(reference()["trials"])
    trials[0]["ci_lower"] = trials[0]["effect"]
    with pytest.raises(ValueError, match="Invalid estimate"):
        module._inverse_variance(trials)


def test_source_change_breaks_anchored_published_numerical_result():
    ref = copy.deepcopy(reference())
    ref["trials"][2]["effect"] = .90
    assert abs(module.historical_paper_reconstruction(ref)["estimate"] - .80446175016) > 0.02


def test_scientific_independence_gates_not_misclassified_as_pass():
    g = reference()["evidence_gates"]
    for gate in ("prospective_exhaustive_search", "blinded_independent_duplicate_adjudication", "method_matched_version_pinned_R_oracle", "complete_end_to_end_meta_harness_replay"):
        assert g[gate] == "NOT_RUN"
    assert g["clinically_combinable_primary_endpoint"] == "BLOCKED"
