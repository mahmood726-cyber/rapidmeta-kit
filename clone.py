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


def _replace_exactly(src: str, old: str, new: str, what: str, n: int = 1) -> str:
    """Full-string literal replace that fails closed if the expected number of
    occurrences is not present. The existing step-8 url replaces do NOT assert,
    so a base-template change can silently no-op and leave inherited prose in
    the output while every test still passes. Every honesty-bug reset below goes
    through here so a partial/zero match is a hard build error, not a silent
    leak. Match the POST-step-1 / PRE-swap base string (see ordering note)."""
    count = src.count(old)
    if count != n:
        die(f"internal: expected {n} occurrence(s) of {what} in the base "
            f"template, found {count}. The base template changed — clone.py's "
            f"honesty-bug resets are out of sync and would silently leak the "
            f"DUPILUMAB_COPD base claims. Refusing to emit a mis-attributed "
            f"dashboard.")
    return src.replace(old, new)


# Characters that corrupt the global HTML+JS token swap. drug/condition are
# stamped VERBATIM (not js-escaped) into both HTML prose and single-quoted JS
# string literals throughout the engine, so an apostrophe ends a JS string ->
# SyntaxError -> the whole dashboard silently dies (the build still exits 0).
# Backslash and angle brackets break the template-literal / regex-replacement
# contexts the same way. Fail closed: medical names have apostrophe-free
# canonical forms ("Crohn disease", "Alzheimer disease") that are safe here.
_SWAP_UNSAFE = {"'": "apostrophe (')", "\\": "backslash (\\)", "<": "<", ">": ">"}
# `condition` (unlike drug/drug_lower) is ALSO stamped into JS regex literals,
# where a forward slash closes the regex -> SyntaxError (build still exits 0).
# So slash is unsafe in condition specifically. Use "or"/"and" instead
# ("general anaesthesia or sedation", "type 1 or 2 diabetes").
_SWAP_UNSAFE_CONDITION = dict(_SWAP_UNSAFE,
    **{"/": "forward slash (/) — condition is stamped into a JS regex literal; use 'or'/'and'"})


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


