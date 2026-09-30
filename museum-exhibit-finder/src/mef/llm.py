"""Optional LLM page assessment with the Claude API.

Used only for pages the rule-based classifier already marked as candidates.
Claude answers the 8 research-logic questions in a strict JSON schema
(structured outputs). Every quote it returns is then checked for a verbatim
match in the page text; unverifiable quotes — and any signal that rests only
on them — are dropped. The model is told to answer "not confirmed" rather than
infer availability.

Requires ``pip install anthropic`` and credentials (ANTHROPIC_API_KEY or an
``ant auth login`` profile). Enable with ``llm.enabled: true`` or ``--llm``.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from .config import settings

SignalName = Literal[
    "renovation", "new_exhibition", "relocation", "exhibit_replaced", "closure", "storage",
    "deaccession_policy", "deaccession_in_progress", "already_transferred", "destroyed",
    "for_sale", "for_donation", "available_transfer", "willing_transfer", "willing_sale",
    "accepts_requests", "touring_for_hire", "international_ok", "contact",
]


class Quote(BaseModel):
    quote: str = Field(description="Exact sentence copied verbatim from the page")
    signals: list[SignalName]


class PageAssessment(BaseModel):
    is_museum: bool
    museum_name: str | None
    country: str | None
    city: str | None
    exhibition_replacement: bool
    old_exhibit_removed: bool
    old_exhibits: list[str]
    fate: Literal[
        "still_in_use", "being_replaced", "already_replaced", "in_storage", "deaccessioned",
        "for_sale", "available_donation", "available_transfer", "already_transferred", "unknown",
    ]
    availability: Literal["confirmed", "not_confirmed", "not_available"]
    contacts: list[str]
    quotes: list[Quote]
    summary: str


SYSTEM = """You assess web pages for Tashkent Polytechnic Museum (Uzbekistan), which is looking \
for exhibits that other museums, science centres and technology/transport museums have retired \
because of renovations or new galleries, and that might be transferred, donated or sold.

Answer strictly from the page text. Rules:
- Quote sentences verbatim; never paraphrase inside `quotes`.
- availability = "confirmed" only if the page explicitly says exhibits/objects are for sale, \
for donation, offered to other institutions, looking for a new home, or in a deaccession/disposal \
process. Otherwise "not_confirmed" (or "not_available" if they went elsewhere / were destroyed).
- Never infer that a museum "probably wants to get rid of" something.
- Only list contacts (names, roles, e-mails, phones) that literally appear on the page.
- Commercial companies selling newly built exhibits are not museums."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_quotes(assessment: PageAssessment, text: str) -> tuple[list[Quote], list[Quote]]:
    hay = _norm(text)
    ok, bad = [], []
    for q in assessment.quotes:
        (ok if _norm(q.quote) and _norm(q.quote) in hay else bad).append(q)
    return ok, bad


def assess_page(url: str, text: str) -> dict | None:
    """Return a verified assessment dict, or None if the model declined."""
    import anthropic

    cfg = settings().llm
    client = anthropic.Anthropic()
    page = text[: int(cfg.get("max_page_chars", 60000))]
    response = client.messages.parse(
        model=cfg.get("model", "claude-opus-5-5"),
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": cfg.get("effort", "medium")},
        system=SYSTEM,
        messages=[{"role": "user", "content": f"URL: {url}\n\n<page>\n{page}\n</page>"}],
        output_format=PageAssessment,
        # Server-side fallback: a declined request is re-run on Anthropic's recommended model.
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    result: PageAssessment = response.parsed_output
    ok, bad = verify_quotes(result, page)
    verified_signals = sorted({s for q in ok for s in q.signals})
    data = result.model_dump()
    data["quotes"] = [q.model_dump() for q in ok]
    data["rejected_quotes"] = [q.model_dump() for q in bad]
    data["verified_signals"] = verified_signals
    if data["availability"] == "confirmed" and not set(verified_signals) & {
        "for_sale", "for_donation", "available_transfer", "willing_transfer", "willing_sale",
        "deaccession_in_progress",
    }:
        data["availability"] = "not_confirmed"
        data["summary"] += " [availability downgraded: no verified quote supports it]"
    return data
