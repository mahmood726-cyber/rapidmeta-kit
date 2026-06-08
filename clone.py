#!/usr/bin/env python
"""Clone the FULL interactive RapidMeta dashboard for a new topic.

USAGE
    python clone.py configs/your_review.json
    python clone.py configs/your_review.json --out output/custom.html

You write a small JSON config (drug, condition, trials). This script
stamps it onto a complete ~1 MB RapidMeta template — the full workbench:
editable extraction, screening, risk-of-bias, live re-pooling, 28-panel
statistics tab, GRADE SoF, WebR R-validation, PRISMA flow. You do NOT
edit the template or this script; you only write configs.

It is deterministic — zero network/LLM calls — so a free-tier CLI key can
produce many dashboards without hitting rate limits.

The base template is template/base_dupilumab_copd.html (the validated
DUPILUMAB_COPD base, unminified so the replacements below work). All
'dupilumab' / 'COPD' / 'dupilumab_copd' tokens are swapped for your
topic, and the realData trial dictionary is replaced wholesale with your
trials.

Exit codes: 0 = built, 2 = bad config (message says what to fix).
"""
from __future__ import annotations
import argparse, html, json, re, sys, io
from pathlib import Path

# Guard the UTF-8 stdout shim: under pytest capture (no/odd .buffer) an
# unconditional reassignment breaks capture and closes the shared buffer.
if (hasattr(sys.stdout, "buffer")
        and getattr(sys.stdout, "encoding", "").lower() != "utf-8"
        and "pytest" not in sys.modules):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
BASE = HERE / "template" / "base_dupilumab_copd.html"

# ---- base-template tokens (constants of the chosen base) --------------------
BASE_DRUG_DISPLAY = "Dupilumab"
BASE_DRUG_LOWER = "dupilumab"
BASE_SLUG = "dupilumab_copd"
BASE_CONDITION = "COPD"


def die(msg: str):
    print(f"\n[CONFIG ERROR] {msg}\n", file=sys.stderr)
    print("See README.md or copy configs/example_finerenone_ckd.json.", file=sys.stderr)
    sys.exit(2)


# Characters that corrupt the global HTML+JS token swap. drug/condition are
# stamped VERBATIM (not js-escaped) into both HTML prose and single-quoted JS
# string literals throughout the engine, so an apostrophe ends a JS string ->
# SyntaxError -> the whole dashboard silently dies (the build still exits 0).
# Backslash and angle brackets break the template-literal / regex-replacement
# contexts the same way. Fail closed: medical names have apostrophe-free
# canonical forms ("Crohn disease", "Alzheimer disease") that are safe here.
_SWAP_UNSAFE = {"'": "apostrophe (')", "\\": "backslash (\\)", "<": "<", ">": ">"}


def _num(v):
    """A real number (not bool/None/str), else None."""
    return v if (isinstance(v, (int, float)) and not isinstance(v, bool)) else None


def _validate_trial_values(i: int, t: dict):
    """Fail closed on clinical/statistical impossibilities so a bad config
    never produces a green build (matches the finerenone repo's
    test_no_impossible_counts / test_data_integrity regression class)."""
    nct = t.get("nct", f"#{i+1}")
    tE, tN, cE, cN = (_num(t.get(k)) for k in ("tE", "tN", "cE", "cN"))
    for label, n in (("tN", tN), ("cN", cN)):
        if n is not None and n < 0:
            die(f"trial {i+1} ({nct}): {label}={n} is negative (impossible arm size).")
    for ev, n, arm in ((tE, tN, "treatment"), (cE, cN, "comparator")):
        if ev is not None and ev < 0:
            die(f"trial {i+1} ({nct}): {arm} event count {ev} is negative.")
        if ev is not None and n is not None and ev > n:
            die(f"trial {i+1} ({nct}): {arm} events ({ev}) exceed arm size ({n}) "
                f"— impossible 2x2 cell.")
    hrL, hrU, hr = (_num(t.get(k)) for k in ("hrLCI", "hrUCI", "publishedHR"))
    for label, v in (("publishedHR", hr), ("hrLCI", hrL), ("hrUCI", hrU)):
        if v is not None and v <= 0:
            die(f"trial {i+1} ({nct}): {label}={v} must be > 0 (ratio measure).")
    if hrL is not None and hrU is not None and hrL > hrU:
        die(f"trial {i+1} ({nct}): inverted CI — hrLCI ({hrL}) > hrUCI ({hrU}).")
    if hr is not None and hrL is not None and hrU is not None and not (hrL <= hr <= hrU):
        die(f"trial {i+1} ({nct}): published point estimate {hr} lies outside its "
            f"CI [{hrL}, {hrU}].")


