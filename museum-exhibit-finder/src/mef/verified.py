"""Verified offers: the strict list the museum actually asked for.

A museum appears here only if a source says that objects it no longer uses
(removed, replaced, deaccessioned, closed) are being **given away, transferred
or sold** — and that offer is not stale (see ``priority``). Everything else
(renovations, new galleries, "fate unknown") is kept out of this file.
"""

from __future__ import annotations

import datetime as dt
import re

from .config import load_yaml
from .evidence import parse_date
from .models import AVAILABILITY_SIGNALS, REMOVAL_SIGNALS, Evidence, MuseumFile
from .priority import Assessment, _assess, _expired, _fresh, assess_exhibit
from .rows import ranked_contacts


def _cell(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).replace("|", "\\|").strip()


def _offer_status(evs: list[Evidence], today: dt.date) -> str:
    open_until = [e for e in evs if e.valid_until and parse_date(e.valid_until) >= today]
    if open_until:
        return f"открыто до {max(e.valid_until for e in open_until)}"
    dated = [e for e in evs if e.source_date]
    if dated:
        newest = max(e.source_date for e in dated)
        undated = " (часть источников без даты)" if len(dated) < len(evs) else ""
        return f"предложение опубликовано {newest}{undated} — уточнить, что ещё доступно"
    return "дата публикации не указана — проверить, что объявление ещё активно"


def _source_line(e: Evidence, today: dt.date | None = None) -> str:
    date = e.source_date or "без даты"
    if e.excerpt and e.excerpt_is_verbatim:
        quote = f" Цитата: «{_cell(e.excerpt)}»"
    elif e.excerpt:
        quote = f" Текст источника (по сниппету, не дословно): {_cell(e.excerpt)}"
    else:
        quote = ""
    closed = f" **Срок подачи заявок истёк {e.valid_until}.**" if today and _expired(e, today) else ""
    return f"  - [{e.id}] {_cell(e.claim).rstrip('.')}.{quote}{closed} Источник: {e.url} ({date})"


def _assessed_items(mf: MuseumFile, today: dt.date) -> list[tuple[str, Assessment]]:
    """Every exhibit (or exhibit-less exhibition) of a museum with its assessment."""
    out = []
    by_id = mf.evidence_by_id()
    for ex in mf.exhibitions:
        if ex.exhibits:
            for it in ex.exhibits:
                dims = it.dimensions and not re.search(r"\bcm\b|\bmm\b|\bm\b", it.name)
                out.append((it.name + (f" — {it.dimensions}" if dims else ""), assess_exhibit(mf, it, today)))
        else:
            evs = [by_id[i] for i in ex.evidence if i in by_id]
            out.append((ex.name, _assess(evs, ex.status, today)))
    return out


def _offered_items(mf: MuseumFile, today: dt.date) -> list[tuple[str, list[Evidence]]]:
    return [(label, a.availability_evidence) for label, a in _assessed_items(mf, today) if a.priority == "A"]


def _earlier_offers(mf: MuseumFile, today: dt.date) -> list[tuple[str, Assessment]]:
    """Items that were offered, but the window closed, the source is stale or social-media only."""
    return [(label, a) for label, a in _assessed_items(mf, today) if a.priority == "B" and a.availability_evidence]


def _museum_evidence(mf: MuseumFile, items, today: dt.date) -> tuple[list, list, list]:
    """(current offer evidence, earlier/closed offer rounds, removal evidence) for one museum."""
    offer = []
    for _, evs in items:
        offer += [e for e in evs if e not in offer]
    avail = [e for e in mf.evidence if set(e.signals) & AVAILABILITY_SIGNALS and e not in offer]
    fresh, stale = _fresh(avail, today)
    offer += fresh
    removal = [e for e in mf.evidence if set(e.signals) & REMOVAL_SIGNALS and e not in offer and e not in stale]
    return offer, stale, removal


def collect(files: list[MuseumFile], today: dt.date) -> tuple[list, list]:
    """(verified, closed): museums with a current documented offer, and museums whose offer lapsed."""
    verified, closed = [], []
    for mf in files:
        items = _offered_items(mf, today)
        if items:
            verified.append((mf, items))
            continue
        earlier = _earlier_offers(mf, today)
        if earlier:
            closed.append((mf, earlier))

    def sort_key(entry):
        mf, items = entry
        evs = _museum_evidence(mf, items, today)[0]
        open_window = any(e.valid_until and parse_date(e.valid_until) >= today for e in evs)
        newest = max((parse_date(e.source_date) or dt.date.min for e in evs), default=dt.date.min)
        return (not open_window, -newest.toordinal())

    verified.sort(key=sort_key)
    return verified, closed


