"""[3] Page parser: HTML via trafilatura, PDF via pypdf."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from .collector import Fetched


@dataclass
class ParsedPage:
    url: str
    title: str
    date: str | None
    text: str
    kind: str  # html | pdf | other


def _html(f: Fetched) -> ParsedPage:
    try:
        import trafilatura
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("trafilatura is not installed: pip install trafilatura") from exc
    html = f.body.decode("utf-8", errors="replace")
    text = trafilatura.extract(html, url=f.final_url, include_comments=False, include_tables=True,
                               favor_recall=True) or ""
    meta = trafilatura.extract_metadata(html, default_url=f.final_url)
    title = (meta.title if meta and meta.title else "") or ""
    date = meta.date if meta and meta.date else None
    if not text:  # very thin pages: fall back to raw visible text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
    return ParsedPage(f.url, title, date, text, "html")


def _pdf(f: Fetched) -> ParsedPage:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(f.body))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:  # damaged page: keep going
            pages.append("")
    info = reader.metadata or {}
    title = str(info.get("/Title") or "")
    raw_date = str(info.get("/CreationDate") or "")
    m = re.match(r"D:(\d{4})(\d{2})?(\d{2})?", raw_date)
    date = "-".join(x for x in m.groups() if x) if m else None
    return ParsedPage(f.url, title, date, "\n".join(pages), "pdf")


def parse(f: Fetched) -> ParsedPage:
    ctype = (f.content_type or "").lower()
    if "pdf" in ctype or f.final_url.lower().endswith(".pdf") or f.body[:5] == b"%PDF-":
        return _pdf(f)
    if "html" in ctype or "xml" in ctype or f.body.lstrip()[:1] == b"<":
        return _html(f)
    return ParsedPage(f.url, "", None, f.body.decode("utf-8", errors="replace"), "other")
