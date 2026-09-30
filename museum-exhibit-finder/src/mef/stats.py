"""Research statistics (section 6 of the final report)."""

from __future__ import annotations

from .models import EVENT_SIGNALS, MuseumFile
from .priority import assess_exhibit, assess_museum

REMOVED_OR_BEYOND = {
    "already_replaced", "in_storage", "deaccessioned", "for_sale", "available_donation",
    "available_transfer", "already_transferred", "being_replaced",
}


def compute_stats(files: list[MuseumFile]) -> dict[str, int]:
    museums = len(files)
    renovation = sum(
        1 for mf in files if any(set(e.signals) & (EVENT_SIGNALS | {"exhibit_replaced", "closure"}) for e in mf.evidence)
    )
    exhibitions_replaced = sum(
        1
        for mf in files
        for ex in mf.exhibitions
        if ex.status in REMOVED_OR_BEYOND or ex.replacement_year or ex.new_exhibition
    )
    exhibits = [(mf, i) for mf in files for ex in mf.exhibitions for i in ex.exhibits]
    confirmed = sum(1 for mf, i in exhibits if assess_exhibit(mf, i).priority == "A")
    prio = [assess_museum(mf).priority for mf in files]
    contacts = sum(1 for mf in files for c in mf.contacts if c.email or c.phone or c.contact_page)
    museums_with_contact = sum(1 for mf in files if any(c.email or c.phone or c.contact_page for c in mf.contacts))
    return {
        "Museums researched": museums,
        "Museums with renovation / replacement / closure projects": renovation,
        "Exhibitions replaced (tracked)": exhibitions_replaced,
        "Old exhibits identified": len(exhibits),
        "Exhibits confirmed available (A)": confirmed,
        "Museums — A (direct opportunity)": prio.count("A"),
        "Museums — B (potential opportunity)": prio.count("B"),
        "Museums — C (lead)": prio.count("C"),
        "Potential opportunities (A+B museums)": prio.count("A") + prio.count("B"),
        "Contacts found": contacts,
        "Museums with a contact": museums_with_contact,
        "Evidence records (sources)": sum(len(mf.evidence) for mf in files),
        "Countries covered": len({mf.museum.country for mf in files}),
    }