def _check_swap_safe(field: str, value: str):
    bad = sorted(
        {_SWAP_UNSAFE[c] for c in value if c in _SWAP_UNSAFE}
        | {f"control U+{ord(c):04X}" for c in value if ord(c) < 0x20}
    )
    if bad:
        die(
            f"'{field}' contains characters that break the HTML/JS token swap: "
            f"{', '.join(bad)}. This field is stamped verbatim into JavaScript "
            f"string literals, so an apostrophe (e.g. \"Crohn's disease\") would "
            f"silently break the generated dashboard. Use the apostrophe-free "
            f"canonical form instead (e.g. \"Crohn disease\", \"Alzheimer disease\")."
        )


# ---- JS literal rendering (reused, proven) ---------------------------------
def js_escape(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'")


def render_outcome(o):
    parts = []
    for k in ("shortLabel", "title"):
        if k in o:
            parts.append(f"{k}: '{js_escape(o[k])}'")
    if "type" in o:
        parts.append(f"type: '{js_escape(o['type'])}'")
    for k in ("tE", "cE", "matchScore", "effect", "lci", "uci", "md", "se",
              "pubHR", "pubHR_LCI", "pubHR_UCI"):
        if k in o and o[k] is not None:
            parts.append(f"{k}: {o[k]}")
    if "estimandType" in o:
        parts.append(f"estimandType: '{js_escape(o['estimandType'])}'")
    return "{ " + ", ".join(parts) + " }"


def _jsnum(v):
    """Render a numeric-or-null field for the JS literal."""
    if v is None:
        return "null"
    return str(v)


# Trial IDs are typed evidence fields: a registry ID must resolve to its OWN
# registry, never a fabricated clinicaltrials.gov link. Only these formats are
# auto-linked; any other ID must carry an explicit `sourceUrl` or the build fails.
_REGISTRY_PATTERNS = [
    (re.compile(r"^NCT\d{8}$"),     "https://clinicaltrials.gov/study/{}"),
    (re.compile(r"^ISRCTN\d{8}$"),  "https://www.isrctn.com/{}"),
    (re.compile(r"^ACTRN\d{14}$"),  "https://www.anzctr.org.au/TrialSearch.aspx?searchTxt={}&isBasic=True"),
]


def _is_nct(trial_id) -> bool:
    return bool(re.match(r"^NCT\d{8}$", str(trial_id).strip()))


def _registry_url(trial_id):
    """Canonical registry URL for a recognized trial-ID format, else None."""
    tid = str(trial_id).strip()
    for rx, tmpl in _REGISTRY_PATTERNS:
        if rx.match(tid):
            return tmpl.format(tid)
    return None


def render_trial_entry(t, default_group):
    head = (
        f"name: '{js_escape(t['name'])}', pmid: '{t.get('pmid','') or ''}', "
        f"phase: '{t.get('phase','III')}', year: {t.get('year',2024)}, "
        f"tE: {_jsnum(t.get('tE'))}, tN: {_jsnum(t.get('tN'))}, "
        f"cE: {_jsnum(t.get('cE'))}, cN: {_jsnum(t.get('cN'))}, "
        f"group: '{js_escape(t.get('group', default_group))}', "
        f"publishedHR: {_jsnum(t.get('publishedHR'))}, "
        f"hrLCI: {_jsnum(t.get('hrLCI'))}, hrUCI: {_jsnum(t.get('hrUCI'))}, "
        f"pubHR: {_jsnum(t.get('pubHR', t.get('publishedHR')))}, "
        f"pubHR_LCI: {_jsnum(t.get('pubHR_LCI', t.get('hrLCI')))}, "
        f"pubHR_UCI: {_jsnum(t.get('pubHR_UCI', t.get('hrUCI')))}"
    )
    outcomes = t.get("allOutcomes")
    if not outcomes:
        # Minimal default outcome so the engine always has something to pool.
        outcomes = [{"shortLabel": "Primary", "title": t.get("outcome_label", "Primary outcome"),
                     "type": "binary"}]
    outcomes_str = ",\n                        ".join(render_outcome(o) for o in outcomes)
    rob = t.get("rob", ["some-concerns"] * 5)
    rob_str = "[" + ", ".join(f"'{js_escape(r)}'" for r in rob) + "]"
    nct = t["nct"]
    return f"""'{nct}': {{


                    {head},


                    allOutcomes: [
                        {outcomes_str}
                    ],


                    rob: {rob_str},


                    snippet: '{js_escape(t.get('snippet',''))}',


                    sourceUrl: '{js_escape(t.get('sourceUrl') or _registry_url(nct) or '')}',


                    ctgovUrl: '{f'https://clinicaltrials.gov/study/{nct}' if _is_nct(nct) else ''}',


                    evidence: []


                }}"""


def replace_realdata_block(src, entries_js):
    i = src.find("realData: {")
    if i < 0:
        die("base template has no 'realData: {' block (unexpected).")
    brace = src.find("{", i)
    depth = 0
    started = False
    end = -1
    for j in range(brace, len(src)):
        c = src[j]
        if c == "{":
            depth += 1; started = True
        elif c == "}":
            depth -= 1
            if started and depth == 0:
                end = j; break
    if end < 0:
        die("could not find end of realData block in base template.")
    new_block = "{\n\n\n                " + entries_js + "\n            }"
    return src[:brace] + new_block + src[end + 1:]


def main():
    ap = argparse.ArgumentParser(description="Clone the full RapidMeta dashboard from a config.")
    ap.add_argument("config")
    ap.add_argument("--out")
    args = ap.parse_args()

    if not BASE.exists():
        die(f"base template missing: {BASE} (re-download the kit).")

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        die(f"config not found: {cfg_path}")
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"config is not valid JSON: {e}")

    # Required fields
    drug = cfg.get("drug")
    slug = cfg.get("slug")
    condition = cfg.get("condition")
    title = cfg.get("title")
    trials = cfg.get("trials")
    if not drug:
        die("config needs 'drug' (e.g. \"Finerenone\").")
    if not slug:
        die("config needs 'slug' (lowercase id, e.g. \"finerenone_ckd\").")
    if not re.fullmatch(r"[a-z0-9_]+", slug):
        die("'slug' must be lowercase letters/digits/underscores only (e.g. finerenone_ckd).")
    if not condition:
        die("config needs 'condition' (e.g. \"CKD in type 2 diabetes\").")
    if not title:
        die("config needs 'title'.")
    if not isinstance(trials, list) or len(trials) < 1:
        die("config needs a 'trials' array (>=1; >=2 to pool).")

    drug_lower = cfg.get("drug_lower", drug.lower())
    comparator = cfg.get("comparator", "Placebo")
    default_group = f"{drug} vs {comparator}"

    # P0: drug / drug_lower / condition are stamped UNESCAPED into JS string
    # literals by the global token swap below. Reject swap-breaking characters
    # FIRST (before per-trial checks) so a bad top-level field fails closed with
    # the field-specific message, not an incidental trial-ID error.
    for _field, _val in (("drug", drug), ("drug_lower", drug_lower),
                         ("condition", condition)):
        _check_swap_safe(_field, _val)

    for i, t in enumerate(trials):
        if "nct" not in t or "name" not in t:
            die(f"trial {i+1} needs at least 'nct' and 'name'.")
        tid = str(t["nct"]).strip()
        if _registry_url(tid) is None and not t.get("sourceUrl"):
            die(f"trial {i+1}: id {tid!r} is not a recognized registry ID "
                f"(NCT########, ISRCTN########, ACTRN##############). Provide a "
                f"valid registry ID, or an explicit 'sourceUrl' for other registries "
                f"(EU-CTR/PACTR/ChiCTR/jRCT...). Refusing to emit a false "
                f"clinicaltrials.gov link from an arbitrary string.")
        _validate_trial_values(i, t)

    src = src0 = BASE.read_text(encoding="utf-8")

    # 1) Title / hero / NYT headline. HTML-escape so an angle bracket / ampersand
    #    in a config value can't break the markup or inject an element.
    src = re.sub(r"<title>[^<]*</title>",
                 f"<title>{html.escape(title)}</title>", src, count=1)
    if cfg.get("hero_h2"):
        _hero = html.escape(cfg["hero_h2"])
        src = re.sub(r'(<div class="va-header"><h2[^>]*>)[^<]+(</h2>)',
                     lambda m: m.group(1) + _hero + m.group(2), src, count=1)
    if cfg.get("nyt_headline"):
        _nyt = html.escape(cfg["nyt_headline"])
        src = re.sub(r'(<h3 class="nyt-headline[^>]*>)[^<]+(</h3>)',
                     lambda m: m.group(1) + _nyt + m.group(2), src, count=1)

    # 2) AUTO_INCLUDE_TRIAL_IDS
    ncts = [t["nct"] for t in trials]
    new_set = ", ".join(f"'{n}'" for n in ncts)
    src = re.sub(r"AUTO_INCLUDE_TRIAL_IDS\s*=\s*new\s+Set\(\[[^\]]*\]\)",
                 f"AUTO_INCLUDE_TRIAL_IDS = new Set([{new_set}])", src, count=1)

    # 3) nctAcronyms
    acro = cfg.get("acronyms") or {t["nct"]: t["name"] for t in trials}
    new_map = ", ".join(f"'{n}': '{js_escape(a)}'" for n, a in acro.items())
    src = re.sub(r"nctAcronyms:\s*\{[^}]*\}", f"nctAcronyms: {{ {new_map} }}", src, count=1)

    # 4) PICO protocol
    pico = cfg.get("pico")
    if pico:
        proto_re = re.compile(
            r"(protocol:\s*\{\s*pop:\s*')(?:\\'|[^'])*(',\s*int:\s*')(?:\\'|[^'])*"
            r"(',\s*comp:\s*')(?:\\'|[^'])*(',\s*out:\s*')(?:\\'|[^'])*"
            r"(',\s*subgroup:\s*')(?:\\'|[^'])*('.*?)\}",
            re.DOTALL)

        def repl(m):
            return (m.group(1) + js_escape(pico.get("pop", "")) +
                    m.group(2) + js_escape(pico.get("int", drug)) +
                    m.group(3) + js_escape(pico.get("comp", comparator)) +
                    m.group(4) + js_escape(pico.get("out", "")) +
                    m.group(5) + js_escape(pico.get("subgroup", "")) +
                    m.group(6) + "}")
        src = proto_re.sub(repl, src, count=1)

    # 5) realData
    entries = ",\n\n\n                ".join(
        render_trial_entry(t, default_group) for t in trials)
    src = replace_realdata_block(src, entries)

    # 6) localStorage keys: rapid_meta_dupilumab_copd -> rapid_meta_<slug>
    src = src.replace(f"rapid_meta_{BASE_SLUG}", f"rapid_meta_{slug}")

    # 7) Global token swaps. ORDER MATTERS — most specific/compound first so
    # a later short swap can't corrupt a longer token. Uppercase forms (used
    # in canonical filenames inside JSON-LD metadata) are handled explicitly
    # so no broken "DUPILUMAB_..." URL leaks into the clone.
    slug_upper = slug.upper()
    swaps = [
        # compound filename stems first (uppercase + lowercase)
        (f"{BASE_DRUG_DISPLAY.upper()}_{BASE_CONDITION}", slug_upper),  # DUPILUMAB_COPD
        (BASE_SLUG, slug),                                              # dupilumab_copd
        # then plain drug-name forms in 3 cases
        (BASE_DRUG_DISPLAY.upper(), drug.upper()),                      # DUPILUMAB
        (BASE_DRUG_DISPLAY, drug),                                      # Dupilumab
        (BASE_DRUG_LOWER, drug_lower),                                  # dupilumab
        # finally the condition token
        (BASE_CONDITION, condition),                                    # COPD
    ]
    for old, new in swaps:
        src = src.replace(old, new)

    # 8) JSON-LD provenance. The base template inherits the previous clone's
    # canonical URLs (the rapidmeta-finerenone repo) and an empty ORCID
    # ("identifier":"https://orcid.org/"). Left untouched these mis-attribute
    # every dashboard's machine-readable provenance to the wrong repo and claim
    # an author ID that isn't supplied. Rewrite them from config, with safe
    # defaults, via exact full-field matches + json.dumps so a stray quote /
    # backslash in a config value can't break the JSON-LD block.
    STALE_REPO = "https://mahmood726-cyber.github.io/rapidmeta-finerenone/"
    page_url_stale = f"{STALE_REPO}{slug_upper}_REVIEW.html"
    canonical_url = cfg.get("canonical_url", f"{slug}.html")
    publisher_url = cfg.get("publisher_url",
                            "https://mahmood726-cyber.github.io/rapidmeta-kit/")
    src = src.replace(f'"url":"{page_url_stale}"',
                      f'"url":{json.dumps(canonical_url)}')
    src = src.replace(f'"url":"{STALE_REPO}"',
                      f'"url":{json.dumps(publisher_url)}')
    orcid = cfg.get("orcid")
    if orcid:
        oid = orcid if str(orcid).startswith("http") else f"https://orcid.org/{orcid}"
        src = src.replace('"identifier":"https://orcid.org/"',
                          f'"identifier":{json.dumps(oid)}')
    else:
        # No ORCID given: drop the empty, misleading identifier entirely.
        src = src.replace(',"identifier":"https://orcid.org/"', "")
    # The help text also cites the source repo as <code>owner/repo</code>
    # (the slash form, distinct from the github.io URLs handled above).
    repo = cfg.get("repo", "mahmood726-cyber/rapidmeta-kit")
    src = src.replace("mahmood726-cyber/rapidmeta-finerenone", repo)

    out_path = Path(args.out) if args.out else (HERE / "output" / f"{slug}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(src, encoding="utf-8")

    # Ensure the shared assets/ folder sits next to the output so the
    # dashboard's CSS / vendor JS / plotly resolve offline. Copied once;
    # all dashboards in the same output folder share it.
    import shutil
    master_assets = HERE / "template" / "assets"
    out_assets = out_path.parent / "assets"
    if master_assets.exists() and not out_assets.exists():
        shutil.copytree(master_assets, out_assets)
        print(f"  copied assets/ -> {out_assets} (shared by all dashboards here)")

    # Report
    residual = len(re.findall(BASE_DRUG_LOWER, src, re.I))
    print(f"\nBuilt: {out_path}")
    print(f"  {len(trials)} trial(s) · drug={drug} · slug={slug} · condition={condition}")
    print(f"  size {len(src):,} bytes (full interactive RapidMeta engine)")
    if residual:
        print(f"  note: {residual} residual '{BASE_DRUG_LOWER}' token(s) remain "
              f"(usually inside the engine's help text; harmless).")
    print(f"\nOpen the file in a browser. Works offline; everything runs client-side.")


if __name__ == "__main__":
    main()
