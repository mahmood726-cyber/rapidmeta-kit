"""Synthetic regression tests for the private XLSX-to-public provenance bridge.

No unpublished human workbook content is checked into this repository.
"""

import hashlib
import importlib.util
import json
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import pytest

PILOT = Path(__file__).resolve().parents[1] / "research_pilots" / "finerenone_hf_2026_10_26"
spec = importlib.util.spec_from_file_location("finerenone_bridge", PILOT / "verify_human_workbook.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

TRIALS = [
    {"trial_id": "FIDELIO-DKD", "finerenone_n": 2833, "finerenone_events": 139,
     "placebo_n": 2841, "placebo_events": 162, "effect_type": "HAZARD_RATIO",
     "effect": .86, "ci_lower": .68, "ci_upper": 1.08},
    {"trial_id": "FIGARO-DKD", "finerenone_n": 3686, "finerenone_events": 117,
     "placebo_n": 3666, "placebo_events": 163, "effect_type": "HAZARD_RATIO",
     "effect": .71, "ci_lower": .56, "ci_upper": .90},
    {"trial_id": "FINEARTS-HF", "finerenone_n": 3003, "finerenone_events": 842,
     "placebo_n": 2998, "placebo_events": 1024, "effect_type": "EVENT_RATE_RATIO",
     "effect": .82, "ci_lower": .71, "ci_upper": .94},
]
SHEETS = ["README", "Analysis_Dataset", "Extraction_Summary", "Detailed_Extraction",
          "Endpoint_Definitions", "MetaAnalysis_Extraction", "Discrepancy_Log"]
XNS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def fixture_cells():
    headers = ["trial_id", "trial_name", "year", "n_finerenone", "events_finerenone",
               "n_placebo", "events_placebo", "effect_type", "effect_estimate", "ci_lower", "ci_upper"]
    data = {f"{letter}4": name for letter, name in zip("ABCDEFGHIJK", headers)}
    for row, trial, year in zip((5, 6, 7), TRIALS, (2020, 2021, 2024)):
        for col, value in dict(A=trial["trial_id"].split("-")[0], B=trial["trial_id"], C=year,
                               D=trial["finerenone_n"], E=trial["finerenone_events"],
                               F=trial["placebo_n"], G=trial["placebo_events"],
                               H=("RR" if row == 7 else "HR"), I=trial["effect"],
                               J=trial["ci_lower"], K=trial["ci_upper"],
                               L="Total (first+recurrent) HF events" if row == 7 else "First HF hospitalisation").items():
            data[f"{col}{row}"] = value
    return data


def make_synthetic_xlsx(path, aggregate=None, details=None):
    if aggregate is None:
        aggregate = fixture_cells()
    if details is None:
        details = {"F10": "Needs CEC appendix check", "F15": "Needs exact criteria from appendix"}
    workbook = (f'<workbook xmlns="{XNS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                + '<sheets>' + ''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(SHEETS, start=1))
                + '</sheets></workbook>')
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, 8))
            + '</Relationships>')

    def xml_for(cells):
        from collections import defaultdict
        rows = defaultdict(list)
        for coord, value in cells.items():
            index = int(''.join(ch for ch in coord if ch.isdigit()))
            if isinstance(value, str):
                datum = f'<c r="{coord}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
            else:
                datum = f'<c r="{coord}"><v>{value}</v></c>'
            rows[index].append(datum)
        return f'<worksheet xmlns="{XNS}"><sheetData>' + ''.join(
            f'<row r="{i}">{"".join(rows[i])}</row>' for i in sorted(rows)) + '</sheetData></worksheet>'

    with ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        for index, name in enumerate(SHEETS, start=1):
            z.writestr(f"xl/worksheets/sheet{index}.xml", xml_for(
                aggregate if name == "Analysis_Dataset" else details if name == "Detailed_Extraction" else {}))


def write_reference(source_path, target_path, *, correct_hash=True):
    target_path.write_text(json.dumps({"human_reference": {"workbook_sha256": (
        hashlib.sha256(source_path.read_bytes()).hexdigest() if correct_hash else "0" * 64)},
        "trials": TRIALS}), encoding="utf-8")


def test_synthetic_unchanged_workbook_yields_30_cell_source_crosswalk(tmp_path):
    source, reference = tmp_path / "private.xlsx", tmp_path / "reference.json"
    make_synthetic_xlsx(source)
    write_reference(source, reference)
    result = bridge.verify(source, reference)
    assert result["checked_aggregate_cells"] == 30
    assert result["status"] == "PASS_PRIVATE_WORKBOOK_TO_PUBLIC_AGGREGATE_BRIDGE_ONLY"
    assert result["clinical_estimand_combinability"] == "BLOCKED"
    assert result["independent_blinded_duplicate_adjudication"] == "NOT_RUN"
    assert result["private_workbook_published"] is False


def test_mutated_workbook_hash_fails_without_silent_rebaseline(tmp_path):
    source, reference = tmp_path / "private.xlsx", tmp_path / "reference.json"
    make_synthetic_xlsx(source)
    write_reference(source, reference, correct_hash=False)
    with pytest.raises(bridge.SourceMismatch, match="Unpinned or modified workbook SHA-256"):
        bridge.verify(source, reference)


def test_wrong_event_total_fails_even_with_rewritten_hash(tmp_path):
    source, reference = tmp_path / "private.xlsx", tmp_path / "reference.json"
    cells = fixture_cells(); cells["E7"] = 843
    make_synthetic_xlsx(source, aggregate=cells)
    write_reference(source, reference)
    with pytest.raises(bridge.SourceMismatch, match="Analysis_Dataset!E7"):
        bridge.verify(source, reference)


def test_rr_cannot_silently_become_hazard_ratio(tmp_path):
    source, reference = tmp_path / "private.xlsx", tmp_path / "reference.json"
    cells = fixture_cells(); cells["H7"] = "HR"
    make_synthetic_xlsx(source, aggregate=cells)
    write_reference(source, reference)
    with pytest.raises(bridge.SourceMismatch, match="Analysis_Dataset!H7"):
        bridge.verify(source, reference)


def test_unverified_human_cec_caveat_cannot_be_overwritten(tmp_path):
    source, reference = tmp_path / "private.xlsx", tmp_path / "reference.json"
    make_synthetic_xlsx(source, details={"F10": "Confirmed", "F15": "Confirmed"})
    write_reference(source, reference)
    with pytest.raises(bridge.SourceMismatch, match="CEC verification caveats"):
        bridge.verify(source, reference)
