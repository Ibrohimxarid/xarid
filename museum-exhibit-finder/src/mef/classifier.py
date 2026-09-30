"""[4] Relevance classifier.

Rule-based and multilingual (see ``config/lexicon.yaml``). For each page or
search snippet it answers, from matched phrases only:

* is this a museum / science centre?          (``is_museum``)
* is it a commercial seller of *new* exhibits? (``commercial`` → excluded)
* which event-chain signals are present?       (renovation … availability)
* which exhibit categories are mentioned?
* how far along the chain is it?               (``stage`` 0–5)
* candidate priority A/B/C                     (to be verified by a person)

It never concludes availability without an availability phrase in the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

from . import POTENTIAL_LEAD
from .config import load_yaml, settings
from .models import AVAILABILITY_SIGNALS, EVENT_SIGNALS, REMOVAL_SIGNALS, Classification

_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")

_MUSEUM_HOST = re.compile(
    r"(museum|museo|musee|museu|muzeum|museet|science|technik|teknisk|tekniska|exploratorium|"
    r"discovery|heureka|experimentarium|technorama|verkehrshaus|questacon|planetarium|miraikan)",
    re.I,
)

FATE_SIGNALS = {"storage", "deaccession_in_progress", "already_transferred", "destroyed"}

SIGNAL_WEIGHTS = {
    "for_sale": 5,
    "for_donation": 5,
    "available_transfer": 5,
    "willing_transfer": 4,
    "willing_sale": 4,
    "deaccession_in_progress": 4,
    "accepts_requests": 2,
    "international_ok": 1,
    "exhibit_replaced": 3,
    "closure": 3,
    "storage": 2,
    "already_transferred": 1,
    "touring_for_hire": 1,
    "renovation": 1,
    "new_exhibition": 1,
    "relocation": 1,
    "deaccession_policy": 0.5,
    "destroyed": 0,
}


def _compile(pattern: str) -> re.Pattern:
    if _CJK.search(pattern):
        return re.compile(pattern, re.IGNORECASE)
    return re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class Lexicon:
    signals: dict[str, list[re.Pattern]]
    museum_terms: list[re.Pattern]
    commercial_terms: list[re.Pattern]
    categories: dict[str, list[re.Pattern]]


@lru_cache(maxsize=1)
def lexicon() -> Lexicon:
    raw = load_yaml("lexicon.yaml")
    return Lexicon(
        signals={k: [_compile(p) for p in v] for k, v in raw.get("signals", {}).items()},
        museum_terms=[_compile(p) for p in raw.get("museum_terms", [])],
        commercial_terms=[_compile(p) for p in raw.get("commercial_terms", [])],
        categories={k: [_compile(p) for p in v] for k, v in raw.get("categories", {}).items()},
    )


def _matches(patterns: list[re.Pattern], text: str, limit: int = 5) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        for m in pat.finditer(text):
            phrase = m.group(0).strip()
            if phrase.lower() not in (f.lower() for f in found):
                found.append(phrase)
            if len(found) >= limit:
                return found
    return found


def match_signals(text: str) -> dict[str, list[str]]:
    lex = lexicon()
    out: dict[str, list[str]] = {}
    for name, patterns in lex.signals.items():
        hits = _matches(patterns, text)
        if hits:
            out[name] = hits
    return out


def match_categories(text: str, min_hits: int = 1) -> list[str]:
    lex = lexicon()
    cats = []
    for name, patterns in lex.categories.items():
        if len(_matches(patterns, text, limit=min_hits)) >= min_hits:
            cats.append(name)
    return cats


def stage_of(signals: set[str], is_museum: bool) -> int:
    """0 nothing · 1 museum · 2 event · 3 old exhibits removed · 4 fate known · 5 available."""
    if signals & AVAILABILITY_SIGNALS:
        return 5
    if signals & FATE_SIGNALS:
        return 4
    if signals & REMOVAL_SIGNALS:
        return 3
    if signals & EVENT_SIGNALS:
        return 2
    return 1 if is_museum else 0


def candidate_priority(signals: set[str], is_museum: bool, commercial: bool) -> str | None:
    if commercial and not is_museum:
        return None
    if not is_museum:
        return None
    if signals & AVAILABILITY_SIGNALS:
        return "A?"
    if signals & REMOVAL_SIGNALS or "deaccession_in_progress" in signals:
        return "B?"
    if signals & EVENT_SIGNALS or "touring_for_hire" in signals:
        return "C?"
    return None


def classify(url: str, text: str, title: str = "") -> Classification:
    blob = f"{title}\n{text}"
    lex = lexicon()
    museum_hits = _matches(lex.museum_terms, blob, limit=10)
    commercial_hits = _matches(lex.commercial_terms, blob, limit=5)
    host = urlsplit(url).netloc
    is_museum = len(museum_hits) >= 1 or bool(_MUSEUM_HOST.search(host))
    museum_score = min(1.0, len(museum_hits) / 3)
    commercial = bool(commercial_hits)

    sig = match_signals(blob)
    cats = match_categories(blob)
    names = set(sig)
    stage = stage_of(names, is_museum)
    prio = candidate_priority(names, is_museum, commercial)

    wanted = set(settings().museum_profile.get("priority_categories", []))
    relevance = sum(SIGNAL_WEIGHTS.get(s, 0) for s in names)
    relevance += min(3.0, 0.5 * len(wanted & set(cats)))
    relevance += 1.0 if is_museum else 0.0
    relevance -= 5.0 if commercial and not is_museum else 0.0

    if prio == "A?":
        summary = "Availability language found — verify against the source before rating A."
    elif prio in ("B?", "C?"):
        summary = POTENTIAL_LEAD
    elif commercial and not is_museum:
        summary = "Excluded: commercial supplier of new exhibits."
    else:
        summary = "Not relevant (no museum event signals)."

    return Classification(
        url=url,
        is_museum=is_museum,
        museum_score=round(museum_score, 2),
        commercial=commercial,
        signals=sig,
        categories=cats,
        stage=stage,
        priority=prio,
        relevance=round(relevance, 2),
        summary=summary,
    )
