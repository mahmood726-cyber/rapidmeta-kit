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


# --- registry-ID handling: never emit a false clinicaltrials.gov link ---------

def test_registry_url_recognizes_known_formats():
    assert clone._registry_url("NCT02713451") == "https://clinicaltrials.gov/study/NCT02713451"
    assert clone._registry_url("ISRCTN12345678") == "https://www.isrctn.com/ISRCTN12345678"
    assert clone._registry_url("ACTRN12615000957594").startswith("https://www.anzctr.org.au/")
    assert clone._registry_url("NOT_A_TRIAL_ID") is None
    assert clone._registry_url("NCT123") is None  # malformed NCT


def test_is_nct_only_true_for_real_nct():
    assert clone._is_nct("NCT02713451")
    assert not clone._is_nct("ACTRN12615000957594")
    assert not clone._is_nct("NOT_A_TRIAL_ID")


def _build_config(trials):
    return {"drug": "X", "drug_lower": "x", "slug": "x_test", "condition": "c",
            "comparator": "P", "title": "t", "hero_h2": "h", "nyt_headline": "n",
            "pico": {"pop": "p", "int": "i", "comp": "c", "out": "o", "subgroup": "s"},
            "trials": trials}


def _run_clone(cfg, tmp_path):
    import json, subprocess, sys, os
    cfgp = tmp_path / "c.json"
    cfgp.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "o.html"
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(clone.__file__), "clone.py"),
                        str(cfgp), "--out", str(out)], capture_output=True, text=True,
                       cwd=os.path.dirname(clone.__file__))
    return r, out


def test_invalid_trial_id_fails_closed(tmp_path):
    r, out = _run_clone(_build_config([{"nct": "NOT_A_TRIAL_ID", "name": "Bad"}]), tmp_path)
    assert r.returncode == 2, r.stderr
    assert "not a recognized registry ID" in (r.stderr + r.stdout)
    assert not out.exists()


def test_invalid_id_with_explicit_source_url_builds(tmp_path):
    r, out = _run_clone(_build_config([
        {"nct": "EU-CTR-2020-001", "name": "Ok", "sourceUrl": "https://www.clinicaltrialsregister.eu/",
         "tE": 5, "tN": 100, "cE": 10, "cN": 100}]), tmp_path)
    assert r.returncode == 0, r.stderr


def test_cloned_dashboard_plotly_is_resolvable_cdn(tmp_path):
    # A clone must reference Plotly from the CDN (where the SRI hash matches),
    # NOT a bare local `assets/plotly.min.js` — clones ship standalone (single
    # file, no co-located assets dir), so a local ref 404s and the SRI mismatches
    # the CDN hash, silently blocking every forest plot.
    r, out = _run_clone(_build_config([{"nct": "NCT01234567", "name": "M",
                        "tE": 5, "tN": 100, "cE": 10, "cN": 100}]), tmp_path)
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert 'src="https://cdn.plot.ly/plotly-2.27.0.min.js"' in html, "Plotly not loaded from CDN"
    assert 'src="assets/plotly.min.js"' not in html, "bare local plotly ref would 404 standalone"
    # the declared SRI must be the CDN file's hash
    assert "sha384-Hl48Kq2HifOWdXEjMsKo6qxqvRLTYqIGbvlENBmkHAxZKIGCXv43H6W1jA671RzC" in html


def test_condition_slash_fails_closed(tmp_path):
    # `condition` is stamped into a JS regex literal; a '/' would close it.
    r, out = _run_clone(dict(_build_config([{"nct": "NCT01234567", "name": "M",
                        "tE": 5, "tN": 100, "cE": 10, "cN": 100}]),
                        condition="general anaesthesia / sedation"), tmp_path)
    assert r.returncode == 2, r.stderr
    assert "forward slash" in (r.stderr + r.stdout)
    assert not out.exists()


def test_drug_slash_still_allowed(tmp_path):
    # '/' is only unsafe in `condition`; drug names like "Early / accelerated RRT"
    # are stamped into a safe context and must still build.
    cfg = dict(_build_config([{"nct": "NCT01234567", "name": "M", "tE": 5, "tN": 100,
                               "cE": 10, "cN": 100}]), drug="Early / accelerated RRT")
    r, out = _run_clone(cfg, tmp_path)
    assert r.returncode == 0, r.stderr


def test_non_nct_id_emits_no_ctgov_link(tmp_path):
    r, out = _run_clone(_build_config([
        {"nct": "ACTRN12615000957594", "name": "ICU-ROX", "tE": 5, "tN": 100, "cE": 10, "cN": 100}]), tmp_path)
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    # the ANZCTR trial must NOT carry a fabricated clinicaltrials.gov/study/ACTRN... link
    assert "clinicaltrials.gov/study/ACTRN12615000957594" not in html
    assert "anzctr.org.au" in html


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
