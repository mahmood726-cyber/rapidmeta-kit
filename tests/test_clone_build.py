"""End-to-end build tests: run clone.py as a subprocess (its real CLI contract)
and assert on the generated dashboard. Subprocess invocation also keeps the
module-level stdout rewrap out of the pytest process.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIGS = REPO_ROOT / "configs"


def run_clone(args, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, "clone.py", *args],
        cwd=cwd, capture_output=True, text=True,
    )


@pytest.mark.parametrize("cfg_name", ["example_finerenone_ckd.json",
                                      "example_minimal.json"])
def test_bundled_examples_build(cfg_name, tmp_path):
    out = tmp_path / "dash.html"
    res = run_clone([str(CONFIGS / cfg_name), "--out", str(out)])
    assert res.returncode == 0, res.stderr
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert len(html) > 500_000          # the full ~1 MB engine is bundled
    # Assets copied next to the output so it runs offline.
    assert (out.parent / "assets" / "plotly.min.js").exists()


def test_finerenone_tokens_stamped(tmp_path):
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    assert "<title>" in html and "Finerenone" in html
    # localStorage namespace was rebound to the new slug.
    assert "rapid_meta_finerenone_ckd" in html
    assert "rapid_meta_dupilumab_copd" not in html
    # The trial NCTs from the config are wired into the include set.
    assert "NCT02540993" in html and "NCT02545049" in html


def test_no_stale_provenance_leaks(tmp_path):
    # Generated dashboards must not inherit the base template's previous-clone
    # JSON-LD provenance: the rapidmeta-finerenone canonical URL, the leftover
    # DUPILUMAB_COPD filename stem, or the empty ORCID identifier.
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    # The owner-qualified stale-repo refs must be gone. (A bare
    # "rapidmeta-finerenone" substring can legitimately arise as
    # "rapidmeta-" + a slug that starts with "finerenone", so we assert the
    # owner-qualified URL/repo forms, not the bare substring.)
    assert "github.io/rapidmeta-finerenone" not in html
    assert "mahmood726-cyber/rapidmeta-finerenone" not in html
    assert "DUPILUMAB_COPD" not in html
    assert '"identifier":"https://orcid.org/"' not in html   # empty ORCID dropped
    # Publisher now points at the kit, not the old topic repo.
    assert "rapidmeta-kit" in html


def test_provenance_overrides_applied(tmp_path):
    cfg = json.loads((CONFIGS / "example_finerenone_ckd.json").read_text("utf-8"))
    cfg["canonical_url"] = "https://example.org/reviews/fin.html"
    cfg["orcid"] = "0000-0002-1825-0097"
    cfg_path = tmp_path / "fin_meta.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "fin.html"
    res = run_clone([str(cfg_path), "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    assert '"url":"https://example.org/reviews/fin.html"' in html
    assert "https://orcid.org/0000-0002-1825-0097" in html


def test_no_unpopulated_placeholders(tmp_path):
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    # NB: not {{ / }} — the engine legitimately uses ${{...}[x]} template
    # literals; only true unpopulated-token markers are checked here.
    for token in ("REPLACE_ME", "__PLACEHOLDER__", "{{REPLACE", "TODO_FIXME"):
        assert token not in html, f"unpopulated placeholder {token!r} in output"


def test_missing_drug_exits_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"slug": "x", "condition": "y", "title": "t",
         "trials": [{"nct": "N", "name": "M"}]}), encoding="utf-8")
    res = run_clone([str(bad), "--out", str(tmp_path / "o.html")])
    assert res.returncode == 2
    assert "drug" in res.stderr.lower()


def test_bad_slug_exits_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"drug": "D", "slug": "Bad Slug!", "condition": "y", "title": "t",
         "trials": [{"nct": "N", "name": "M"}]}), encoding="utf-8")
    res = run_clone([str(bad), "--out", str(tmp_path / "o.html")])
    assert res.returncode == 2
    assert "slug" in res.stderr.lower()


def test_empty_trials_exits_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"drug": "D", "slug": "ok", "condition": "y", "title": "t",
         "trials": []}), encoding="utf-8")
    res = run_clone([str(bad), "--out", str(tmp_path / "o.html")])
    assert res.returncode == 2
    assert "trials" in res.stderr.lower()


def test_malformed_json_exits_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    res = run_clone([str(bad), "--out", str(tmp_path / "o.html")])
    assert res.returncode == 2
    assert "json" in res.stderr.lower()


def test_missing_config_file_exits_2(tmp_path):
    res = run_clone([str(tmp_path / "does_not_exist.json"),
                     "--out", str(tmp_path / "o.html")])
    assert res.returncode == 2


def test_apostrophe_condition_rejected(tmp_path):
    # Regression: a condition with an apostrophe ("Crohn's disease") is stamped
    # verbatim into single-quoted JS string literals and silently breaks the
    # dashboard. clone.py must fail closed (exit 2) and write nothing.
    out = tmp_path / "o.html"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"drug": "Upadacitinib", "slug": "upa_crohn",
         "condition": "Crohn's disease", "title": "t",
         "trials": [{"nct": "NCT1", "name": "M"}]}), encoding="utf-8")
    res = run_clone([str(bad), "--out", str(out)])
    assert res.returncode == 2
    assert "condition" in res.stderr.lower()
    assert "apostrophe" in res.stderr.lower()
    assert not out.exists()          # nothing written on a rejected config


def test_apostrophe_drug_rejected(tmp_path):
    out = tmp_path / "o.html"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"drug": "Drug's", "slug": "x", "condition": "Y", "title": "t",
         "trials": [{"nct": "NCT1", "name": "M"}]}), encoding="utf-8")
    res = run_clone([str(bad), "--out", str(out)])
    assert res.returncode == 2
    assert "drug" in res.stderr.lower()
    assert not out.exists()
