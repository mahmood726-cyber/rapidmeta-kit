"""Unit tests for the vendor-engine drift classifier in
scripts/check_engine_drift.py.

The classifier must distinguish a real CODE change from a comments/format-only
change (so a re-sync sweep can be scoped to files that actually drifted), and
must treat a changed STRING LITERAL as code (a displayed string is shipped
behaviour, e.g. a hardcoded path the review flagged).
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_engine_drift", ROOT / "scripts" / "check_engine_drift.py")
ced = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ced)


def test_normalize_ignores_comments_and_whitespace():
    a = "function f(x){\n  return x+1; // add one\n}"
    b = "/* doc */ function f(x){ return x+1; }   "
    assert ced._normalize_js(a) == ced._normalize_js(b)


def test_normalize_keeps_real_code_difference():
    a = "var k = Math.max(1, qStar);"
    b = "var k = Math.max(1, Q / df);"
    assert ced._normalize_js(a) != ced._normalize_js(b)


def test_normalize_treats_string_literal_change_as_code():
    a = 'help("see Cochrane Handbook v6.5");'
    b = 'help("see ~/.claude/rules/advanced-stats.md");'
    assert ced._normalize_js(a) != ced._normalize_js(b)


def test_normalize_does_not_eat_url_in_string():
    # '//' inside an http(s):// scheme must survive normalization.
    a = 'var u = "https://example.com/x";'
    assert "https://example.com/x" in ced._normalize_js(a)


def test_vendor_audit_classifies(tmp_path):
    # canonical comes from the real kit; point target at a temp dir seeded with
    # one MATCH, one comment-only, one CODE-DRIFT, leaving the rest MISSING.
    canon = Path(ced.CANON_VENDOR)
    names = sorted(p.name for p in canon.glob("*.js"))
    assert len(names) >= 3, "expected several canonical vendor engines"
    target = tmp_path / "vendor"
    target.mkdir()
    match_f, cmt_f, code_f = names[0], names[1], names[2]

    src0 = (canon / match_f).read_text(encoding="utf-8", errors="replace")
    (target / match_f).write_text(src0, encoding="utf-8")                      # MATCH

    src1 = (canon / cmt_f).read_text(encoding="utf-8", errors="replace")
    (target / cmt_f).write_text("/* re-synced */\n" + src1, encoding="utf-8")  # comment-only

    src2 = (canon / code_f).read_text(encoding="utf-8", errors="replace")
    (target / code_f).write_text(src2 + "\nvar __DRIFT__ = 123;\n",
                                 encoding="utf-8")                              # CODE-DRIFT

    rows, code_drift = ced.vendor_audit(str(target))
    status = {name: st for name, st, _ in rows}
    assert status[match_f] == "MATCH"
    assert status[cmt_f] == "comment-only"
    assert status[code_f] == "CODE-DRIFT"
    assert code_drift == 1
    # everything else is reported missing (and does not raise)
    assert any(st == "MISSING" for st in status.values())
