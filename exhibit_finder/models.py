"""Candidate record: one potential exhibit, as found by research."""

from dataclasses import dataclass, field, fields, asdict

# Factual status vocabulary for the object itself.
EXHIBIT_STATUSES = (
    "ON_DISPLAY",      # still in the gallery -- not available
    "SCHEDULED_FOR_REPLACEMENT",
    "RETIRED",         # taken off display
    "REPLACED",        # removed because a newer exhibit replaced it
    "IN_STORAGE",
    "DEACCESSIONED",
    "FOR_TRANSFER",    # offered to other institutions
    "FOR_DONATION",
    "FOR_SALE",
    "SOLD",            # gone
    "SCRAPPED",        # gone
    "UNKNOWN",
)
OFFERED_STATUSES = {"FOR_TRANSFER", "FOR_DONATION", "FOR_SALE"}
RETIRED_STATUSES = {"RETIRED", "REPLACED", "IN_STORAGE", "DEACCESSIONED"} | OFFERED_STATUSES
GONE_STATUSES = {"ON_DISPLAY", "SOLD", "SCRAPPED"}

SOURCE_TYPES = ("science_centre", "technology_museum", "transport_museum", "automotive_museum",
                "other_museum", "university", "company", "exhibit_manufacturer", "other")
MUSEUM_SOURCE_TYPES = {"science_centre", "technology_museum", "transport_museum", "automotive_museum",
                       "other_museum"}

CONDITIONS = ("working", "complete", "needs_repair", "parts_missing", "unusable", "unknown")

EVIDENCE_TYPES = ("official_museum_document", "museum_website", "direct_correspondence", "press",
                  "auction_listing", "marketplace_listing", "other")


@dataclass
class Candidate:
    # What it is
    id: str
    title: str
    description: str = ""
    object_type: str = ""          # e.g. "interactive exhibit", "engine cutaway", "book" -- the head noun
    tags: list = field(default_factory=list)

    # Where it is
    source_institution: str = ""
    source_type: str = "other"     # one of SOURCE_TYPES
    country: str = ""
    city: str = ""

    # History and status
    history: str = ""              # e.g. "Installed 2012; replaced 2026 during gallery renovation"
    exhibit_status: str = "UNKNOWN"
    status_date: str = ""          # ISO date the status was observed / stated
    evidence_url: str = ""
    evidence_type: str = ""        # one of EVIDENCE_TYPES

    # Exhibit facts
    condition: str = "unknown"     # one of CONDITIONS
    dimensions: str = ""
    weight_kg: float = None
    photos_available: bool = None
    documentation_available: bool = None

    # Contact and transfer
    contact_name: str = ""
    contact_role: str = ""
    contact_email: str = ""
    international_transfer: str = "unknown"  # "yes" | "no" | "unknown"

    # Acquisition criteria that research must state explicitly (None = not established)
    is_museum_exhibit: bool = None
    logistics_reasonable: bool = None
    availability_confirmed: bool = None

    # Optional researcher-written justification; validated, never trusted blindly.
    why_it_fits: str = ""

    @classmethod
    def from_dict(cls, data):
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"candidate {data.get('id', '?')}: unknown field(s) {sorted(unknown)}")
        return cls(**data)

    def to_dict(self):
        return asdict(self)
