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
