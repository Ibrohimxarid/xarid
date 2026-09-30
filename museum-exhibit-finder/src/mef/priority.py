"""A / B / C prioritisation and the 8 "AI research logic" answers.

Decisions come only from evidence signals and evidence-backed exhibit
statuses — never from wording like "the museum probably wants to get rid of
it".

A — DIRECT OPPORTUNITY   availability confirmed (for sale / donation / transfer /
                          offered to other museums / deaccession in progress)
                          by evidence not older than ``availability_max_age_years``
B — POTENTIAL OPPORTUNITY old exhibits replaced / removed / stored, fate unknown
                          (or availability evidence that is stale)
C — LEAD                  renovation / new exhibition / relocation / published
                          deaccession programme only
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from . import POTENTIAL_LEAD, UNKNOWN
from .config import settings
from .evidence import (
    age_years,
    exhibit_evidence,
    parse_date,
    primary_source,
    signals_of,
    unattached_evidence,
)
from .models import (
    AVAILABILITY_SIGNALS,
    EVENT_SIGNALS,
    REMOVAL_SIGNALS,
    STATUS_LABELS,
    Evidence,
    Exhibit,
    MuseumFile,
)

AVAILABLE_STATUSES = {"for_sale", "available_donation", "available_transfer", "deaccessioned"}
REMOVED_STATUSES = {"already_replaced", "in_storage", "being_replaced"}
GONE_STATUSES = {"already_transferred"}
# Sources that alone cannot confirm availability (brief: confirm social-media finds officially).
UNCONFIRMED_SOURCES = {"social_media", "forum"}
RANK = {"A": 3, "B": 2, "C": 1, None: 0}


@dataclass
class Assessment:
    priority: str | None
    stage: int
    availability: str
    availability_evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _expired(e: Evidence, today: dt.date | None) -> bool:
    deadline = parse_date(e.valid_until)
    return deadline is not None and deadline < (today or dt.date.today())


def _fresh(evs: list[Evidence], today: dt.date | None) -> tuple[list[Evidence], list[Evidence]]:
    """Split availability evidence into still-valid and stale (too old or offer window closed)."""
    max_age = settings().availability_max_age_years
    fresh, stale = [], []
    for e in evs:
        age = age_years(e, today)
        too_old = age is not None and age > max_age
        (stale if too_old or _expired(e, today) else fresh).append(e)
    return fresh, stale


def _assess(evs: list[Evidence], status: str | None, today: dt.date | None) -> Assessment:
    sig = signals_of(evs)
    avail_evs = [e for e in evs if set(e.signals) & AVAILABILITY_SIGNALS]
    notes: list[str] = []

    if status in GONE_STATUSES:
        return Assessment(None, 4, "No — already transferred/sold to another party.", [], notes)

    if avail_evs or status in AVAILABLE_STATUSES:
        fresh, stale = _fresh(avail_evs, today)
        if fresh and all(e.source_type in UNCONFIRMED_SOURCES for e in fresh):
            notes.append("Availability reported only on social media / forums — confirm on an "
                         "official source before treating as a direct opportunity.")
            return Assessment("B", 4, "Reported but not confirmed by an official source.", fresh, notes)
        if fresh:
            undated = [e for e in fresh if not e.source_date]
            if undated:
                notes.append("Availability source is undated — confirm the offer is still open.")
            return Assessment(
                "A", 5, "Yes — availability confirmed by source (see evidence).", fresh, notes
            )
        if stale:
            closed = [e for e in stale if _expired(e, today)]
            if closed:
                last = max(e.valid_until or "" for e in closed)
                notes.append(f"Offer window closed on {last} — ask whether the item is still available.")
            else:
                newest = max((e.source_date or "") for e in stale)
                notes.append(f"Availability evidence dated {newest} is older than "
                             f"{settings().availability_max_age_years} years — re-confirm.")
            return Assessment("B", 4, "Stale — was available per source; re-confirm.", stale, notes)
        # status claims availability but no availability-signal evidence: treat as removed
        notes.append("Status says available but no evidence carries an availability signal.")

    if sig & REMOVAL_SIGNALS or status in REMOVED_STATUSES or "deaccession_in_progress" in sig:
        stage = 4 if sig & {"storage", "deaccession_in_progress"} or status == "in_storage" else 3
        return Assessment("B", stage, POTENTIAL_LEAD, [], notes)
    if sig & (EVENT_SIGNALS | {"touring_for_hire", "deaccession_policy"}) or status == "still_in_use":
        return Assessment("C", 2, POTENTIAL_LEAD, [], notes)
    return Assessment(None, 1, UNKNOWN, [], notes)


def assess_exhibit(mf: MuseumFile, exhibit: Exhibit, today: dt.date | None = None) -> Assessment:
    evs = exhibit_evidence(mf, exhibit)
    return _assess(evs, exhibit.status, today)


def assess_museum(mf: MuseumFile, today: dt.date | None = None) -> Assessment:
    best = _assess(unattached_evidence(mf), None, today)
    for ex in mf.exhibitions:
        ex_evs = [e for e in mf.evidence if e.id in ex.evidence]
        cand = _assess(ex_evs, ex.status, today)
        if RANK[cand.priority] > RANK[best.priority]:
            best = cand
        for item in ex.exhibits:
            cand = assess_exhibit(mf, item, today)
            if RANK[cand.priority] > RANK[best.priority]:
                best = cand
    return best


def research_answers(mf: MuseumFile, today: dt.date | None = None) -> dict[str, str]:
    """The 8 questions from the brief, answered only from stored evidence."""
    a = assess_museum(mf, today)
    sig = signals_of(mf.evidence)

    def cite(evs: list[Evidence]) -> str:
        return ", ".join(f"[{e.id}]" for e in evs) or "—"

    event_evs = [e for e in mf.evidence if set(e.signals) & (EVENT_SIGNALS | {"exhibit_replaced"})]
    removal_evs = [e for e in mf.evidence if set(e.signals) & REMOVAL_SIGNALS]
    statuses = sorted({STATUS_LABELS[i.status] for ex in mf.exhibitions for i in ex.exhibits if i.status != "unknown"}
                      | {STATUS_LABELS[ex.status] for ex in mf.exhibitions if ex.status != "unknown"})
    fate_sig = sig & {"storage", "deaccession_in_progress", "already_transferred", "destroyed",
                      "for_sale", "for_donation", "available_transfer"}
    contacts = [c for c in mf.contacts if c.email or c.phone or c.contact_page]
    src = primary_source(mf.evidence)

    return {
        "1. Is this a museum?": f"Yes — {mf.museum.type}.",
        "2. Evidence of exhibition replacement?": (
            f"Yes {cite(event_evs)}" if event_evs else "No evidence found yet."
        ),
        "3. Was an old exhibit removed?": (
            f"Yes {cite(removal_evs)}" if removal_evs or statuses else "Not confirmed."
        ),
        "4. What happened to it?": (
            "; ".join(statuses) if statuses else (", ".join(sorted(fate_sig)) if fate_sig else UNKNOWN)
        ),
        "5. Is the exhibit potentially available?": (
            a.availability + (f" {cite(a.availability_evidence)}" if a.availability_evidence else "")
        ),
        "6. Evidence supporting this?": cite(mf.evidence),
        "7. Who should TPM contact?": (
            "; ".join(
                " ".join(x for x in [c.name, f"({c.position})" if c.position else None,
                                     c.email, c.phone, c.contact_page] if x)
                for c in contacts[:3]
            )
            if contacts
            else UNKNOWN
        ),
        "8. What is the original source?": src.url if src else UNKNOWN,
    }
