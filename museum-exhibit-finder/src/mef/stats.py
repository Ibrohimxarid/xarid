"""Research statistics (section 6 of the final report)."""

from __future__ import annotations

from .models import EVENT_SIGNALS, MuseumFile
from .priority import assess_exhibit, assess_museum

REPLACED_STATUSES = {"already_replaced", "in_storage", "being_replaced", "already_transferred"}


def compute_stats(files: list[MuseumFile]) -> dict[str, int]:
    museums = len(files)
    renovation = sum(
        1 for mf in files if any(set(e.signals) & (EVENT_SIGNALS | {"exhibit_replaced", "closure"}) for e in mf.evidence)
    )
    exhibitions_replaced = 0
    for mf in files:
        by_id = mf.evidence_by_id()
        for ex in mf.exhibitions:
            sig = {s for i in ex.evidence if i in by_id for s in by_id[i].signals}
            if ex.status in REPLACED_STATUSES or sig & {"exhibit_replaced", "closure"}:
                exhibitions_replaced += 1
    exhibits = [(mf, i) for mf in files for ex in mf.exhibitions for i in ex.exhibits]
    confirmed = sum(1 for mf, i in exhibits if assess_exhibit(mf, i).priority == "A")
    assessed = [assess_museum(mf) for mf in files]
    prio = [a.priority for a in assessed]
    b_offered = sum(1 for a in assessed if a.priority == "B" and a.availability_evidence)
    contacts = sum(1 for mf in files for c in mf.contacts if c.email or c.phone or c.contact_page)
    museums_with_contact = sum(1 for mf in files if any(c.email or c.phone or c.contact_page for c in mf.contacts))
    return {
        "Museums researched": museums,
        "Museums with renovation / replacement / closure projects": renovation,
        "Exhibitions replaced (tracked)": exhibitions_replaced,
        "Old exhibits identified": len(exhibits),
        "Exhibits confirmed available (A)": confirmed,
        "Museums — A (documented current offer: giving away / selling / transferring)": prio.count("A"),
        "Museums — B, offered earlier (window closed / stale / not officially confirmed)": b_offered,
        "Museums — B, removed or stored, fate unknown (no offer found)": prio.count("B") - b_offered,
        "Museums — C (lead: renovation / new exhibition only)": prio.count("C"),
        "Contacts found": contacts,
        "Museums with a contact": museums_with_contact,
        "Evidence records (sources)": sum(len(mf.evidence) for mf in files),
        "Countries covered": len({mf.museum.country for mf in files}),
    }
