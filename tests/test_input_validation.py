"""Fail-closed validation: impossible 2x2 cells / inverted CIs must abort the
build (exit 2), not produce a green dashboard."""
import pytest

import clone


def _ok(trial):
    clone._validate_trial_values(0, {"nct": "NCT00000000", "name": "X", **trial})


def _blocked(trial):
    with pytest.raises(SystemExit) as e:
        _ok(trial)
    assert e.value.code == 2


def test_events_exceed_arm_size_blocked():
    _blocked({"tE": 50, "tN": 10})
    _blocked({"cE": 30, "cN": 20})


def test_negative_counts_blocked():
    _blocked({"tN": -5})
    _blocked({"tE": -1, "tN": 100})


def test_inverted_ci_blocked():
    _blocked({"hrLCI": 1.2, "hrUCI": 0.8})


def test_point_outside_ci_blocked():
    _blocked({"publishedHR": 1.5, "hrLCI": 0.7, "hrUCI": 0.9})


def test_nonpositive_ratio_blocked():
    _blocked({"publishedHR": 0})
    _blocked({"hrLCI": -0.1, "hrUCI": 0.9})


def test_valid_trial_passes():
    _ok({"tE": 5, "tN": 100, "cE": 12, "cN": 100,
         "publishedHR": 0.8, "hrLCI": 0.7, "hrUCI": 0.92})


def test_missing_values_pass():
    # absent numeric fields are allowed (not all configs carry 2x2 + HR)
    _ok({})


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
