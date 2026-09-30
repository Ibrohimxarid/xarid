"""[5] Duplicate detector.

* URLs are canonicalised (scheme, ``www.``, tracking params, fragments,
  trailing slash) so the same article found by two queries is stored once.
* Museums are matched by registrable domain first (strongest key), then by
  fuzzy name within the same country (RapidFuzz ``token_set_ratio``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from rapidfuzz import fuzz

_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|_hs|ref$|ref_src$|igshid$|si$)")

_STOP = {
    "the", "museum", "museums", "of", "and", "for", "science", "centre", "center",
    "national", "de", "la", "le", "des", "du", "der", "die", "das", "und", "fur", "für",
    "museo", "musee", "muzeum", "museet", "del", "di", "y", "e", "&",
}


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False) if not _TRACKING.match(k)]
    path = re.sub(r"/+$", "", parts.path) or "/"
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))


@lru_cache(maxsize=1)
def _extractor():
    import tldextract

    # Offline: use the snapshot bundled with tldextract, never fetch the PSL.
    return tldextract.TLDExtract(suffix_list_urls=())


def registered_domain(url: str | None) -> str | None:
    if not url:
        return None
    ext = _extractor()(url)
    if not ext.domain:
        return None
    return f"{ext.domain}.{ext.suffix}".lower() if ext.suffix else ext.domain.lower()


def _ascii_tokens(text: str) -> list[str]:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).split()


def normalise_name(name: str, extra_stop: frozenset[str] | set[str] = frozenset()) -> str:
    return " ".join(w for w in _ascii_tokens(name) if w not in _STOP and w not in extra_stop)


def name_similarity(a: str, b: str, extra_stop: frozenset[str] | set[str] = frozenset()) -> float:
    """Order-insensitive similarity of distinctive name tokens.

    Uses token_sort (not token_set) so that "Science Museum" is not a 100% match
    for every name that merely contains those words; ``extra_stop`` removes
    tokens such as the city ("Deutsches Museum München" = "Deutsches Museum").
    """
    na, nb = normalise_name(a, extra_stop), normalise_name(b, extra_stop)
    if not na or not nb:
        return float(fuzz.token_sort_ratio(" ".join(_ascii_tokens(a)), " ".join(_ascii_tokens(b))))
    return float(fuzz.token_sort_ratio(na, nb))


@dataclass
class DuplicatePair:
    a: str
    b: str
    reason: str
    score: float


# Domains shared by many unrelated institutions: never a duplicate key.
SHARED_DOMAINS = {
    "wikipedia.org", "facebook.com", "linkedin.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "google.com", "blogspot.com", "wordpress.com", "gov.uk", "europa.eu",
}


def find_duplicate_museums(museums: list[dict], threshold: float = 92.0) -> list[DuplicatePair]:
    """``museums``: dicts with ``id``, ``name``, ``aliases``, ``country``, ``website``."""
    pairs: list[DuplicatePair] = []
    for i, m in enumerate(museums):
        for n in museums[i + 1 :]:
            da, db = registered_domain(m.get("website")), registered_domain(n.get("website"))
            if da and db and da == db and da not in SHARED_DOMAINS:
                # Same domain can legitimately host sister sites (e.g. a museum group);
                # flag only if the names are also close.
                sim = name_similarity(m["name"], n["name"])
                if sim >= 80:
                    pairs.append(DuplicatePair(m["id"], n["id"], f"same domain {da}", sim))
                    continue
            if (m.get("country") or "").lower() != (n.get("country") or "").lower():
                continue
            names_a = [m["name"], *m.get("aliases", [])]
            names_b = [n["name"], *n.get("aliases", [])]
            cities = set(_ascii_tokens(f"{m.get('city') or ''} {n.get('city') or ''}"))
            best = max(name_similarity(x, y, cities) for x in names_a for y in names_b)
            if best >= threshold:
                pairs.append(DuplicatePair(m["id"], n["id"], "similar name, same country", best))
    return pairs


def dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for u in urls:
        c = canonical_url(u)
        if c not in seen:
            seen.add(c)
            out.append(u)
    return out
