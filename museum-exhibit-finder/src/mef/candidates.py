"""Candidate list for TPM: relevance-checked, acquisition-prioritised.

Builds three lists from the knowledge base:

* ``candidates`` — objects (or galleries) that passed the relevance check
  (DIRECT / STRONG / RELATED / WEAK) and for which a source shows they were
  removed, retired or offered. Ordered HIGH → MEDIUM → LOW, then by relevance.
* ``channels``   — documented give-away / transfer programmes whose item
  lists were not captured: places to ask for the list.
* ``rejected``   — objects that are offered but fail the relevance check
  (books, furniture, decorative ...). Shown only as "do not recommend".

Renovation-only museums (no removal or offer evidence) are not candidates.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .evidence import parse_date
from .models import AVAILABILITY_SIGNALS, REMOVAL_SIGNALS, STATUS_LABELS, Evidence, Exhibit, Exhibition, MuseumFile
from .priority import Assessment, _assess, _fresh, assess_exhibit
from .relevance import (
    PRIORITY_ORDER,
    RELEVANCE_ORDER,
    Acquisition,
    area_labels,
    assess_acquisition,
    ideal_target_flags,
    newest_date,
    profile_areas,
    why_it_fits_problems,
)
from .rows import ranked_contacts


@dataclass
class Candidate:
    museum: MuseumFile
    exhibition: Exhibition
    exhibit: Exhibit | None
    assessment: Assessment
    acquisition: Acquisition
    evidence: list[Evidence]

    @property
    def obj(self) -> Exhibit | Exhibition:
        return self.exhibit or self.exhibition

    @property
    def label(self) -> str:
        if self.exhibit:
            return self.exhibit.name
        ex = self.exhibition
        return f"Retired exhibits: {ex.old_exhibition}" if ex.old_exhibition else ex.name

    @property
    def kind(self) -> str:
        return "object" if self.exhibit else "gallery (objects not itemised)"

    @property
    def why_it_fits(self) -> str:
        return self.obj.fit_for_tpm or ""

    @property
    def why_problems(self) -> list[str]:
        return why_it_fits_problems(self.obj.fit_for_tpm)

    @property
    def areas(self) -> str:
        return area_labels(profile_areas(self.obj.category))

    @property
    def offered(self) -> bool:
        return bool(self.assessment.availability_evidence)

    def offer_evidence(self) -> list[Evidence]:
        return list(self.assessment.availability_evidence)

    def removal_evidence(self) -> list[Evidence]:
        return [e for e in self.evidence if set(e.signals) & (REMOVAL_SIGNALS | {"deaccession_in_progress"})
                and e not in self.assessment.availability_evidence]

    def history(self) -> str:
        ex, it = self.exhibition, self.exhibit
        parts = []
        installed = (it.year if it else None) or ex.opening_year
        if installed:
            parts.append(f"installed / made {installed}")
        if ex.replacement_year:
            parts.append(f"removed / replaced {ex.replacement_year}")
        if ex.new_exhibition:
            parts.append(f"replaced by: {ex.new_exhibition}")
        status = it.status if it else ex.status
        parts.append(f"status: {STATUS_LABELS.get(status, status)}")
        return "; ".join(parts)

    def contacts(self) -> list:
        return ranked_contacts(self.museum)

    def ideal(self) -> dict[str, str]:
        return ideal_target_flags(self.museum, self.obj)


@dataclass
class Channel:
    museum: MuseumFile
    programme: str
    offer_evidence: list[Evidence] = field(default_factory=list)
    items: list[str] = field(default_factory=list)


def _objects(mf: MuseumFile, today: dt.date):
    by_id = mf.evidence_by_id()
    for ex in mf.exhibitions:
        if ex.exhibits:
            for it in ex.exhibits:
                evs = [by_id[i] for i in dict.fromkeys(list(it.evidence) + list(ex.evidence)) if i in by_id]
                yield ex, it, assess_exhibit(mf, it, today), evs
        else:
            evs = [by_id[i] for i in ex.evidence if i in by_id]
            yield ex, None, _assess(evs, ex.status, today), evs


def build(files: list[MuseumFile], today: dt.date | None = None):
    today = today or dt.date.today()
    candidates: list[Candidate] = []
    rejected: list[Candidate] = []
    channels: dict[str, Channel] = {}

    for mf in files:
        for ex, it, a, evs in _objects(mf, today):
            obj = it or ex
            acq = assess_acquisition(mf, obj, a, today)
            cand = Candidate(mf, ex, it, a, acq, evs)
            removed_or_offered = a.priority in ("A", "B")
            if acq.relevance is None:
                if a.availability_evidence:
                    ch = channels.setdefault(mf.museum.id, Channel(mf, mf.research.transfer_programme or ""))
                    ch.items.append(cand.label)
                    ch.offer_evidence += [e for e in a.availability_evidence if e not in ch.offer_evidence]
                continue
            if acq.relevance.value == "NOT_RELEVANT":
                if a.availability_evidence:  # offered, but not for TPM
                    rejected.append(cand)
                continue
            if removed_or_offered:
                candidates.append(cand)
        if mf.research.transfer_programme and mf.museum.id not in channels:
            avail = [e for e in mf.evidence if set(e.signals) & AVAILABILITY_SIGNALS]
            fresh, _ = _fresh(avail, today)
            channels[mf.museum.id] = Channel(mf, mf.research.transfer_programme, fresh or avail)
        elif mf.museum.id in channels and mf.research.transfer_programme:
            channels[mf.museum.id].programme = mf.research.transfer_programme

    def key(c: Candidate):
        return (
            PRIORITY_ORDER[c.acquisition.priority],
            RELEVANCE_ORDER[c.acquisition.relevance],
            not c.offered,
            -newest_date(c.assessment).toordinal(),
            c.museum.museum.name,
        )

    candidates.sort(key=key)
    rejected.sort(key=lambda c: c.museum.museum.name)
    chans = sorted(channels.values(), key=lambda ch: (
        not ch.offer_evidence,
        -max((parse_date(e.source_date) or dt.date.min for e in ch.offer_evidence), default=dt.date.min).toordinal(),
        ch.museum.museum.name,
    ))
    return candidates, chans, rejected
