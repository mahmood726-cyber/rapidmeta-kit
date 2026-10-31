"""Transport-only regression for the exact native-metafor TSV input path.

These tests mock process execution. They check lossless count serialization
and DO NOT claim that R or metafor ran; actual external parity is tested in
metafor-tests/test_metafor_oracle.py on the separate native-R CI job.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
ORACLE_MODULE = ROOT / "metafor-tests" / "test_metafor_oracle.py"


def load_oracle_transport():
    # Import the real test helper; importing does not execute R.
    spec = importlib.util.spec_from_file_location(
        "_rapidmeta_metafor_transport_for_tests", ORACLE_MODULE
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("measure,method", [("RR", "PM"), ("OR", "DL")])
def test_metafor_transport_preserves_raw_fractional_and_unsafe_counts(measure, method):
    module = load_oracle_transport()
    raw_rows = (
        (10.5, 100, 20, 100),
        (10, 100.5, 20, 100),
        (9007199254740992, 9007199254740994, 20, 100),
    )
    expected = (
        "tE\ttN\tcE\tcN\n"
        "10.5\t100\t20\t100\n"
        "10\t100.5\t20\t100\n"
        "9007199254740992\t9007199254740994\t20\t100\n"
    )
    with patch.object(module.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as mocked:
        module.invoke_metafor(raw_rows, measure, method)
    args, kwargs = mocked.call_args
    assert args[0][-2:] == [measure, method]
    assert kwargs["input"] == expected


def test_metafor_transport_explicit_correction_mode_preserves_counts():
    module = load_oracle_transport()
    with patch.object(module.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as mocked:
        module.invoke_metafor(((0, 100, 8, 100), (8, 100, 16, 100)), "RR", "PM", matched_cc05=True)
    args, kwargs = mocked.call_args
    assert args[0][-3:] == ["RR", "PM", "CC05"]
    assert kwargs["input"].splitlines()[1:] == ["0\t100\t8\t100", "8\t100\t16\t100"]
