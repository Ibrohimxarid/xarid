"""[10] Report generator.

Writes ``reports/<run>/REPORT.md`` with the six required sections, a museum
card file (``MUSEUM_CARDS.md``) with the 8 research-logic answers per museum,
and one outreach draft per A/B museum under ``outreach/``.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from . import POTENTIAL_LEAD, UNKNOWN
from .config import PATHS
from .models import STATUS_LABELS, MuseumFile
from .outreach import build_draft
from .priority import assess_museum, research_answers
from .rows import database_record, iter_rows, museum_summary
from .stats import compute_stats

ORDER = {"A": 0, "B": 1, "C": 2, None: 3, "—": 3}


def _cell(v) -> str:
    s = "" if v is None else str(v)
    return re.sub(r"\s+", " ", s.replace("|", "\\|")).strip()


def _link(url: str, label: str | None = None) -> str:
    if not url or not url.startswith("http"):
        return _cell(url)
    return f"[{_cell(label or 'source')}]({url})"


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(_cell(c) if not str(c).startswith("[") else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _sorted(files: list[MuseumFile]) -> list[MuseumFile]:
    return sorted(files, key=lambda mf: (ORDER[assess_museum(mf).priority], mf.museum.country, mf.museum.name))


def section_opportunities(files: list[MuseumFile]) -> str:
    rows = [r for r in iter_rows(files) if r.priority in ("A", "B") and (r.exhibit or r.exhibition)]
    rows.sort(key=lambda r: (ORDER[r.priority], r.museum.museum.country, r.museum.museum.name))
    body = []
    for r in rows:
        rec = database_record(r)
        body.append([
            r.priority,
            f"{rec['Museum']} ({rec['Country']})",
            rec["Old Exhibit"],
            rec["Exhibit Category"] if rec["Exhibit Category"] != UNKNOWN else "—",
            rec["Current Status"],
            rec["Availability Evidence"][:300],
            _link(rec["Source"], rec["Source Date"] if rec["Source Date"] != UNKNOWN else "n.d."),
        ])
    if not body:
        return "_No exhibit-level opportunities yet._"
    return _table(["P", "Museum", "Exhibit / collection", "Category", "Status", "Availability evidence", "Source"], body)


def section_leads(files: list[MuseumFile]) -> str:
    body = []
    for mf in _sorted(files):
        s = museum_summary(mf)
        if s["priority"] not in ("B", "C"):
            continue
        m = mf.museum
        body.append([
            s["priority"], m.name, f"{m.city or ''}, {m.country}".strip(", "), m.type,
            s["old"], s["event"], s["year"],
            mf.research.next_step or POTENTIAL_LEAD,
            _link(s["source"], s["source_date"]),
        ])
    if not body:
        return "_No leads._"
    return _table(["P", "Museum", "Location", "Type", "Old exhibition", "New / event", "Year",
                   "Next step", "Source"], body)


def section_contacts(files: list[MuseumFile]) -> str:
    body = []
    for mf in _sorted(files):
        by_id = mf.evidence_by_id()
        for c in mf.contacts:
            src = c.source if c.source.startswith("http") else by_id[c.source].url
            body.append([
                mf.museum.name, c.name or "—", c.position or "—", c.email or "—", c.phone or "—",
                _link(c.contact_page, "page") if c.contact_page else "—", _link(src, "source"),
            ])
    if not body:
        return "_No contacts recorded yet._"
    return _table(["Museum", "Name", "Position", "Email", "Phone", "Contact page", "Source"], body)


def section_sources(files: list[MuseumFile]) -> str:
    parts = []
    for mf in _sorted(files):
        parts.append(f"**{mf.museum.name}** ({mf.museum.country})\n")
        for e in mf.evidence:
            parts.append(
                f"- [{e.id}] {_cell(e.title or e.claim)} — {_cell(e.publisher or '')} "
                f"({e.source_date or 'n.d.'}; accessed {e.accessed}; {e.verified_via}) — {e.url}"
            )
        parts.append("")
    return "\n".join(parts)


def section_statistics(files: list[MuseumFile]) -> str:
    stats = compute_stats(files)
    countries = sorted({mf.museum.country for mf in files})
    return _table(["Metric", "Value"], [[k, v] for k, v in stats.items()]) + (
        f"\n\nCountries: {', '.join(countries)}"
    )


def museum_cards(files: list[MuseumFile]) -> str:
    out = ["# Museum cards\n",
           "Every statement below is backed by an evidence record `[eN]` listed under the card.\n"]
    for mf in _sorted(files):
        m = mf.museum
        a = assess_museum(mf)
        out.append(f"## {m.name} — priority {a.priority or '—'}\n")
        out.append("### Museum\n")
        out.append(_table(["Field", "Value"], [
            ["Museum name", m.name + (f" / {m.name_local}" if m.name_local else "")],
            ["Country", m.country], ["City", m.city or UNKNOWN],
            ["Website", m.website or UNKNOWN], ["Museum type", m.type],
            ["General email", m.general_email or UNKNOWN], ["Phone", m.phone or UNKNOWN],
            ["LinkedIn", m.linkedin or UNKNOWN],
        ]))
        for ex in mf.exhibitions:
            out.append(f"\n### Exhibition — {ex.name}\n")
            out.append(_table(["Field", "Value"], [
                ["Gallery", ex.gallery or UNKNOWN], ["Opening year", ex.opening_year or UNKNOWN],
                ["Replacement/renovation year", ex.replacement_year or UNKNOWN],
                ["New exhibition", ex.new_exhibition or UNKNOWN],
                ["Old exhibition", ex.old_exhibition or UNKNOWN],
                ["Status", STATUS_LABELS.get(ex.status, ex.status)],
                ["Evidence", ", ".join(f"[{i}]" for i in ex.evidence) or "—"],
            ]))
            for item in ex.exhibits:
                out.append(f"\n#### Old exhibit — {item.name}\n")
                out.append(_table(["Field", "Value"], [
                    ["Description", item.description or UNKNOWN],
                    ["Type / category", ", ".join(item.category) or UNKNOWN],
                    ["Manufacturer", item.manufacturer or UNKNOWN],
                    ["Year / approx. age", " / ".join(x for x in [item.year, item.approx_age] if x) or UNKNOWN],
                    ["Dimensions", item.dimensions or UNKNOWN], ["Weight", item.weight or UNKNOWN],
                    ["Interactive", UNKNOWN if item.interactive is None else ("yes" if item.interactive else "no")],
                    ["Working condition", item.condition or UNKNOWN],
                    ["Educational purpose", item.educational_purpose or UNKNOWN],
                    ["Quantity", item.quantity or UNKNOWN],
                    ["Photos", " ".join(item.photos) or UNKNOWN], ["Video", " ".join(item.video) or UNKNOWN],
                    ["Documentation", " ".join(item.documentation) or UNKNOWN],
                    ["Current status", STATUS_LABELS.get(item.status, item.status)],
                    ["Fit for TPM", item.fit_for_tpm or "—"],
                    ["Evidence", ", ".join(f"[{i}]" for i in item.evidence) or "—"],
                ]))
        out.append("\n### Acquisition potential & research logic\n")
        out.append(_table(["Question", "Answer"], [[k, v] for k, v in research_answers(mf).items()]))
        if a.notes:
            out.append("\n> " + " ".join(a.notes))
        if mf.research.open_questions:
            out.append("\n**Open questions:**\n" + "\n".join(f"- {q}" for q in mf.research.open_questions))
        out.append(f"\n**Next step:** {mf.research.next_step or UNKNOWN}  \n"
                   f"**Outreach status:** {mf.research.outreach_status}\n")
        out.append("**Evidence:**\n")
        for e in mf.evidence:
            out.append(f"- **[{e.id}]** {_cell(e.claim)} — {e.url} "
                       f"({e.source_date or 'n.d.'}; {e.source_type}; {e.verified_via}; signals: "
                       f"{', '.join(e.signals) or '—'})")
            if e.excerpt:
                out.append(f"  > {'“' if e.excerpt_is_verbatim else ''}{_cell(e.excerpt)}"
                           f"{'”' if e.excerpt_is_verbatim else ' (paraphrase)'}")
        out.append("\n---\n")
    return "\n".join(out)


def generate(files: list[MuseumFile], label: str = "run", out_root: Path | None = None) -> Path:
    today = dt.date.today().isoformat()
    run_dir = (out_root or PATHS.reports) / f"{today}-{label}"
    (run_dir / "outreach").mkdir(parents=True, exist_ok=True)
    for stale in (run_dir / "outreach").glob("*.md"):
        stale.unlink()

    drafts = [build_draft(mf) for mf in _sorted(files) if assess_museum(mf).priority in ("A", "B")]
    for d in drafts:
        (run_dir / "outreach" / f"{d.museum_id}.md").write_text(d.markdown(), encoding="utf-8")

    stats = compute_stats(files)
    via: dict[str, int] = {}
    for mf in files:
        for e in mf.evidence:
            via[e.verified_via] = via.get(e.verified_via, 0) + 1
    via_line = ", ".join(f"{k}: {v}" for k, v in sorted(via.items()))
    snippet_note = (
        "\n> **Verification:** evidence marked `web_search_snippet` was taken from search-result "
        "summaries (the pages could not be opened from the research environment). Open the source "
        "link and confirm the fact before contacting a museum.\n"
        if via.get("web_search_snippet") else ""
    )
    report = f"""# Tashkent Polytechnic Museum — Exhibit Acquisition Finder

