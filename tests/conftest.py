"""Shared fixtures + a stdout-safe loader for clone.py.

clone.py reassigns ``sys.stdout`` to a UTF-8 ``TextIOWrapper`` at import time
(so the CLI prints unicode cleanly on Windows cp1252 consoles). Under pytest's
output capture that reassignment can corrupt the capture file. We side-step it:
before importing we point ``sys.stdout`` at a ``StringIO`` (which has no
``.buffer`` attribute), so clone.py's ``if hasattr(sys.stdout, "buffer")``
guard is False and the reassignment is skipped. The real stdout is restored
immediately after import.
"""
from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CLONE_PATH = REPO_ROOT / "clone.py"


def _load_clone():
    saved = sys.stdout
    sys.stdout = io.StringIO()  # no .buffer -> clone.py skips its stdout rewrap
    try:
        spec = importlib.util.spec_from_file_location("clone", CLONE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.stdout = saved


clone = _load_clone()


@pytest.fixture(scope="session")
def clone_mod():
    """The imported clone.py module (pure functions)."""
    return clone


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def minimal_cfg() -> dict:
    return {
        "drug": "Drug X",
        "slug": "drugx_conditiony",
        "condition": "Condition Y",
        "title": "Drug X for Condition Y",
        "trials": [
            {"nct": "NCT00000001", "name": "TRIAL-1", "year": 2021,
             "tE": 40, "tN": 400, "cE": 60, "cN": 400},
            {"nct": "NCT00000002", "name": "TRIAL-2", "year": 2022,
             "tE": 35, "tN": 380, "cE": 55, "cN": 390},
        ],
    }
