"""TASHKENT POLYTECHNIC MUSEUM RELEVANCE CHECK.

Rule-based and factual: a candidate's category is decided by WHAT the object is
and WHICH profile concepts it demonstrates -- never by a numeric score.

  DIRECT_MATCH  -- demonstrates a Group A concept (automotive, transport,
                   physics, engineering, robotics, interactive STEM, industry).
  STRONG_MATCH  -- demonstrates a Group B concept (aviation, rail, telecoms,
                   computing, space ...): technology education, natural fit.
  RELATED       -- a technology object outside the museum's categories.
  WEAK_MATCH    -- a Group C object type (book, photo, poster, furniture ...)
                   with a real technology-history connection, or a toy /
                   souvenir version of a technology object.
  NOT_RELEVANT  -- excluded types (art, archaeology ...), Group C types with no
                   technology connection, or nothing technological at all.
"""

import re
from dataclasses import dataclass, field

from . import profile

DIRECT_MATCH = "DIRECT_MATCH"
STRONG_MATCH = "STRONG_MATCH"
RELATED = "RELATED"
WEAK_MATCH = "WEAK_MATCH"
NOT_RELEVANT = "NOT_RELEVANT"
RELEVANCE_ORDER = (DIRECT_MATCH, STRONG_MATCH, RELATED, WEAK_MATCH, NOT_RELEVANT)


def _compile(phrase):
    if phrase.startswith("re:"):
        return re.compile(phrase[3:], re.IGNORECASE)
    words = [re.escape(w) for w in re.split(r"[\s-]+", phrase.strip())]
    body = r"[\s-]+".join(words)
    # Optional plural on the last word; word boundaries on both ends.
    return re.compile(r"(?<![\w])" + body + r"(?:s|es)?(?![\w])", re.IGNORECASE)


def _compile_all(phrases):
    return tuple((p, _compile(p)) for p in phrases)


_CONCEPT_PATTERNS = {
    (cat.code, concept.label): _compile_all(concept.phrases)
    for cat in profile.ALL_CATEGORIES for concept in cat.concepts
}
_EXCLUDED = _compile_all(profile.EXCLUDED_TYPES)
_LOW = _compile_all(profile.LOW_PRIORITY_TYPES)
_NOVELTY = _compile_all(profile.NOVELTY_MARKERS)
_GENERAL = _compile_all(profile.GENERAL_TECH_TERMS)
_INTERACTIVE = _compile_all(profile.INTERACTIVE_MARKERS)
_DEMONSTRATOR = _compile_all(profile.DEMONSTRATOR_MARKERS)
_EXHIBIT = _compile_all(profile.EXHIBIT_MARKERS)


def _hits(patterns, text):
    return [phrase for phrase, rx in patterns if rx.search(text)]


@dataclass
class ConceptMatch:
    category_code: str
    category_name: str
    group: str
    areas: tuple
    concept: str
    demonstrates: str
    matched_phrases: list
    in_title: bool


@dataclass
class RelevanceResult:
    relevance: str
    object_kind: str                  # "technology" | "low_priority_type" | "excluded_type" | "unknown"
    type_term: str = ""               # the Group C / excluded term that decided the object kind
    matches: list = field(default_factory=list)   # ConceptMatch, Group A first
    general_terms: list = field(default_factory=list)
    interactive: bool = False
    demonstrator: bool = False
    novelty: bool = False
    reason: str = ""

    @property
    def group_a(self):
        return [m for m in self.matches if m.group == "A"]

    @property
    def group_b(self):
        return [m for m in self.matches if m.group == "B"]


def find_concepts(title, full_text):
    found = []
    for cat in profile.ALL_CATEGORIES:
        for concept in cat.concepts:
            pats = _CONCEPT_PATTERNS[(cat.code, concept.label)]
            hits = _hits(pats, full_text)
            if hits:
                found.append(ConceptMatch(cat.code, cat.name, cat.group, cat.areas, concept.label,
                                          concept.demonstrates, hits, bool(_hits(pats, title))))
    # Group A before B; concepts named in the title before those only in the description.
    found.sort(key=lambda m: (m.group, not m.in_title))
    return found


_CONTAINER = re.compile(r"^.*?\b(?:collection|set|lot|pair|group|series|selection|assortment|number|box)"
                        r"\s+of\s+", re.IGNORECASE)
_MODIFIER = re.compile(r"\s+(?:of|with|for|from|featuring|showing|depicting|including|on|about|in)\s+|[,;(]",
                       re.IGNORECASE)
_ALL_CONCEPT_PATTERNS = tuple(p for pats in _CONCEPT_PATTERNS.values() for p in pats)


def _last_hit(patterns, text):
    """Return (end position, phrase) of the match that ends last, or None."""
    best = None
    for phrase, rx in patterns:
        for m in rx.finditer(text):
            if best is None or m.end() > best[0]:
                best = (m.end(), phrase)
    return best


def _head_kind(text):
    hits = []
    for kind, pats in (("technology", _ALL_CONCEPT_PATTERNS), ("excluded_type", _EXCLUDED),
                       ("low_priority_type", _LOW)):
        hit = _last_hit(pats, text)
        if hit:
            hits.append((hit[0], kind, hit[1] if kind != "technology" else ""))
    if not hits:
        return None
    rank = {"technology": 0, "excluded_type": 1, "low_priority_type": 2}
    end, kind, term = max(hits, key=lambda h: (h[0], -rank[h[1]]))
    return kind, term


