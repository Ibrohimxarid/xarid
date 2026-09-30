"""Flatten the knowledge base into rows shared by the exporter and the report."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import POTENTIAL_LEAD, UNKNOWN
from .evidence import primary_source, signals_of
from .models import STATUS_LABELS, Evidence, Exhibit, Exhibition, MuseumFile
from .priority import Assessment, assess_exhibit, assess_museum, _assess

DATABASE_FIELDS = [
    "Museum", "Country", "City", "Website", "Museum Type", "Exhibition", "Old Exhibit",
    "Exhibit Category", "Manufacturer", "Year", "Replacement Year", "Current Status",
    "Availability Evidence", "Source", "Source Date", "Contact Name", "Contact Position",
    "Email", "Phone", "LinkedIn", "Photo", "Video", "Acquisition Potential", "Priority",
    "Notes", "Outreach Status",
    # extra columns (after the required minimum set)
    "Museum ID", "Exhibit ID", "Description", "Interactive", "Dimensions", "Weight",
    "Condition", "Fit for TPM", "Evidence IDs", "Next Step",
]


def _or_unknown(v) -> str:
    if v is None or v == "" or v == []:
        return UNKNOWN
    return str(v)


def acquisition_flags(evs: list[Evidence], mf: MuseumFile) -> str:
    def flag(signals: set[str]) -> str:
        hits = [e.id for e in evs if set(e.signals) & signals]
        return f"yes [{', '.join(hits)}]" if hits else "unknown"

    contact = "yes" if any(c.email or c.phone or c.contact_page for c in mf.contacts) else "no"
    return "; ".join(
        [
            f"available: {flag({'for_sale', 'for_donation', 'available_transfer', 'deaccession_in_progress'})}",
            f"willing to transfer: {flag({'willing_transfer', 'available_transfer', 'for_donation'})}",
            f"willing to sell: {flag({'willing_sale', 'for_sale'})}",
            f"accepts requests: {flag({'accepts_requests'})}",
            f"contact identified: {contact}",
            f"international transfer: {flag({'international_ok'})}",
        ]
    )


_KIND_RANK = {"person": 0, "department": 1, "general": 2}


def ranked_contacts(mf: MuseumFile) -> list:
    """Reachable contacts, people first, then departments, then general lines."""
    usable = [c for c in mf.contacts if c.email or c.phone or c.linkedin or c.contact_page]
    return sorted(usable, key=lambda c: _KIND_RANK.get(c.kind, 3))


def best_contact(mf: MuseumFile):
    ranked = ranked_contacts(mf)
    return ranked[0] if ranked else None


def best_email_contact(mf: MuseumFile):
    """The contact an e-mail should go to: the highest-ranked one with an address."""
    return next((c for c in ranked_contacts(mf) if c.email), None)


@dataclass
class Row:
    museum: MuseumFile
    exhibition: Exhibition | None
    exhibit: Exhibit | None
    assessment: Assessment
    evidence: list[Evidence]

    @property
    def priority(self) -> str | None:
        return self.assessment.priority


def iter_rows(files: list[MuseumFile], today: dt.date | None = None) -> list[Row]:
    rows: list[Row] = []
    for mf in files:
        by_id = mf.evidence_by_id()
        if not mf.exhibitions:
            rows.append(Row(mf, None, None, assess_museum(mf, today), list(mf.evidence)))
            continue
        for ex in mf.exhibitions:
            ex_evs = [by_id[i] for i in ex.evidence if i in by_id]
            if not ex.exhibits:
                evs = ex_evs or list(mf.evidence)
                rows.append(Row(mf, ex, None, _assess(evs, ex.status, today), evs))
                continue
            for item in ex.exhibits:
                evs = [by_id[i] for i in item.evidence if i in by_id] or ex_evs
                a = assess_exhibit(mf, item, today)
                if a.priority is None and item.status == "unknown":
                    a = _assess(evs, ex.status, today)
                rows.append(Row(mf, ex, item, a, evs))
    return rows


def database_record(row: Row) -> dict[str, str]:
    mf, ex, item, a = row.museum, row.exhibition, row.exhibit, row.assessment
    m = mf.museum
    src = primary_source(a.availability_evidence or row.evidence) or primary_source(mf.evidence)
    contact = best_contact(mf)
    status = item.status if item else (ex.status if ex else "unknown")
    if a.availability_evidence:
        avail = " | ".join(f"[{e.id}] {e.claim} ({e.url})" for e in a.availability_evidence)
    elif a.priority in ("B", "C"):
        avail = POTENTIAL_LEAD
    else:
        avail = a.availability
    notes = " ".join(filter(None, [item.notes if item else None, ex.notes if ex and not item else None, *a.notes]))
    return {
        "Museum": m.name,
        "Country": m.country,
        "City": _or_unknown(m.city),
        "Website": _or_unknown(m.website),
        "Museum Type": m.type,
        "Exhibition": ex.name if ex else "—",
        "Old Exhibit": item.name if item else (ex.old_exhibition if ex and ex.old_exhibition else UNKNOWN),
        "Exhibit Category": ", ".join(item.category) if item and item.category else UNKNOWN,
        "Manufacturer": _or_unknown(item.manufacturer if item else None),
        "Year": _or_unknown((item.year if item else None) or (ex.opening_year if ex else None)),
        "Replacement Year": _or_unknown(ex.replacement_year if ex else None),
        "Current Status": STATUS_LABELS.get(status, status),
        "Availability Evidence": avail,
        "Source": src.url if src else UNKNOWN,
        "Source Date": _or_unknown(src.source_date if src else None),
        "Contact Name": _or_unknown(contact.name if contact else None),
        "Contact Position": _or_unknown(contact.position if contact else None),
        "Email": _or_unknown((contact.email if contact else None) or m.general_email),
        "Phone": _or_unknown((contact.phone if contact else None) or m.phone),
        "LinkedIn": _or_unknown((contact.linkedin if contact else None) or m.linkedin),
        "Photo": " ".join(item.photos) if item and item.photos else UNKNOWN,
        "Video": " ".join(item.video) if item and item.video else UNKNOWN,
        "Acquisition Potential": acquisition_flags(row.evidence, mf),
        "Priority": a.priority or "—",
        "Notes": notes or "",
        "Outreach Status": mf.research.outreach_status,
        "Museum ID": m.id,
        "Exhibit ID": item.id if item else "",
        "Description": _or_unknown(item.description if item else None),
        "Interactive": "" if not item or item.interactive is None else ("yes" if item.interactive else "no"),
        "Dimensions": _or_unknown(item.dimensions if item else None),
        "Weight": _or_unknown(item.weight if item else None),
        "Condition": _or_unknown(item.condition if item else None),
        "Fit for TPM": item.fit_for_tpm if item and item.fit_for_tpm else (mf.research.outreach.fit or ""),
        "Evidence IDs": ", ".join(e.id for e in row.evidence),
        "Next Step": mf.research.next_step or "",
    }


def museum_signals(mf: MuseumFile) -> set[str]:
    return signals_of(mf.evidence)


def museum_summary(mf: MuseumFile, today: dt.date | None = None) -> dict[str, str]:
    a = assess_museum(mf, today)
    ex = mf.exhibitions[0] if mf.exhibitions else None
    src = primary_source(mf.evidence)
    return {
        "priority": a.priority or "—",
        "stage": str(a.stage),
        "availability": a.availability,
        "event": (ex.new_exhibition or ex.name) if ex else UNKNOWN,
        "old": (ex.old_exhibition or UNKNOWN) if ex else UNKNOWN,
        "year": (ex.replacement_year or UNKNOWN) if ex else UNKNOWN,
        "source": src.url if src else UNKNOWN,
        "source_date": (src.source_date or "n.d.") if src else "",
    }