def _check_swap_safe(field: str, value: str, unsafe: dict = _SWAP_UNSAFE):
    bad = sorted(
        {unsafe[c] for c in value if c in unsafe}
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
        _check_swap_safe(_field, _val,
                         _SWAP_UNSAFE_CONDITION if _field == "condition" else _SWAP_UNSAFE)

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

    # 4) PICO protocol. ALWAYS reset (not just when config supplies `pico`):
    # the base `protocol:{}` carries dupilumab estimand prose ("Adults with COPD
    # and type-2 inflammation", "Annual moderate-severe exacerbation rate ...",
    # "Blood eosinophils, smoking status, ICS use"). The token swap leaves all of
    # that intact, so a config that omits `pico` would otherwise ship dupilumab
    # PICO text. Fall back to topic-neutral defaults derived from drug/condition.
    pico = cfg.get("pico") or {}
    proto_re = re.compile(
        r"(protocol:\s*\{\s*pop:\s*')(?:\\'|[^'])*(',\s*int:\s*')(?:\\'|[^'])*"
        r"(',\s*comp:\s*')(?:\\'|[^'])*(',\s*out:\s*')(?:\\'|[^'])*"
        r"(',\s*subgroup:\s*')(?:\\'|[^'])*('.*?)\}",
        re.DOTALL)
    _proto_n = len(proto_re.findall(src))
    if _proto_n != 1:
        die(f"internal: expected exactly 1 protocol:{{...}} block in the base "
            f"template, found {_proto_n} — base changed; refusing to leak the "
            f"inherited dupilumab PICO prose.")

    def repl(m):
        return (m.group(1) + js_escape(pico.get("pop") or f"Adults with {condition}") +
                m.group(2) + js_escape(pico.get("int", drug)) +
                m.group(3) + js_escape(pico.get("comp", comparator)) +
                m.group(4) + js_escape(pico.get("out") or "Primary outcome (see Outcome Selector)") +
                m.group(5) + js_escape(pico.get("subgroup", "")) +
                m.group(6) + "}")
    src = proto_re.sub(repl, src, count=1)

    # 5) realData
    entries = ",\n\n\n                ".join(
        render_trial_entry(t, default_group) for t in trials)
    src = replace_realdata_block(src, entries)

    # 6) localStorage keys: rapid_meta_dupilumab_copd -> rapid_meta_<slug>
    src = src.replace(f"rapid_meta_{BASE_SLUG}", f"rapid_meta_{slug}")

    # 6b) HONESTY-BUG resets (run AFTER step 1's <title> rewrite and BEFORE the
    #     step-7 token swap, so we match the pristine base strings exactly).
    #     Left untouched, the swap only rewrites the Dupilumab/COPD/slug tokens
    #     and leaves the dupilumab-specific PROSE, the "RapidMeta Respiratory"
    #     headline, the frozen 2026-05-24 dates, and the "landmark RCTs" quality
    #     claim — all of which become false claims on a new topic. Every reset
    #     below asserts its match count (via _replace_exactly) so a future base
    #     change can't silently no-op into a leak.
    import datetime as _dt

    # P0-1: meta description + JSON-LD description. The base value is dupilumab
    # estimand prose ("type-2 inflammation; Annual moderate-severe exacerbation
    # rate ..."). Rewrite from optional config 'description', else a topic-
    # neutral default. The same string appears in <meta content="..."> and in
    # the JSON-LD "description":"..." field — both are reset.
    _base_desc = ("Dupilumab; Adults with COPD and type-2 inflammation; "
                  "Annual moderate-severe exacerbation rate Pooled mean "
                  "differences reflect the trial-published primary analyt")
    _desc = cfg.get("description") or (
        f"{drug} in {condition}: living meta-analysis dashboard.")
    # The meta tag is plain-HTML attribute text; HTML-escape it. The JSON-LD
    # field is JSON; json.dumps it (the leading/trailing quotes come from dumps).
    src = _replace_exactly(
        src,
        f'<meta name="description" content="{_base_desc}">',
        f'<meta name="description" content="{html.escape(_desc, quote=True)}">',
        'the inherited <meta> description')
    src = _replace_exactly(
        src,
        f'"description":"{_base_desc}"',
        f'"description":{json.dumps(_desc)}',
        'the inherited JSON-LD description')

    # P0-2: JSON-LD headline + name, the in-engine app: title, and the two
    # print/export <title>s. The base brand is "RapidMeta Respiratory | ... with
    # Type 2 Inflammation v1.1". Build the new brand from the required config
    # title, prefixing "RapidMeta <specialty> | " ONLY if config sets specialty
    # (drop the hardcoded "Respiratory" otherwise — a false specialty claim on a
    # cardiology/critical-care topic).
    _specialty = cfg.get("specialty")
    _brand = f"RapidMeta {_specialty} | {title}" if _specialty else title
    _base_brand = ("RapidMeta Respiratory | Dupilumab for COPD with "
                   "Type 2 Inflammation v1.1")
    # JSON-LD headline+name (one combined, unique substring -> count 1).
    src = _replace_exactly(
        src,
        f'"headline":"{_base_brand}","name":"{_base_brand}"',
        f'"headline":{json.dumps(_brand)},"name":{json.dumps(_brand)}',
        'the inherited JSON-LD headline/name')
    # The in-engine app-name and the two print/export <title>s share the bare
    # brand string verbatim (3 occurrences after step 1 consumed the page
    # <title>). Reset all three together.
    src = _replace_exactly(src, _base_brand, html.escape(_brand),
                           'the inherited app/print brand titles', n=3)

    # P0-3: JSON-LD datePublished / dateModified. The base is frozen at
    # 2026-05-24 (the dupilumab build date). Use optional config 'date', else
    # today's build date — never inherit the stale date.
    _date = cfg.get("date") or _dt.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(_date)):
        die(f"config 'date' must be ISO YYYY-MM-DD (got {_date!r}).")
    src = _replace_exactly(src, '"datePublished":"2026-05-24"',
                           f'"datePublished":{json.dumps(_date)}',
                           'the inherited datePublished')
    src = _replace_exactly(src, '"dateModified":"2026-05-24"',
                           f'"dateModified":{json.dumps(_date)}',
                           'the inherited dateModified')

    # P1-5: hero subtitle quality claim. "Multi-source meta-analysis of landmark
    # RCTs" overstates the evidence base ("landmark" is unearned). Soften to
    # "included RCTs". Appears 3x: the hero <p> plus two i18n lookup KEYS — all
    # three are reset together so the Arabic-translation lookup keeps matching
    # the displayed English text.
    src = _replace_exactly(src, "landmark RCTs", "included RCTs",
                           'the "landmark RCTs" hero/i18n claim', n=3)

    # P0-1b: the visible "Review Title" PICO row + the editable Population /
    # Primary-Outcome <input> values carry dupilumab estimand prose verbatim
    # ("(IL-4Ralpha Monoclonal Antibody) for Moderate-to-Severe COPD with Type 2
    # Inflammation (Blood Eosinophils >=300/uL)...", "Adults with COPD and
    # type-2 inflammation", "Annual moderate-severe exacerbation rate"). The
    # token swap alone leaves the dupilumab-specific clinical detail intact, so
    # these are reset from config (pico.* / review_title) with topic-neutral
    # defaults. _pico is the config pico block (may be None).
    _pico = cfg.get("pico") or {}
    _review_title = cfg.get("review_title", title)
    src = _replace_exactly(
        src,
        '<td class="p-4 text-slate-300">Dupilumab (IL-4Ralpha Monoclonal '
        'Antibody) for Moderate-to-Severe COPD with Type 2 Inflammation '
        '(Blood Eosinophils >=300/uL): A Living Systematic Review and '
        'Meta-Analysis of Phase 3 RCTs</td>',
        f'<td class="p-4 text-slate-300">{html.escape(_review_title)}</td>',
        'the inherited Review Title row')
    _pop = _pico.get("pop") or f"Adults with {condition}"
    src = _replace_exactly(
        src,
        'value="Adults with COPD and type-2 inflammation"',
        f'value="{html.escape(_pop, quote=True)}"',
        'the inherited Population PICO input')
    _out = _pico.get("out") or "Primary outcome (see Outcome Selector)"
    src = _replace_exactly(
        src,
        'value="Annual moderate-severe exacerbation rate"',
        f'value="{html.escape(_out, quote=True)}"',
        'the inherited Primary Outcome PICO input')

    # P0-1c: PUBLISHED_META_BENCHMARKS is a hardcoded dupilumab external-evidence
    # block (real BOREAS/NOTUS NEJM trials, Bhatt 2023/2024). On any cloned topic
    # the swap turns these into FABRICATED comparators ("finerenone vs placebo
    # ... NEJM 2023;389:205-214"). The consumer reads it with `?? []`, so empty
    # it unless the config supplies its own benchmarks. Matched as a regex on the
    # whole const (whitespace-tolerant) but asserted to change exactly once.
    _bench_re = re.compile(
        r"const PUBLISHED_META_BENCHMARKS = \{.*?\n        \};",
        re.DOTALL)
    _bench_matches = _bench_re.findall(src)
    if len(_bench_matches) != 1:
        die(f"internal: expected exactly 1 PUBLISHED_META_BENCHMARKS block, "
            f"found {len(_bench_matches)} — base template changed; refusing to "
            f"leak fabricated dupilumab benchmark comparators.")
    if cfg.get("benchmarks"):
        _bench_js = "const PUBLISHED_META_BENCHMARKS = " + json.dumps(
            cfg["benchmarks"]) + ";"
    else:
        _bench_js = "const PUBLISHED_META_BENCHMARKS = {};"
    src = _bench_re.sub(lambda _m: _bench_js, src, count=1)

    # P1-6: fail closed if the template tree carries an inherited self-assurance
    # badge tier (an unearned Bronze/Silver/Gold assurance claim) or an
    # assurance.json. The current base has none (its only "Gold" hits are
    # "Goldacre" citations), so this is a forward regression guard: if a future
    # base re-bakes an assurance tier, refuse to clone it onto a new topic where
    # the badge would be a false claim.
    _assurance_files = list((HERE / "template").rglob("assurance.json"))
    if _assurance_files:
        die(f"inherited assurance artifact(s) in the template tree: "
            f"{', '.join(str(p) for p in _assurance_files)}. A cloned topic "
            f"must not inherit a self-assurance badge tier it has not earned. "
            f"Remove the assurance.json from the base before cloning.")
    _baked_tier = re.search(
        r'(?:assurance|badge)[_\s]*tier"?\s*[:=]\s*"?(Bronze|Silver|Gold)',
        src, re.I)
    if _baked_tier:
        die(f"the base template bakes in an assurance/badge tier "
            f"({_baked_tier.group(1)}) — refusing to stamp an unearned "
            f"assurance claim onto the cloned topic.")

    # P1-4: hero_h2 / nyt_headline fail-closed. If the config omits these, the
    # post-swap fallback (handled below) is the base text with only the
    # drug/condition tokens swapped — which can still carry a topic-specific
    # claim (the hero "...with Type-2 Inflammation", the "Dupilumab Evidence"
    # NYT headline). Rather than ship that leaked claim, require the operator to
    # supply them. (Checked after the swap, below, where the fallback is final.)

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

    # P1-4 (resolved here, post-swap): hero_h2 / nyt_headline fail-closed.
    # When the config supplies these, step 1 already overwrote the hero <h2> /
    # NYT <h3>. When it omits them, the displayed text is the BASE prose with
    # only the drug/condition tokens swapped — which can still carry a topic-
    # specific claim the new topic never earned:
    #   * hero fallback "<drug> in <condition> with Type-2 Inflammation"
    #   * NYT fallback  "The <drug> Evidence"  (was "The Dupilumab Evidence")
    # If a banned token survives in the un-overridden fallback, refuse to build
    # and tell the operator to supply hero_h2 / nyt_headline explicitly.
    _LEAK_TOKENS = ("Type-2 Inflammation", "Type 2 Inflammation",
                    "Dupilumab Evidence")
    if not cfg.get("hero_h2") or not cfg.get("nyt_headline"):
        _leaked = [tok for tok in _LEAK_TOKENS if tok in src]
        if _leaked:
            missing = [f for f, present in (("hero_h2", cfg.get("hero_h2")),
                                            ("nyt_headline", cfg.get("nyt_headline")))
                       if not present]
            die(f"the un-overridden hero/NYT fallback still contains "
                f"topic-specific base text {_leaked} that does not match "
                f"'{drug} in {condition}'. The drug/condition token swap alone "
                f"cannot make this honest. Supply {', '.join(missing)} in the "
                f"config (a topic-neutral headline) so the dashboard does not "
                f"ship an inherited DUPILUMAB_COPD claim.")

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
