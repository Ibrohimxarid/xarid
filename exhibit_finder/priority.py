"""ACQUISITION PRIORITY and IDEAL TARGET assessment.

Priority is NOT computed from availability alone. HIGH requires all five
criteria to be established as true:

  1. genuine museum exhibit      (was on display in a museum / science centre)
  2. physically reusable         (working or complete)
  3. educational value           (demonstrates a profile concept)
  4. reasonable logistics        (size, weight, dismantling, hazards)
  5. current availability confirmed (offered now, backed by evidence)

  HIGH   -- DIRECT/STRONG relevance and all five criteria true.
  MEDIUM -- DIRECT/STRONG relevance and exactly one criterion not yet established.
  LOW    -- weaker relevance, any criterion known to be false, or two or more unknowns.
"""

from dataclasses import dataclass, field

from . import models
from .relevance import DIRECT_MATCH, STRONG_MATCH

HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"
PRIORITY_ORDER = (HIGH, MEDIUM, LOW)

CRITERIA = (
    ("genuine_museum_exhibit", "genuine museum exhibit"),
    ("physically_reusable", "physically reusable"),
    ("educational_value", "educational value"),
    ("reasonable_logistics", "reasonable logistics"),
    ("availability_confirmed", "current availability confirmed"),
)


def _genuine_exhibit(c):
    if c.is_museum_exhibit is not None:
        return c.is_museum_exhibit
    if c.source_type in models.MUSEUM_SOURCE_TYPES and c.exhibit_status in models.RETIRED_STATUSES:
        return True
    return None


def _reusable(c):
    if c.condition in ("working", "complete"):
        return True
    if c.condition == "unusable":
        return False
    return None  # needs_repair / parts_missing / unknown are open questions


def _educational(rel):
    if rel.relevance == DIRECT_MATCH:
        return True
    if rel.relevance == STRONG_MATCH:
        # A Group B object teaches something when it is presented as an exhibit/demonstrator.
        return True if (rel.interactive or rel.demonstrator) else None
    return False


def _availability(c):
    if c.exhibit_status in models.GONE_STATUSES:
        return False
    if c.availability_confirmed is False:
        return False
    if c.availability_confirmed and c.evidence_url:
        return True
    if c.exhibit_status in models.OFFERED_STATUSES and c.evidence_url:
        return True
    return None  # claimed without evidence, or not stated


@dataclass
class PriorityResult:
    priority: str
    criteria: dict                     # name -> True / False / None
    unmet: list = field(default_factory=list)       # human-readable, False
    uncertain: list = field(default_factory=list)   # human-readable, None
    ideal_target: bool = False
    ideal_target_gaps: list = field(default_factory=list)


def assess(candidate, rel):
    crit = {
        "genuine_museum_exhibit": _genuine_exhibit(candidate),
        "physically_reusable": _reusable(candidate),
        "educational_value": _educational(rel),
        "reasonable_logistics": candidate.logistics_reasonable,
        "availability_confirmed": _availability(candidate),
    }
    labels = dict(CRITERIA)
    unmet = [labels[k] for k, v in crit.items() if v is False]
    uncertain = [labels[k] for k, v in crit.items() if v is None]

    if rel.relevance not in (DIRECT_MATCH, STRONG_MATCH) or unmet or len(uncertain) >= 2:
        priority = LOW
    elif len(uncertain) == 1:
        priority = MEDIUM
    else:
        priority = HIGH

    gaps = ideal_target_gaps(candidate, rel, crit)
    return PriorityResult(priority, crit, unmet, uncertain, not gaps, gaps)


def ideal_target_gaps(c, rel, crit):
    """OLD MUSEUM EXHIBIT + RETIRED + AVAILABLE + DIRECT_MATCH + PHOTOS/DOCS + CONTACT + INTERNATIONAL TRANSFER."""
    gaps = []
    if crit["genuine_museum_exhibit"] is not True:
        gaps.append("not established as an old museum exhibit")
    if c.exhibit_status not in models.RETIRED_STATUSES:
        gaps.append("not established as replaced/retired")
    if crit["availability_confirmed"] is not True:
        gaps.append("current availability not confirmed with evidence")
    if rel.relevance != DIRECT_MATCH:
        gaps.append("not a DIRECT_MATCH")
    if not (c.photos_available or c.documentation_available):
        gaps.append("no photos/documentation")
    if not (c.contact_name or c.contact_email):
        gaps.append("no contact person")
    if c.international_transfer != "yes":
        gaps.append("international transfer not confirmed possible")
    return gaps
