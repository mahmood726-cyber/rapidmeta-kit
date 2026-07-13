r"""assistant.py — the chat INTERFACE. It explains numbers; it never makes one.

THE WALL (rigid, structural — not a guideline):

  * This module does NOT import the pooling engine. There is no code path from a
    chat turn to :func:`rmharness.pooling.pool`. The assistant is handed a
    read-only :class:`Context` built from numbers the deterministic core ALREADY
    computed, plus the provenance records. It cannot recompute anything.
  * Every number in a model's reply is checked against the set of numbers that
    appear in the Context. Any number that is NOT traceable to a computed value
    is treated as a fabrication: the reply is REFUSED (fail-closed), never shown.
    So even a tiny model that hallucinates a statistic cannot surface one.
  * If the answer isn't in the Context, the assistant says so ("I don't know —
    that isn't in the data") rather than inventing it.

Two back-ends, same wall:
  * NO MODEL  -> a deterministic template explainer. Grounded by construction,
    zero fabrication, works on any machine. The tool is never blocked on a model.
  * SMALL MODEL (llama-cpp-python, GGUF) -> fluent natural-language answers,
    passed through the same fabrication gate before the user sees them.

Tests in tests/test_assistant_wall.py TRIP if the wall is ever breached.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Optional

# NOTE: deliberately NO `from .pooling import ...`. The assistant must not be able
# to compute. tests/test_assistant_wall.py asserts this import is absent.

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


# --------------------------------------------------------------------------- #
# Read-only context: computed facts + provenance. Immutable by construction.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Context:
    """A frozen snapshot of ALREADY-COMPUTED results the assistant may explain.

    `facts` is a read-only mapping of label -> value. `allowed` is the set of
    numeric tokens (as rounded strings) that legitimately appear in the facts;
    the fabrication gate rejects any number a reply contains that is not in it.
    """
    facts: MappingProxyType
    allowed: frozenset
    provenance: tuple
    narrative: str  # the text block shown to the model

    def render(self) -> str:
        return self.narrative


def _num_variants(x) -> list:
    """String forms a number may legitimately take in a reply (rounding-aware)."""
    if x is None:
        return []
    try:
        f = float(x)
    except (TypeError, ValueError):
        return []
    out = set()
    for nd in (0, 1, 2, 3, 4):
        out.add(f"{f:.{nd}f}")
    if abs(f - round(f)) < 1e-9:
        out.add(str(int(round(f))))
    # percent form (I^2 stored as a number like 68.0 -> "68")
    out.add(f"{f:.0f}")
    return list(out)


def _canon(tok: str) -> str:
    """Canonicalize a numeric token for comparison: drop trailing zeros."""
    try:
        f = float(tok)
    except ValueError:
        return tok
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return ("%.6f" % f).rstrip("0").rstrip(".")


def build_context(pooled: dict, trials: list, provenance: Optional[list] = None,
                  published: Optional[list] = None,
                  exclusions: Optional[list] = None) -> Context:
    """Assemble a read-only Context from the deterministic core's output.

    `pooled` is a pooled-result dict from the deterministic core; `trials` the bundle trial rows;
    `provenance` optional per-trial source records; `published` optional
    comparison values; `exclusions` optional {trial, reason} rows.
    """
    facts = {}
    measure = pooled.get("measure", "effect")
    facts["measure"] = measure
    facts["k (number of trials pooled)"] = pooled.get("k")
    if pooled.get("estimate_ratio") is not None:
        facts[f"pooled {measure}"] = round(pooled["estimate_ratio"], 4)
        ci = pooled.get("ci_ratio") or [None, None]
        if ci[0] is not None:
            facts[f"pooled {measure} 95% CI"] = [round(ci[0], 4), round(ci[1], 4)]
    else:
        facts[f"pooled {measure} (log/difference scale)"] = round(pooled.get("estimate_log", 0.0), 4)
    facts["I-squared (%)"] = round(pooled.get("I2_percent", 0.0), 1)
    facts["tau-squared (between-study variance)"] = round(pooled.get("tau2", 0.0), 4)
    facts["Cochran Q"] = round(pooled.get("Q", 0.0), 4)
    facts["degrees of freedom"] = pooled.get("df")

    # per-trial rows (labels + published effect where present)
    tl = []
    for t in trials:
        row = {"name": t.get("name") or t.get("nct")}
        for kk in ("year", "nct", "pmid", "publishedHR", "hrLCI", "hrUCI", "tE", "tN", "cE", "cN"):
            if t.get(kk) is not None:
                row[kk] = t[kk]
        tl.append(row)
    facts["trials"] = tl

    if published:
        facts["published comparison"] = published
    if exclusions:
        facts["excluded trials (with reasons)"] = exclusions

    prov = tuple((p.get("name") or p.get("nct"), p.get("source"), p.get("doi"))
                 for p in (provenance or []))

    narrative = _render_facts(facts, prov)

    # Allowed numeric tokens = every number that ACTUALLY APPEARS in the context
    # the model is shown (the narrative — computed values, per-trial counts,
    # citation years/volumes, DOIs), plus rounding variants of the computed
    # values so a legitimate re-rounding ("0.87" for 0.8722) is accepted. A reply
    # may repeat any number it can see; it may never introduce one it cannot.
    allowed = set()
    for tok in _NUM.findall(narrative):
        allowed.add(_canon(tok))

    def _collect(v):
        if isinstance(v, dict):
            for x in v.values():
                _collect(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                _collect(x)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            for s in _num_variants(v):
                allowed.add(_canon(s))
    _collect(facts)

    return Context(facts=MappingProxyType(dict(facts)),
                   allowed=frozenset(allowed), provenance=prov, narrative=narrative)


def _render_facts(facts: dict, prov: tuple) -> str:
    lines = ["COMPUTED RESULTS (these are the ONLY numbers you may state):"]
    for k, v in facts.items():
        if k == "trials":
            lines.append("- trials pooled:")
            for r in v:
                bits = ", ".join(f"{kk}={vv}" for kk, vv in r.items() if kk != "name")
                lines.append(f"    * {r['name']}: {bits}")
        elif k in ("published comparison", "excluded trials (with reasons)"):
            lines.append(f"- {k}: {v}")
        else:
            lines.append(f"- {k}: {v}")
    if prov:
        lines.append("PROVENANCE (source of each trial):")
        for name, src, doi in prov:
            lines.append(f"    * {name}: {src} (doi {doi})")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Fabrication gate — the numeric wall
# --------------------------------------------------------------------------- #
def fabricated_numbers(answer: str, ctx: Context) -> list:
    """Return numbers in `answer` that are NOT traceable to the Context.

    A non-empty result means the reply invented a statistic -> it must be refused.
    Years and list indices inside the provenance/citation strings are allowed
    because they were collected into ctx.allowed.
    """
    bad = []
    for tok in _NUM.findall(answer):
        if _canon(tok) in ctx.allowed:
            continue
        # allow bare small integers 0-12 (counts, list positions, 'k' values)
        try:
            f = float(tok)
            if abs(f - round(f)) < 1e-9 and 0 <= f <= 12:
                continue
        except ValueError:
            pass
        bad.append(tok)
    return bad


REFUSAL = ("I can't answer that from the computed results — it isn't in the data. "
           "The numbers I can explain are the ones in this review's results and provenance.")

# Quantities a pooled-effect review does NOT contain. If a question asks for one
# of these and the results object doesn't carry it, we refuse BEFORE the model can
# misattribute an in-context number to the wrong concept (a tiny model asked for a
# p-value will happily label I^2=0 as "p=0.0"). This is the second guard: the
# number-wall stops untraceable numbers; this stops unsupported *intents*.
_UNSUPPORTED = {
    "p-value": ("p-value", "p value", "pvalue", "p val"),
    "number needed to treat": ("number needed to treat", "nnt"),
    "absolute risk / ARR": ("absolute risk", "arr", "risk reduction percent"),
    "cost / price": ("price", "cost", "how much does", "afford"),
    "prevalence / incidence": ("prevalence", "incidence", "how many people", "how many patients"),
    "diagnostic accuracy": ("sensitivity", "specificity", "likelihood ratio", "auc"),
}


def unsupported_intent(question: str, ctx: "Context") -> Optional[str]:
    """If the question asks for a named quantity this review does not compute,
    return that quantity's label (-> caller refuses); else None. Skips the check
    when the quantity actually IS present in the facts."""
    q = question.lower()
    facts_blob = " ".join(str(k).lower() for k in ctx.facts.keys())
    for label, kws in _UNSUPPORTED.items():
        if any(kw in q for kw in kws):
            # only refuse if we genuinely don't carry it
            if not any(kw in facts_blob for kw in kws):
                return label
    return None


def guard(answer: str, ctx: Context) -> tuple:
    """Pass a model reply through the wall. Returns (safe_text, ok, fabricated)."""
    bad = fabricated_numbers(answer, ctx)
    if bad:
        return (REFUSAL, False, bad)
    return (answer, True, [])


# --------------------------------------------------------------------------- #
# Deterministic explainer (NO MODEL) — grounded by construction
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "You are a careful meta-analysis assistant embedded in an offline tool. Your "
    "job is to EXPLAIN, in plain language, the results already computed by a "
    "deterministic engine, shown in the COMPUTED RESULTS block.\n"
    "RULES:\n"
    "1. You MAY explain what a quantity means and what it implies (e.g. what "
    "I-squared measures, whether a confidence interval crosses 1, what "
    "heterogeneity implies for a conclusion), using the numbers shown.\n"
    "2. You MUST NOT state, compute, estimate, or invent any NUMBER that is not "
    "already in the COMPUTED RESULTS block. Never do arithmetic. Quote the "
    "provided numbers verbatim.\n"
    "3. If a question asks for a number or fact that is NOT in the block, reply "
    "exactly: \"I don't know - that isn't in the data.\"\n"
    "Be brief, plain, and helpful. Prefer explaining the shown numbers over "
    "refusing."
)


def explain_deterministic(ctx: Context, question: str) -> str:
    """A no-model fallback: template answers for the common questions, grounded
    only in the Context. Zero fabrication by construction."""
    unsup = unsupported_intent(question, ctx)
    if unsup is not None:
        return (f"I don't know - that isn't in the data. This review computes the pooled "
                f"effect, its CI, heterogeneity and the included trials; it does not "
                f"produce {unsup}.")
    q = question.lower()
    f = ctx.facts
    measure = f.get("measure", "effect")
    pooled = f.get(f"pooled {measure}")
    ci = f.get(f"pooled {measure} 95% CI")
    i2 = f.get("I-squared (%)")
    tau2 = f.get("tau-squared (between-study variance)")
    k = f.get("k (number of trials pooled)")

    def with_ci():
        return f"{pooled} (95% CI {ci[0]} to {ci[1]})" if (pooled is not None and ci) else str(pooled)

    if any(w in q for w in ("i2", "i²", "i-squared", "heterogen")):
        msg = (f"I-squared is {i2}%. It is the share of the variation across the "
               f"{k} trials that is due to real differences between them rather "
               f"than chance. tau-squared (the between-study variance) is {tau2}. ")
        if i2 is not None:
            if i2 < 25:
                msg += "This is low: the trials tell a consistent story, so the pooled number is a fair summary."
            elif i2 < 60:
                msg += "This is moderate: interpret the pooled number with some caution."
            else:
                msg += ("This is high: the trials disagree enough that a single pooled number "
                        "may be misleading. Look at what differs between them before relying on it.")
        return msg
    # specific intents BEFORE the generic 'pooled result' catch-all, so
    # "which trials are pooled" isn't swallowed by the word "pooled".
    if any(w in q for w in ("which trial", "which trials", "what trials", "drive", "weight",
                            "influential", "biggest", "included", "list")):
        names = ", ".join(r["name"] for r in f.get("trials", []))
        return (f"The pooled estimate is an inverse-variance weighted average of these "
                f"{k} trials: {names}. Larger, more precise trials get more weight. "
                f"Use 'remove <trial>' in the harness to see exactly how much each one moves the result.")
    if any(w in q for w in ("reduce", "benefit", "protective", "help", "work", "significant", "cross")):
        if pooled is not None and ci:
            direction = ("below 1, and the 95% CI does not cross 1, so the effect is "
                         "statistically significant in the protective direction"
                         if ci[1] < 1 else
                         "and the 95% CI crosses 1, so the effect is not statistically significant")
            return (f"The pooled {measure} is {with_ci()}. That is {direction}. "
                    f"(This describes the pooled numbers; it is not medical advice.)")
    if any(w in q for w in ("pooled", "overall", "result", "effect", "summary", "headline")):
        return (f"The pooled {measure} across {k} trials is {with_ci()}. "
                f"Heterogeneity I-squared is {i2}%.")
    if any(w in q for w in ("exclud", "why not", "left out")):
        ex = f.get("excluded trials (with reasons)")
        if ex:
            return "Excluded trials and reasons: " + "; ".join(
                f"{e.get('trial')} ({e.get('reason')})" for e in ex)
        return "I don't have exclusion reasons in this review's data."
    if any(w in q for w in ("published", "cochrane", "compare", "agree")):
        pub = f.get("published comparison")
        if pub:
            return f"Published comparison on record: {pub}. Our pooled {measure} is {with_ci()}."
        return "There is no published-comparison value in this review's data."
    # default
    return (f"I can explain the computed results for this review: pooled {measure} "
            f"{with_ci()}, I-squared {i2}%, across {k} trials. Ask about the pooled "
            f"result, heterogeneity, what drives it, exclusions, or the published comparison.")


# --------------------------------------------------------------------------- #
# Optional small-model back-end (llama-cpp-python). Same wall applies.
# --------------------------------------------------------------------------- #
class LlamaChat:
    """Thin wrapper over llama-cpp-python for a local GGUF. No Ollama, no server.
    Loaded lazily; the assistant works without it (deterministic explainer)."""

    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: Optional[int] = None,
                 verbose: bool = False):
        from llama_cpp import Llama  # imported only if a model is actually used
        self.model_path = model_path
        self.llm = Llama(model_path=model_path, n_ctx=n_ctx,
                         n_threads=n_threads, verbose=verbose)

    def reply(self, system: str, context_text: str, question: str, max_tokens: int = 256) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{context_text}\n\nQUESTION: {question}"},
        ]
        out = self.llm.create_chat_completion(messages=messages, max_tokens=max_tokens,
                                              temperature=0.0)
        return out["choices"][0]["message"]["content"].strip()


def answer(ctx: Context, question: str, chat: Optional[LlamaChat] = None) -> dict:
    """Answer a question about the review. If a model is provided it phrases the
    reply, but the fabrication gate always runs before the text is returned. With
    no model, the grounded deterministic explainer is used.

    Returns {text, ok, fabricated, backend}. `ok` is False only if a model reply
    was refused for fabricating a number.
    """
    # Guard 2 (intent): refuse unsupported quantities before the model can answer,
    # so it cannot misattribute an in-context number to a concept we don't have.
    unsup = unsupported_intent(question, ctx)
    if unsup is not None:
        text = (f"I don't know - that isn't in the data. This review does not produce {unsup}.")
        return {"text": text, "ok": True, "fabricated": [],
                "backend": "deterministic" if chat is None else "model", "refused_intent": unsup}
    if chat is None:
        return {"text": explain_deterministic(ctx, question), "ok": True,
                "fabricated": [], "backend": "deterministic"}
    raw = chat.reply(SYSTEM_PROMPT, ctx.render(), question)
    safe, ok, bad = guard(raw, ctx)          # Guard 1 (numeric): no untraceable number
    return {"text": safe, "ok": ok, "fabricated": bad, "backend": "model",
            "raw": raw}
