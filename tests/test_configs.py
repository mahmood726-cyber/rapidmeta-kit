"""The bundled example configs must satisfy schema.json. We do a stdlib-only
structural check (always runs) plus a full jsonschema validation (skipped if
jsonschema isn't installed, so the default suite stays dependency-free).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((REPO_ROOT / "schema.json").read_text(encoding="utf-8"))
EXAMPLES = sorted((REPO_ROOT / "configs").glob("*.json"))


def test_examples_exist():
    names = {p.name for p in EXAMPLES}
    assert "example_finerenone_ckd.json" in names
    assert "example_minimal.json" in names


@pytest.mark.parametrize("cfg_path", EXAMPLES, ids=lambda p: p.name)
def test_example_has_required_fields(cfg_path):
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for field in SCHEMA["required"]:
        assert field in cfg, f"{cfg_path.name} missing required '{field}'"
    assert re.fullmatch(r"[a-z0-9_]+", cfg["slug"]), cfg["slug"]
    assert isinstance(cfg["trials"], list) and len(cfg["trials"]) >= 1
    for t in cfg["trials"]:
        assert "nct" in t and "name" in t


@pytest.mark.parametrize("cfg_path", EXAMPLES, ids=lambda p: p.name)
def test_example_validates_against_schema(cfg_path):
    jsonschema = pytest.importorskip("jsonschema")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    jsonschema.validate(cfg, SCHEMA)