**Research run:** {label} · **Date:** {today} · **Museums researched:** {stats['Museums researched']} ·
**Countries:** {stats['Countries covered']} · **Evidence records:** {stats['Evidence records (sources)']} ({via_line})
{snippet_note}
Priority legend — **A**: direct opportunity (availability confirmed by source) ·
**B**: potential opportunity (old exhibits removed/stored, fate unknown, or availability evidence stale) ·
**C**: lead (renovation/new exhibition only).
Where availability is not confirmed the system states: *{POTENTIAL_LEAD}*
Unknown fields read: *{UNKNOWN}*

## 1. EXHIBIT OPPORTUNITIES

{section_opportunities(files)}

## 2. MUSEUM LEADS

{section_leads(files)}

## 3. CONTACT LIST

{section_contacts(files)}

## 4. SOURCES

{section_sources(files)}

## 5. OUTREACH DRAFTS

{chr(10).join(d.markdown() for d in drafts) if drafts else '_No A/B museums yet._'}

## 6. RESEARCH STATISTICS

{section_statistics(files)}

---
Museum-by-museum cards with the 8 research-logic answers: `MUSEUM_CARDS.md`.
"""
    (run_dir / "REPORT.md").write_text(report, encoding="utf-8")
    (run_dir / "MUSEUM_CARDS.md").write_text(museum_cards(files), encoding="utf-8")
    return run_dir