def _object_kind(type_text):
    """Decide what kind of object this is from its type (or title).

    Finds the head noun phrase: container words are dropped ("Collection of
    300 railway timetables" -> "300 railway timetables"), modifiers after
    "of/with/for/..." are cut ("Photograph of a locomotive" -> "Photograph"),
    and within what remains the LAST decisive term wins, because English
    compounds are head-final ("railway timetables" are timetables, "toy
    steam engine" is a steam engine -- then capped as a toy). On a tie,
    technology wins ("rotating chair" is an exhibit). If the head phrase has no
    decisive term, the whole text is used. Supplying `object_type` makes this
    exact.
    """
    text = _CONTAINER.sub("", type_text, count=1)
    head = _MODIFIER.split(text, maxsplit=1)[0]
    found = _head_kind(head) or _head_kind(text)
    return found if found else ("unknown", "")


def _normalise(text):
    return re.sub(r"\bcut[\s-]+away", "cutaway", text or "", flags=re.IGNORECASE)


def check(candidate):
    """Run the relevance check on a models.Candidate."""
    title = _normalise(candidate.title or "")
    object_type = _normalise(candidate.object_type)
    type_text = object_type or title
    full_text = _normalise(" ".join([title, object_type, candidate.description, candidate.history,
                                     " ".join(candidate.tags)]))

    matches = find_concepts(title + " " + object_type, full_text)
    kind, type_term = _object_kind(type_text)
    general = _hits(_GENERAL, title + " " + object_type)
    res = RelevanceResult(
        relevance=NOT_RELEVANT, object_kind=kind, type_term=type_term, matches=matches,
        general_terms=general,
        interactive=bool(_hits(_INTERACTIVE, full_text)),
        demonstrator=bool(_hits(_DEMONSTRATOR, full_text)),
        novelty=bool(_hits(_NOVELTY, title + " " + object_type)),
    )

    if kind == "excluded_type":
        res.reason = f"Excluded object type '{type_term}' (art/archaeology/natural history/etc.)."
        return res

    if kind == "low_priority_type":
        if matches:
            res.relevance = WEAK_MATCH
            res.reason = (f"Group C object type '{type_term}' with a technology-history connection "
                          f"({matches[0].concept}); not an exhibit that demonstrates anything itself.")
        else:
            res.reason = f"Group C object type '{type_term}' with no technology connection."
        return res

    if res.group_a:
        res.relevance = DIRECT_MATCH
        res.reason = f"Group A concept: {res.group_a[0].category_name} -- {res.group_a[0].concept}."
    elif res.group_b:
        res.relevance = STRONG_MATCH
        res.reason = f"Group B concept: {res.group_b[0].category_name} -- {res.group_b[0].concept}."
    elif general:
        res.relevance = RELATED
        res.reason = f"Technology object ({', '.join(general[:3])}) outside the museum's core categories."
    else:
        res.reason = "No connection to technology, science, engineering or transport."
        return res

    if res.novelty:
        res.relevance = WEAK_MATCH
        res.reason += " Capped at WEAK_MATCH: toy/souvenir/collectible, not a working exhibit."
    return res


# --------------------------------------------------------------------------
# WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM
# --------------------------------------------------------------------------

def _join(items):
    items = list(dict.fromkeys(items))
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def generate_why_it_fits(candidate, result):
    """Concrete statement of what the object teaches and which museum areas it serves."""
    if result.relevance == NOT_RELEVANT or not result.matches:
        return ""
    picked, seen_cats = [], set()
    for m in result.matches:
        if m.category_code not in seen_cats:
            picked.append(m)
            seen_cats.add(m.category_code)
        if len(picked) == 2:
            break

    form = "Interactive" if result.interactive else ("Demonstration" if result.demonstrator else "")
    subject = f"{form} {candidate.title}".strip() if form and form.lower() not in candidate.title.lower() \
        else candidate.title
    teaches = "; it also shows ".join(m.demonstrates for m in picked)
    areas = []
    for m in picked:
        areas.extend(m.areas)
    if result.interactive:
        areas.append("interactive science")
    if result.relevance == WEAK_MATCH:
        return (f"{candidate.title} documents {picked[0].demonstrates} as supporting material only. "
                f"Fits the museum's technology history area; it is not a hands-on exhibit.")
    return f"{subject} demonstrates {teaches}. Fits the museum's {_join(areas)} areas."


def validate_why_it_fits(text, result):
    """Return a list of problems with a researcher-written WHY_IT_FITS (empty = acceptable)."""
    problems = []
    t = (text or "").strip()
    low = t.lower()
    if len(t) < 60:
        problems.append("too short to explain a concrete educational connection")
    for phrase in profile.GENERIC_WHY_PHRASES:
        if phrase in low:
            problems.append(f"generic wording: '{phrase}'")
    if not any(area.lower() in low for area in profile.PROFILE_AREAS):
        problems.append("does not name any of the museum's profile areas")
    concept_words = {w.lower() for m in result.matches for p in m.matched_phrases for w in re.split(r"[\s-]+", p)
                     if len(w) > 3}
    if result.matches and not any(w in low for w in concept_words):
        problems.append("does not mention what the object actually demonstrates")
    return problems
