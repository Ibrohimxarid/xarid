"""[6] Contact extractor.

Pulls e-mail addresses (incl. ``name [at] museum [dot] org``), phone numbers,
LinkedIn URLs and role titles from page text. Every contact keeps the URL it
was found on — nothing is guessed or constructed (no ``firstname.lastname@``
pattern filling).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .dedupe import registered_domain

_EMAIL = re.compile(r"(?<![\w.+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24})(?![\w-])")
_OBFUSCATED = re.compile(
    r"([A-Za-z0-9._%+-]+)\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\{\s*at\s*\}|\s+at\s+)\s*"
    r"([A-Za-z0-9-]+(?:\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\s+dot\s+|\.)\s*[A-Za-z0-9-]+)+)",
    re.IGNORECASE,
)
_PHONE = re.compile(r"(?<!\w)(\+\d{1,3}[\s.-]?(?:\(?\d{1,4}\)?[\s.-]?){2,5}\d{2,4})(?!\w)")
_LINKEDIN = re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company|school)/[A-Za-z0-9_%\-/.]+", re.I)

ROLE_TITLES = [
    "Director", "Chief Executive", "CEO", "Deputy Director", "Head of Collections",
    "Collections Manager", "Collection Manager", "Registrar", "Curator", "Senior Curator",
    "Head of Exhibitions", "Exhibitions Manager", "Exhibition Manager", "Exhibits Manager",
    "Head of Programmes", "Head of Learning", "Head of Operations", "Operations Director",
    "Technical Manager", "Workshop Manager", "Exhibit Developer", "Project Manager",
    "Sammlungsleiter", "Kurator", "Leiter der Ausstellungen", "Registrarin",
    "conservateur", "responsable des collections", "directeur", "directrice",
    "conservator", "collectiebeheerder", "hoofd collecties",
    "intendent", "samlingschef", "utställningschef",
]
_ROLE = re.compile(r"(?<!\w)(" + "|".join(re.escape(r) for r in ROLE_TITLES) + r")(?!\w)", re.I)

_IGNORE_EMAIL = re.compile(r"(example\.(com|org)|sentry|wixpress|\.png$|\.jpg$|\.gif$|@2x)", re.I)


@dataclass
class ExtractedContact:
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    role: str | None = None
    context: str = ""
    same_domain: bool | None = None
    source: str = ""
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _deobfuscate(user: str, domain: str) -> str:
    domain = re.sub(r"\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\s+dot\s+)\s*", ".", domain, flags=re.I)
    return f"{user}@{domain.replace(' ', '')}"


def _context(text: str, start: int, end: int, width: int = 90) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - width) : min(len(text), end + width)]).strip()


def extract_contacts(text: str, source_url: str, museum_website: str | None = None) -> list[ExtractedContact]:
    home = registered_domain(museum_website or source_url)
    out: list[ExtractedContact] = []
    seen: set[str] = set()

    def add_email(addr: str, start: int, end: int) -> None:
        addr = addr.strip(".").lower()
        if addr in seen or _IGNORE_EMAIL.search(addr):
            return
        seen.add(addr)
        ctx = _context(text, start, end)
        role = _ROLE.search(ctx)
        out.append(
            ExtractedContact(
                email=addr,
                role=role.group(1) if role else None,
                context=ctx,
                same_domain=(registered_domain("http://" + addr.split("@", 1)[1]) == home) if home else None,
                source=source_url,
            )
        )

    for m in _EMAIL.finditer(text):
        add_email(m.group(1), m.start(), m.end())
    for m in _OBFUSCATED.finditer(text):
        candidate = _deobfuscate(m.group(1), m.group(2))
        if _EMAIL.fullmatch(candidate):
            add_email(candidate, m.start(), m.end())
    for m in _PHONE.finditer(text):
        num = re.sub(r"\s+", " ", m.group(1)).strip()
        digits = re.sub(r"\D", "", num)
        if len(digits) < 8 or num in seen:
            continue
        seen.add(num)
        out.append(ExtractedContact(phone=num, context=_context(text, m.start(), m.end()), source=source_url))
    for m in _LINKEDIN.finditer(text):
        link = m.group(0).rstrip("/.")
        if link in seen:
            continue
        seen.add(link)
        out.append(ExtractedContact(linkedin=link, context=_context(text, m.start(), m.end()), source=source_url))
    return out