def verified_offers_markdown(files: list[MuseumFile], today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    verified, closed = collect(files, today)
    snippet = sum(1 for mf, _ in verified for e in mf.evidence if e.verified_via == "web_search_snippet")
    out = [
        "# Подтверждённые предложения: музеи, которые реально отдают / продают снятые предметы",
        "",
        f"Дата: {today.isoformat()} · В список попадают **только** случаи, где источник прямо говорит, что "
        "предметы, которые музей больше не использует (сняты, заменены, списаны, музей закрыт), "
        "**передаются, продаются или отдаются** другим организациям, и предложение не устарело "
        "(не старше 2 лет и срок объявления не истёк).",
        "",
        "Реконструкции, новые галереи и «старые экспонаты на складе, судьба неизвестна» сюда **не входят** "
        "— они в `REPORT.md` → Museum Leads.",
        "",
    ]
    if snippet:
        out += [
            "> ⚠️ Доказательства получены из сводок поисковой выдачи (страницы не открывались из среды "
            "исследования). Перед письмом откройте ссылку и убедитесь, что объявление ещё на месте.",
            "",
        ]
    out += [f"## Подтверждено: {len(verified)} организаций", ""]
    out += ["| # | Музей | Что предлагают | Статус предложения | Кто может получить |", "|---|---|---|---|---|"]
    for n, (mf, items) in enumerate(verified, 1):
        evs = _museum_evidence(mf, items, today)[0]
        what = "; ".join(label for label, _ in items[:3]) + (" …" if len(items) > 3 else "")
        out.append(f"| {n} | {_cell(mf.museum.name)} ({_cell(mf.museum.country)}) | {_cell(what)} | "
                   f"{_offer_status(evs, today)} | {_cell(mf.research.eligibility or 'не указано')} |")
    out.append("")
    for n, (mf, items) in enumerate(verified, 1):
        evs, earlier, removal = _museum_evidence(mf, items, today)
        out += [f"### {n}. {mf.museum.name} — {mf.museum.city or ''}, {mf.museum.country}".replace(" — ,", " —"), ""]
        if mf.research.summary_ru:
            out += [f"_{_cell(mf.research.summary_ru)}_", ""]
        out.append("**Что предлагают:**")
        out += [f"- {_cell(label)}" for label, _ in items]
        out.append("")
        out.append("**Доказательство, что предлагают (отдают / продают / передают):**")
        out += [_source_line(e, today) for e in evs]
        if earlier:
            out += ["", "**Более ранние раунды передачи (срок истёк — подтверждают, что музей реально отдаёт):**"]
            out += [_source_line(e, today) for e in earlier]
        if removal:
            out += ["", "**Доказательство, что предметы сняты / заменены / на складе / музей закрыт:**"]
            out += [_source_line(e, today) for e in removal]
        out.append("")
        out.append(f"**Статус:** {_offer_status(evs, today)}  ")
        out.append(f"**Кто может получить:** {_cell(mf.research.eligibility or 'не указано — уточнить')}  ")
        contacts = ranked_contacts(mf)[:3]
        if contacts:
            out.append("**Контакт:** " + "; ".join(
                ", ".join(x for x in [c.name, c.position, c.email, c.phone, c.contact_page] if x) for c in contacts))
        else:
            out.append("**Контакт:** не найден — через страницу объявления")
        out.append(f"**Следующий шаг:** {_cell(mf.research.next_step or '—')}")
        out.append("")

    out += ["## Предлагали, но срок истёк, данные старше 2 лет или нет официального подтверждения — "
            "спросить, что осталось", ""]
    if closed:
        out += ["| Музей | Что предлагали | Почему не в основном списке | Источник |", "|---|---|---|---|"]
        for mf, earlier in closed:
            what = "; ".join(label for label, _ in earlier)
            notes = " ".join(dict.fromkeys(n for _, a in earlier for n in a.notes))
            urls = " ".join(dict.fromkeys(e.url for _, a in earlier for e in a.availability_evidence))
            out.append(f"| {_cell(mf.museum.name)} ({_cell(mf.museum.country)}) | {_cell(what)[:200]} | "
                       f"{_cell(notes)} | {urls} |")
    else:
        out.append("_Нет._")
    out.append("")

    excluded = load_yaml("excluded_channels.yaml").get("excluded", [])
    if excluded:
        out += ["## Проверено и исключено (не подходит под критерий)", "",
                "| Канал | Почему исключён | Источник |", "|---|---|---|"]
        out += [f"| {_cell(x['name'])} | {_cell(x['reason'])} | {x['url']} |" for x in excluded]
        out.append("")
    return "\n".join(out)
