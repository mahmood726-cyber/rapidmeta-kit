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


# --- HONESTY-BUG regression: no inherited DUPILUMAB_COPD base claims leak -----
# The base template is the validated DUPILUMAB_COPD build. The token swap only
# rewrites the drug/condition/slug tokens; the dupilumab-specific PROSE, the
# "RapidMeta Respiratory" brand, the frozen 2026-05-24 dates, the "landmark
# RCTs" quality claim, and the BOREAS/NOTUS benchmark comparators all survive
# unless clone.py explicitly resets them. These tests assert a new-topic build
# carries NONE of those base claims (models test_no_stale_provenance_leaks).

# Every string here is a verbatim dupilumab-base claim that MUST NOT survive a
# clone to an unrelated topic. Case-insensitive so a "Type-2"/"type-2" variant
# can't slip through.
_BANNED_BASE_CLAIMS = [
    "type-2 inflammation",
    "type 2 inflammation",
    "annual moderate-severe exacerbation",
    "rapidmeta respiratory",
    "landmark rcts",
    "dupilumab evidence",
    "il-4ralpha",          # the dupilumab mechanism in the Review Title row
    "boreas",              # hardcoded dupilumab benchmark comparators
    "notus",
]


def test_no_inherited_base_claims_leak(tmp_path):
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8").lower()
    leaked = [c for c in _BANNED_BASE_CLAIMS if c in html]
    assert not leaked, f"inherited DUPILUMAB_COPD base claim(s) leaked: {leaked}"
    # The frozen base build-date must not survive (P0-3).
    assert "2026-05-24" not in html
    # JSON-LD headline/name must come from the config title, not the base brand.
    assert '"headline":"rapidmeta respiratory' not in html
    assert '"name":"rapidmeta respiratory' not in html
    # The benchmark block was emptied (no fabricated comparators).
    assert "const published_meta_benchmarks = {};" in html


def test_jsonld_dates_are_build_date_not_frozen(tmp_path):
    # P0-3: datePublished/dateModified default to the build date, never the
    # inherited 2026-05-24. With no config 'date' they should be today's ISO.
    import datetime
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    assert f'"datePublished":"{today}"' in html
    assert f'"dateModified":"{today}"' in html


def test_config_date_overrides_build_date(tmp_path):
    cfg = json.loads((CONFIGS / "example_finerenone_ckd.json").read_text("utf-8"))
    cfg["date"] = "2026-01-15"
    cfg_path = tmp_path / "fin_date.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "fin.html"
    res = run_clone([str(cfg_path), "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    assert '"datePublished":"2026-01-15"' in html
    assert '"dateModified":"2026-01-15"' in html


def test_jsonld_is_valid_json(tmp_path):
    # The honesty resets stamp config values into the JSON-LD via json.dumps;
    # an em-dash / quote / backslash in the title must not break the block.
    import re as _re
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    m = _re.search(r'<script type="application/ld\+json">(.*?)</script>',
                   html, _re.S)
    assert m, "JSON-LD block missing"
    data = json.loads(m.group(1))            # raises if the resets broke JSON
    assert "Finerenone" in data["headline"]
    assert data["description"]               # non-empty topic-neutral default


def test_description_override_applied(tmp_path):
    cfg = json.loads((CONFIGS / "example_finerenone_ckd.json").read_text("utf-8"))
    cfg["description"] = "Custom honest synopsis of the finerenone review."
    cfg_path = tmp_path / "fin_desc.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "fin.html"
    res = run_clone([str(cfg_path), "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    assert "Custom honest synopsis of the finerenone review." in html


def test_missing_hero_with_leak_fails_closed(tmp_path):
    # P1-4: a config that omits hero_h2/nyt_headline AND whose token swap leaves
    # a topic-specific base claim in the hero/NYT fallback must fail closed (the
    # clone would otherwise display "...with Type-2 Inflammation" for a non-
    # dupilumab topic). drug/condition here do not contain the swapped tokens,
    # so the "Type-2 Inflammation" hero fallback survives -> die(2).
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(
        {"drug": "Finerenone", "slug": "fin_x", "condition": "CKD",
         "title": "Finerenone for CKD",
         "trials": [{"nct": "NCT02540993", "name": "FIDELIO"}]}),
        encoding="utf-8")
    out = tmp_path / "o.html"
    res = run_clone([str(bad), "--out", str(out)])
    assert res.returncode == 2
    assert "hero_h2" in res.stderr or "nyt_headline" in res.stderr


def test_specialty_drops_respiratory_by_default(tmp_path):
    # P0-2: without a config 'specialty', the brand is just the title — the
    # hardcoded "Respiratory" specialty word must not appear.
    out = tmp_path / "fin.html"
    res = run_clone([str(CONFIGS / "example_finerenone_ckd.json"),
                     "--out", str(out)])
    assert res.returncode == 0, res.stderr
    html = out.read_text(encoding="utf-8")
    assert "Respiratory" not in html
