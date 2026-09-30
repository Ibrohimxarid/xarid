"""[7] Exhibit extractor.

Finds sentences that talk about specific exhibits/objects being replaced,
removed, stored or offered, and tags them with the exhibit taxonomy. The
output is a list of *mentions* for a researcher to confirm — it does not
create exhibit records by itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .classifier import match_categories, match_signals

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ0-9\"'“])")

OBJECT_WORDS = re.compile(
    r"(?<!\w)(exhibits?|interactives?|installations?|objects?|simulators?|engines?|locomotives?|"
    r"aircraft|vehicles?|machines?|models?|galler(y|ies)|displays?|equipment|collection|"
    r"Exponate?|Objekte?|Ausstellung|dispositifs?|manipulations?|objets?|opstellingen?|objecten|"
    r"föremål|genstande|gjenstander|esineet|piezas|oggetti|eksponaty|exponáty)(?!\w)",
    re.I,
)


@dataclass
class ExhibitMention:
    sentence: str
    signals: list[str]
    categories: list[str]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in _SENT.split(text) if len(s.strip()) > 20]


def extract_mentions(text: str, max_mentions: int = 25) -> list[ExhibitMention]:
    out: list[ExhibitMention] = []
    for sent in split_sentences(text):
        if not OBJECT_WORDS.search(sent):
            continue
        sig = match_signals(sent)
        if not sig:
            continue
        out.append(ExhibitMention(sentence=sent[:600], signals=sorted(sig), categories=match_categories(sent)))
        if len(out) >= max_mentions:
            break
    return out
