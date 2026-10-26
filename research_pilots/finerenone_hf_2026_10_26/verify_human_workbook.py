"""Validate a locally held human extraction workbook against public trial fixtures.

This script never uploads the workbook. It fails closed on SHA, missing cells,
changed counts, effect measures or malformed workbook XML. It does not certify
any Clinical Endpoint Committee definitions or prospectively blinded review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from posixpath import normpath
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PN = "{http://schemas.openxmlformats.org/package/2006/relationships}"
SOURCE_DIR = Path(__file__).resolve().parent
MAX_WORKBOOK_BYTES = 20_000_000
MAX_UNPACKED_XML_BYTES = 10_000_000


class SourceMismatch(ValueError):
    """Human-reference workbook differs from the pinned scientific source."""


def _read_xml(archive: ZipFile, name: str) -> ET.Element:
    try:
        info = archive.getinfo(name)
        if info.file_size > MAX_UNPACKED_XML_BYTES:
            raise SourceMismatch(f"Oversized XLSX XML member: {name}")
        return ET.fromstring(archive.read(info))
    except (KeyError, ET.ParseError, BadZipFile) as exc:
        raise SourceMismatch(f"Cannot read XLSX XML member {name}: {exc}") from exc


def sheet_cells(archive: ZipFile, sheet_name: str) -> tuple[dict[str, object], list[str]]:
    """Read only the named worksheet's literal cells using stdlib XLSX XML.

    No external links, macros, formulas, or recalculation are evaluated.
    """
    workbook = _read_xml(archive, "xl/workbook.xml")
    relationships = _read_xml(archive, "xl/_rels/workbook.xml.rels")
    sheets = workbook.find(NS + "sheets")
    if sheets is None:
        raise SourceMismatch("XLSX workbook lacks sheets")
    names = [s.get("name", "") for s in sheets.findall(NS + "sheet")]
    sheet = next((s for s in sheets.findall(NS + "sheet") if s.get("name") == sheet_name), None)
    if sheet is None:
        raise SourceMismatch(f"Missing worksheet {sheet_name}")
    rid = sheet.get(RNS + "id")
    targets = {
        r.get("Id"): r.get("Target") for r in relationships.findall(PN + "Relationship")
        if r.get("Type", "").endswith("/worksheet")
    }
    target = targets.get(rid)
    if not target:
        raise SourceMismatch(f"No worksheet relationship for {sheet_name}")
    path = normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
    if not path.startswith("xl/worksheets/"):
        raise SourceMismatch(f"Unsafe worksheet relationship for {sheet_name}")
    strings: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
        sst = _read_xml(archive, "xl/sharedStrings.xml")
        for si in sst.findall(NS + "si"):
            strings.append("".join(t.text or "" for t in si.iter(NS + "t")))
    data = _read_xml(archive, path)
    cells: dict[str, object] = {}
    for cell in data.iter(NS + "c"):
        loc = cell.get("r")
        if not loc:
            continue
        if cell.find(NS + "f") is not None:
            raise SourceMismatch(f"Formula source cell is not acceptable: {sheet_name}!{loc}")
        value = cell.find(NS + "v")
        if cell.get("t") == "inlineStr":
            content: object = "".join(t.text or "" for t in cell.iter(NS + "t"))
        elif value is None or value.text is None:
            continue
        elif cell.get("t") == "s":
            try:
                content = strings[int(value.text)]
            except (IndexError, ValueError) as exc:
                raise SourceMismatch(f"Invalid shared string: {sheet_name}!{loc}") from exc
        elif cell.get("t") in {"str", "e", "b"}:
            content = value.text
        else:
            try:
                content = float(value.text)
            except ValueError as exc:
                raise SourceMismatch(f"Invalid numeric source: {sheet_name}!{loc}") from exc
        cells[loc] = content
    return cells, names


def _same(actual: object, expected: object) -> bool:
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        return isinstance(actual, (float, int)) and math.isfinite(actual) and math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-12)
    return actual == expected


def verify(source_path: Path, reference_path: Path = SOURCE_DIR / "reference.json") -> dict:
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    source_path = Path(source_path)
    if not source_path.is_file() or source_path.stat().st_size > MAX_WORKBOOK_BYTES:
        raise SourceMismatch("Missing or excessively large workbook")
    actual_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    expected_hash = reference["human_reference"]["workbook_sha256"]
    if actual_hash != expected_hash:
        raise SourceMismatch(f"Unpinned or modified workbook SHA-256: {actual_hash}")

    try:
        with ZipFile(source_path) as z:
            cells, sheet_names = sheet_cells(z, "Analysis_Dataset")
            meta, _ = sheet_cells(z, "Detailed_Extraction")
    except BadZipFile as exc:
        raise SourceMismatch("Invalid workbook ZIP") from exc

    required_tabs = {
        "README", "Analysis_Dataset", "Extraction_Summary", "Detailed_Extraction",
        "Endpoint_Definitions", "MetaAnalysis_Extraction", "Discrepancy_Log"
    }
    if set(sheet_names) != required_tabs:
        raise SourceMismatch(f"Unexpected workbook tabs: {sheet_names}")
    expected_headers = ["trial_id", "trial_name", "year", "n_finerenone", "events_finerenone",
                        "n_placebo", "events_placebo", "effect_type", "effect_estimate", "ci_lower", "ci_upper"]
    for col, expected in zip("ABCDEFGHIJK", expected_headers):
        if not _same(cells.get(f"{col}4"), expected):
            raise SourceMismatch(f"Header mismatch: Analysis_Dataset!{col}4")
    if [t.get("trial_id") for t in reference.get("trials", [])] != ["FIDELIO-DKD", "FIGARO-DKD", "FINEARTS-HF"]:
        raise SourceMismatch("Unexpected trial identifiers, order or count")
    checks = 0
    crosswalk = []
    for row, trial in zip((5, 6, 7), reference["trials"]):
        workbook_effect_type = "RR" if trial["effect_type"] == "EVENT_RATE_RATIO" else "HR"
        trial_fields = {
            "A": trial["trial_id"].split("-")[0],
            "B": trial["trial_id"],
            "D": trial["finerenone_n"],
            "E": trial["finerenone_events"],
            "F": trial["placebo_n"],
            "G": trial["placebo_events"],
            "H": workbook_effect_type,
            "I": trial["effect"],
            "J": trial["ci_lower"],
            "K": trial["ci_upper"],
        }
        for col, wanted in trial_fields.items():
            coordinate = f"{col}{row}"
            if not _same(cells.get(coordinate), wanted):
                raise SourceMismatch(f"Source mismatch at Analysis_Dataset!{coordinate}: workbook={cells.get(coordinate)!r} expected={wanted!r}")
            checks += 1
        notes = str(cells.get(f"L{row}", "")).lower()
        if row == 7 and ("total" not in notes or "recurrent" not in notes):
            raise SourceMismatch("FINEARTS total-recurrent event note missing")
        crosswalk.append({"trial_id": trial["trial_id"], "workbook_range": f"Analysis_Dataset!A{row}:L{row}", "matched_fields": len(trial_fields), "status": "MATCH"})
    # Document uncertainty rather than silently upgrading source review status.
    if meta.get("F10") != "Needs CEC appendix check" or meta.get("F15") != "Needs exact criteria from appendix":
        raise SourceMismatch("Independent CEC verification caveats missing from workbook")
    return {
        "status": "PASS_PRIVATE_WORKBOOK_TO_PUBLIC_AGGREGATE_BRIDGE_ONLY",
        "workbook_sha256": actual_hash,
        "checked_aggregate_cells": checks,
        "trial_rows": crosswalk,
        "cec_appendix_status": "NOT_VERIFIED",
        "clinical_estimand_combinability": "BLOCKED",
        "prospective_discovery": "NOT_RUN",
        "independent_blinded_duplicate_adjudication": "NOT_RUN",
        "external_R_method_matched_replay": "NOT_RUN",
        "private_workbook_published": False,
        "note": "Only three trial aggregate rows were checked. Original workbook has seven tabs; README refers to an absent Next_Steps tab."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True, help="Local original XLSX; never uploaded")
    parser.add_argument("--reference", type=Path, default=SOURCE_DIR / "reference.json")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.workbook, args.reference), indent=2, sort_keys=True))
    except SourceMismatch as exc:
        parser.exit(2, f"SOURCE_CHECK_FAIL: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
