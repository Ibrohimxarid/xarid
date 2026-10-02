"""Targeted search queries.

Never "search for any museum objects that are available". Every query
combines (a) a concrete profile concept, (b) the language institutions use
when an exhibit is retired or offered, and (c) an institution type that owns
real exhibits. Group C / excluded object types are subtracted.
"""

from . import profile

# How institutions describe exhibits leaving the floor.
RETIREMENT_PHRASES = (
    '"exhibit for sale"',
    '"exhibits for sale"',
    '"available for transfer"',
    '"free to a good home" exhibit',
    '"decommissioned exhibit"',
    '"retired exhibit"',
    '"gallery renovation" "old exhibits"',
    '"exhibit replacement" OR "replaced exhibits"',
    '"deaccession" technology museum',
)

# Who owns genuine exhibits in this field.
SOURCE_PHRASES = (
    "science centre",
    "science center",
    "technology museum",
    "transport museum",
    "automotive museum",
)

NEGATIVE_TERMS = ("-book", "-books", "-painting", "-poster", "-archive", "-toy")


def _term(phrase):
    if phrase.startswith("re:"):
        return None
    return f'"{phrase}"' if " " in phrase else phrase


def generate(groups=("A",), per_concept=3, negatives=True):
    """Yield dicts: category, concept, query.

    For each concept, up to `per_concept` queries rotate through retirement
    and source phrases, so the same concept is searched in several ways.
    """
    cats = [c for c in profile.ALL_CATEGORIES if c.group in groups]
    neg = " " + " ".join(NEGATIVE_TERMS) if negatives else ""
    n = 0
    for cat in cats:
        for concept in cat.concepts:
            terms = [t for t in (_term(p) for p in concept.phrases) if t][:3]
            if not terms:
                continue
            subject = "(" + " OR ".join(terms) + ")" if len(terms) > 1 else terms[0]
            for i in range(per_concept):
                retire = RETIREMENT_PHRASES[(n + i) % len(RETIREMENT_PHRASES)]
                source = SOURCE_PHRASES[(n + i) % len(SOURCE_PHRASES)]
                yield {"category": f"{cat.code} {cat.name}", "concept": concept.label,
                       "query": f"{subject} {retire} {source}{neg}"}
            n += 1
