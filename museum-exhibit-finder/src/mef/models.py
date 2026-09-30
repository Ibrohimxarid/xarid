"""Pydantic models for the research knowledge base.

One YAML file in ``research/museums/`` = one :class:`MuseumFile`:

    museum → exhibitions → exhibits
           → evidence (every claim points at a source URL)
           → contacts
           → research (next step, outreach status)

``extra="forbid"`` everywhere so a typo in a research file fails loudly
instead of silently dropping data.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Signal(str, Enum):
    """Event-chain signals an evidence record can support."""

    # Stage 1 — something is changing at the museum
    renovation = "renovation"
    new_exhibition = "new_exhibition"
    relocation = "relocation"
    # Stage 2 — old exhibition / exhibits taken out
    exhibit_replaced = "exhibit_replaced"
    closure = "closure"
    # Stage 3 — fate of the old exhibits is known
    storage = "storage"
    deaccession_policy = "deaccession_policy"
    deaccession_in_progress = "deaccession_in_progress"
    already_transferred = "already_transferred"
    destroyed = "destroyed"
    # Stage 4 — availability
    for_sale = "for_sale"
    for_donation = "for_donation"
    available_transfer = "available_transfer"
    willing_transfer = "willing_transfer"
    willing_sale = "willing_sale"
    accepts_requests = "accepts_requests"
    touring_for_hire = "touring_for_hire"
    international_ok = "international_ok"
    # Stage 5 — contact
    contact = "contact"


AVAILABILITY_SIGNALS = {
    Signal.for_sale.value,
    Signal.for_donation.value,
    Signal.available_transfer.value,
    Signal.willing_transfer.value,
    Signal.willing_sale.value,
    Signal.deaccession_in_progress.value,
}
REMOVAL_SIGNALS = {
    Signal.exhibit_replaced.value,
    Signal.closure.value,
    Signal.storage.value,
}
EVENT_SIGNALS = {
    Signal.renovation.value,
    Signal.new_exhibition.value,
    Signal.relocation.value,
}


class ExhibitStatus(str, Enum):
    still_in_use = "still_in_use"
    being_replaced = "being_replaced"
    already_replaced = "already_replaced"
    in_storage = "in_storage"
    deaccessioned = "deaccessioned"
    for_sale = "for_sale"
    available_donation = "available_donation"
    available_transfer = "available_transfer"
    already_transferred = "already_transferred"  # went to someone else — not available
    unknown = "unknown"


STATUS_LABELS = {
    "still_in_use": "Still in use",
    "being_replaced": "Being replaced",
    "already_replaced": "Already replaced",
    "in_storage": "In storage",
    "deaccessioned": "Deaccessioned",
    "for_sale": "For sale",
    "available_donation": "Available for donation",
    "available_transfer": "Available for transfer",
    "already_transferred": "Already transferred/sold to another party",
    "unknown": "Unknown",
}


class SourceType(str, Enum):
    official_site = "official_site"
    press_release = "press_release"
    annual_report = "annual_report"
    board_document = "board_document"
    procurement = "procurement"
    government = "government"
    association = "association"
    news = "news"
    trade_press = "trade_press"
    social_media = "social_media"
    forum = "forum"
    archive = "archive"
    collection_database = "collection_database"
    other = "other"


class VerifiedVia(str, Enum):
    web_fetch = "web_fetch"  # page itself was read
    web_search_snippet = "web_search_snippet"  # only a search-result summary was seen
    pipeline = "pipeline"  # fetched + parsed by mef.collector/parser
    llm = "llm"  # extracted by mef.llm with verbatim-quote check
    manual = "manual"  # checked by a person


class OutreachStatus(str, Enum):
    not_contacted = "not_contacted"
    research_more = "research_more"
    draft_ready = "draft_ready"
    contacted = "contacted"
    replied = "replied"
    negotiating = "negotiating"
    closed_unavailable = "closed_unavailable"
    acquired = "acquired"


_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


class Evidence(Strict):
    id: str
    url: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    source_type: SourceType = SourceType.other
    source_date: Optional[str] = Field(
        None, description="Publication date of the source: YYYY, YYYY-MM or YYYY-MM-DD"
    )
    accessed: str = Field(..., description="Date the source was read: YYYY-MM-DD")
    valid_until: Optional[str] = Field(
        None, description="Deadline/expiry of the offer stated by the source (YYYY[-MM[-DD]])"
    )
    language: Optional[str] = None
    claim: str = Field(..., description="What this source supports, in plain English")
    excerpt: Optional[str] = Field(None, description="Quote or close paraphrase from the source")
    excerpt_is_verbatim: bool = False
    signals: list[Signal] = Field(default_factory=list)
    verified_via: VerifiedVia = VerifiedVia.web_search_snippet
    notes: Optional[str] = None

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError(f"evidence url must be absolute http(s): {v!r}")
        return v.strip()

    @field_validator("source_date", "accessed", "valid_until")
    @classmethod
    def _date(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = str(v).strip()
        if not _DATE_RE.match(v):
            raise ValueError(f"date must be YYYY, YYYY-MM or YYYY-MM-DD: {v!r}")
        return v


class Contact(Strict):
    name: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    contact_page: Optional[str] = None
    kind: str = Field("general", description="person | general | department")
    source: str = Field(..., description="Evidence id or URL where this contact was published")

    @field_validator("email")
    @classmethod
    def _email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError(f"not an email address: {v!r}")
        return v


class Museum(Strict):
    id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    name_local: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    country: str
    city: Optional[str] = None
    website: Optional[str] = None
    type: str = Field(..., description="e.g. science centre, technology museum, transport museum")
    parent_org: Optional[str] = None
    general_email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None


class Exhibit(Strict):
    id: str
    name: str
    description: Optional[str] = None
    category: list[str] = Field(default_factory=list)
    manufacturer: Optional[str] = None
    year: Optional[str] = Field(None, description="Year built / installed, if known")
    approx_age: Optional[str] = None
    dimensions: Optional[str] = None
    weight: Optional[str] = None
    interactive: Optional[bool] = None
    condition: Optional[str] = None
    educational_purpose: Optional[str] = None
    quantity: Optional[str] = None
    photos: list[str] = Field(default_factory=list)
    video: list[str] = Field(default_factory=list)
    documentation: list[str] = Field(default_factory=list)
    status: ExhibitStatus = ExhibitStatus.unknown
    evidence: list[str] = Field(default_factory=list)
    fit_for_tpm: Optional[str] = Field(
        None, description="Why this could suit Tashkent Polytechnic Museum"
    )
    notes: Optional[str] = None

    @field_validator("year", "approx_age", "dimensions", "weight", mode="before")
    @classmethod
    def _str(cls, v):
        return None if v is None else str(v)


class Exhibition(Strict):
    id: str
    name: str
    gallery: Optional[str] = None
    opening_year: Optional[str] = None
    replacement_year: Optional[str] = None
    new_exhibition: Optional[str] = None
    old_exhibition: Optional[str] = None
    status: ExhibitStatus = ExhibitStatus.unknown
    evidence: list[str] = Field(default_factory=list)
    exhibits: list[Exhibit] = Field(default_factory=list)
    notes: Optional[str] = None

    @field_validator("opening_year", "replacement_year", mode="before")
    @classmethod
    def _str(cls, v):
        return None if v is None else str(v)


class Outreach(Strict):
    reason: Optional[str] = Field(None, description="Why contact this museum (fact-based)")
    interest: Optional[str] = Field(None, description="Which exhibits interest TPM")
    fit: Optional[str] = Field(None, description="Why they could suit Tashkent Polytechnic Museum")
    email_hook: Optional[str] = Field(
        None,
        description="Sentence completing 'We understand from <source> that …' — facts only",
    )
    source: Optional[str] = Field(None, description="Evidence id the e-mail hook is based on")


class Research(Strict):
    researcher: str = "mef"
    last_updated: str
    outreach_status: OutreachStatus = OutreachStatus.not_contacted
    next_step: Optional[str] = None
    open_questions: list[str] = Field(default_factory=list)
    eligibility: Optional[str] = Field(
        None, description="Who may receive the objects, as stated by the source (e.g. UK public bodies first)"
    )
    outreach: Outreach = Field(default_factory=Outreach)
    notes: Optional[str] = None


class MuseumFile(Strict):
    museum: Museum
    contacts: list[Contact] = Field(default_factory=list)
    exhibitions: list[Exhibition] = Field(default_factory=list)
    evidence: list[Evidence]
    research: Research

    @model_validator(mode="after")
    def _references(self) -> "MuseumFile":
        ids = [e.id for e in self.evidence]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"{self.museum.id}: duplicate evidence ids {sorted(dup)}")
        if not ids:
            raise ValueError(f"{self.museum.id}: at least one evidence record is required")
        known = set(ids)
        for ex in self.exhibitions:
            for ref in ex.evidence:
                if ref not in known:
                    raise ValueError(f"{self.museum.id}/{ex.id}: unknown evidence id {ref!r}")
            for item in ex.exhibits:
                for ref in item.evidence:
                    if ref not in known:
                        raise ValueError(
                            f"{self.museum.id}/{ex.id}/{item.id}: unknown evidence id {ref!r}"
                        )
                if item.status != ExhibitStatus.unknown.value and not item.evidence:
                    raise ValueError(
                        f"{self.museum.id}/{ex.id}/{item.id}: status {item.status!r} needs evidence"
                    )
        for c in self.contacts:
            if not c.source.startswith("http") and c.source not in known:
                raise ValueError(f"{self.museum.id}: contact source {c.source!r} not found")
        return self

    def evidence_by_id(self) -> dict[str, Evidence]:
        return {e.id: e for e in self.evidence}


# ---- discovery-side records -------------------------------------------------


class SearchResult(Strict):
    query: str
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    engine: str = "unknown"
    rank: Optional[int] = None
    lang: Optional[str] = None
    retrieved: Optional[str] = None


class Classification(Strict):
    """Output of the relevance classifier for one page/snippet."""

    url: str
    is_museum: bool
    museum_score: float
    commercial: bool
    signals: dict[str, list[str]] = Field(
        default_factory=dict, description="signal -> matched phrases"
    )
    categories: list[str] = Field(default_factory=list)
    stage: int = 0
    priority: Optional[str] = None
    relevance: float = 0.0
    summary: str = ""
