"""TASHKENT POLYTECHNIC MUSEUM RELEVANCE CHECK and acquisition priority.

Relevance answers "would this object genuinely serve TPM's automotive /
transport / physics / engineering / robotics / STEM exhibition?" — decided by
rules over two recorded facts (categories and object_type), never by a score:

* DIRECT_MATCH  — a demonstration object (interactive station, demonstrator,
  cutaway, simulator, robot, digital installation) in a core TPM area, or an
  engine/turbine/motor in a core area (engines are named in A1/A2/A6).
* STRONG_MATCH  — a real technology object (vehicle, aircraft, rolling stock,
  machine, instrument, computer, model) in a core or "useful" (group B) area,
  or a demonstration object in a group-B-only area.
* RELATED       — a component / part of a technology object.
* WEAK_MATCH    — household equipment or another object with only a loose link.
* NOT_RELEVANT  — books, documents, furniture, vitrines, decorative objects,
  or no connection to technology/science/engineering/transport. Never shown.

Objects whose contents are not itemised (``mixed_collection``/``unspecified``)
get no relevance: they are *channels* to ask, not candidates.

Acquisition priority (HIGH / MEDIUM / LOW) is not availability alone. It
counts six factual checks — strong relevance, genuine museum exhibit,
physically reusable, educational value, reasonable logistics (incl. whether a
foreign museum may receive it) and current availability:

* HIGH   — strong relevance (DIRECT/STRONG) and every other check is "yes";
* MEDIUM — strong relevance and exactly one check is "no" or "unknown";
* LOW    — weak relevance (RELATED/WEAK) or two or more open checks.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from functools import lru_cache

from .config import load_yaml
from .evidence import parse_date
from .models import Exhibit, Exhibition, MuseumFile, ObjectType, Relevance
from .priority import Assessment, _expired

STRONG = {Relevance.DIRECT_MATCH, Relevance.STRONG_MATCH}
RELEVANCE_ORDER = {r: i for i, r in enumerate(Relevance)}
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
YES, NO, UNKNOWN = "yes", "no", "unknown"


def _v(x):
    """Enum value or the plain string (models store enum values as strings)."""
    return getattr(x, "value", x)


@lru_cache(maxsize=1)
def rules() -> dict:
    return load_yaml("relevance.yaml")


def _group(name: str) -> set[str]:
    return set(rules()["object_type_groups"][name])


def profile_areas(categories: list[str]) -> list[str]:
    mapping = rules()["category_area"]
    return sorted({mapping[c] for c in categories if c in mapping})


def area_labels(areas: list[str]) -> str:
    names = rules()["areas"]
    return "; ".join(f"{a} {names[a]}" for a in areas)


def classify(categories: list[str], object_type: ObjectType | str) -> tuple[Relevance | None, str]:
    """Rule-based relevance for one object. Returns (relevance, reason)."""
    ot = ObjectType(object_type).value
    areas = profile_areas(categories)
    core = [a for a in areas if a.startswith("A")]
    useful = "B" in areas
    excluded_cats = set(rules()["excluded_categories"])

    if ot in _group("excluded"):
        return Relevance.NOT_RELEVANT, f"тип объекта «{ot}» в списке исключений (книги, документы, мебель, декор)"
    if categories and set(categories) <= excluded_cats:
        return Relevance.NOT_RELEVANT, f"категории {categories} в списке исключений"
    if ot in _group("not_itemised"):
        return None, "состав не перечислен — это канал, где запросить список, а не кандидат"
    if not areas:
        return Relevance.NOT_RELEVANT, "нет связи с техникой, наукой, инженерией или транспортом"
    if ot in _group("demonstration"):
        if core:
            return Relevance.DIRECT_MATCH, f"{ot} в основном направлении {', '.join(core)}"
        return Relevance.STRONG_MATCH, f"{ot} в направлении группы B"
    if ot == ObjectType.engine.value and core:
        return Relevance.DIRECT_MATCH, f"двигатель в основном направлении {', '.join(core)}"
    if ot in _group("real_technology"):
        return Relevance.STRONG_MATCH, f"реальный технический объект ({ot}), направление {', '.join(areas)}"
    if ot in _group("partial"):
        return Relevance.RELATED, "деталь технического объекта, а не целый экспонат"
    if ot in _group("low_value"):
        return Relevance.WEAK_MATCH, "обычная бытовая техника — низкий приоритет по ТЗ"
    return Relevance.WEAK_MATCH, "слабая связь с профилем TPM"


def relevance_of(obj: Exhibit | Exhibition) -> tuple[Relevance | None, str]:
    override = getattr(obj, "relevance", None)
    if override:
        return Relevance(override), f"вручную: {obj.relevance_reason}"
    return classify(obj.category, obj.object_type)


def why_it_fits_problems(text: str | None) -> list[str]:
    """Reasons a WHY_IT_FITS text is not acceptable (empty list = fine)."""
    if not text or not text.strip():
        return ["отсутствует"]
    problems = []
    low = text.lower()
    if len(text.strip()) < 60:
        problems.append("слишком коротко (<60 символов), чтобы объяснить образовательную связь")
    if any(re.search(p, low) for p in rules()["generic_why_it_fits_patterns"]):
        problems.append("общая фраза — назовите явление или технологию, которую показывает объект")
    if not any(t in low for t in rules()["why_it_fits_terms"]):
        problems.append("не названо ни одно конкретное явление, технология или действие")
    return problems


@dataclass
class Check:
    name: str
    status: str  # yes / no / unknown
    detail: str


@dataclass
class Acquisition:
    relevance: Relevance | None
    relevance_reason: str
    priority: str | None  # HIGH / MEDIUM / LOW, None for NOT_RELEVANT or not itemised
    checks: list[Check] = field(default_factory=list)

    @property
    def open_checks(self) -> list[Check]:
        return [c for c in self.checks if c.status != YES]

    def why_not_high(self) -> str:
        ru = {YES: "да", NO: "нет", UNKNOWN: "неизвестно"}
        return "; ".join(f"{c.name}: {ru[c.status]} — {c.detail}" for c in self.open_checks)


CHECK_NAMES = [
    "Сильное соответствие профилю",
    "Подлинный музейный экспонат",
    "Физически пригоден",
    "Образовательная ценность",
    "Разумная логистика",
    "Доступность подтверждена сейчас",
]


def _notes_ru(notes: list[str]) -> str:
    out = []
    for n in notes:
        m = re.match(r"Offer window closed on (\S+)", n)
        if m:
            out.append(f"срок предложения истёк {m.group(1)}")
            continue
        m = re.match(r"Availability evidence dated (\S+) is older than (\d+) years", n)
        if m:
            out.append(f"данные от {m.group(1)} старше {m.group(2)} лет")
            continue
        if n.startswith("Availability reported only on social media"):
            out.append("сведения только из соцсетей, официального подтверждения нет")
            continue
        if n.startswith("Availability source is undated"):
            out.append("источник без даты")
            continue
        out.append(n)
    return "; ".join(out)


def _availability_check(a: Assessment, today: dt.date) -> Check:
    name = CHECK_NAMES[5]
    if a.priority == "A" and a.availability_evidence:
        open_dated = [e for e in a.availability_evidence if e.source_date and not _expired(e, today)]
        if open_dated:
            newest = max(e.source_date for e in open_dated)
            return Check(name, YES, f"предложение от {newest}")
        return Check(name, UNKNOWN, "предложение есть, но без даты — проверить, что оно ещё действует")
    if a.availability_evidence:
        return Check(name, NO, _notes_ru(a.notes) or "предложение устарело или закрыто")
    return Check(name, NO, "ни один источник не говорит, что его отдают (снят / на складе, судьба неизвестна)")


def _logistics_check(mf: MuseumFile, obj: Exhibit | Exhibition) -> Check:
    name = CHECK_NAMES[4]
    intl = _v(mf.research.international_transfer)
    transport = getattr(obj, "transport", None)
    ot = ObjectType(obj.object_type).value
    if transport is None and ot in ("rolling_stock",):
        transport_v, how = "oversize", "по типу объекта"
    else:
        transport_v, how = _v(transport), "по источнику"
    if transport_v in ("oversize", "hazardous"):
        return Check(name, NO, f"{'негабаритная' if transport_v == 'oversize' else 'опасный груз —'} перевозка ({how})")
    if intl == "no":
        return Check(name, NO, "источник ограничивает получателей организациями своей страны")
    if transport_v == "standard" and intl == "yes":
        return Check(name, YES, "обычная перевозка; ограничений для иностранных получателей нет")
    parts = []
    if transport_v is None:
        parts.append("размер и вес не указаны")
    if intl == "domestic_first":
        parts.append("приоритет у организаций своей страны, иностранным — только после них")
    elif intl == "unknown":
        parts.append("не сказано, может ли получить иностранный музей")
    return Check(name, UNKNOWN, "; ".join(parts))


def assess_acquisition(
    mf: MuseumFile, obj: Exhibit | Exhibition, a: Assessment, today: dt.date | None = None
) -> Acquisition:
    today = today or dt.date.today()
    rel, reason = relevance_of(obj)
    if rel is None or rel == Relevance.NOT_RELEVANT:
        return Acquisition(rel, reason, None, [])
    ot = ObjectType(obj.object_type).value
    checks = [Check(CHECK_NAMES[0], YES if rel in STRONG else NO, rel.value)]

    if ot in _group("partial") | _group("low_value"):
        checks.append(Check(CHECK_NAMES[1], NO, f"{ot} — не целый музейный экспонат"))
    else:
        displayed = getattr(obj, "former_exhibit", None)
        detail = "предмет музейного собрания" + (", был в экспозиции" if displayed else "")
        checks.append(Check(CHECK_NAMES[1], YES, detail))

    wc = getattr(obj, "working_condition", None)
    if wc is None:
        cond = getattr(obj, "condition", None)
        checks.append(Check(CHECK_NAMES[2], UNKNOWN, f"состояние: {cond}" if cond else "состояние не указано"))
    elif _v(wc) == "parts_only":
        checks.append(Check(CHECK_NAMES[2], NO, "только на запчасти"))
    else:
        checks.append(Check(CHECK_NAMES[2], YES, {"working": "работает", "restorable": "можно восстановить", "display_only": "пригоден для статичной экспозиции"}[_v(wc)]))

    if ot in _group("demonstration"):
        checks.append(Check(CHECK_NAMES[3], YES, "интерактивный / демонстрационный объект"))
    elif ot in _group("real_technology"):
        checks.append(Check(CHECK_NAMES[3], YES, "реальный технический объект для экспозиции истории техники"))
    else:
        checks.append(Check(CHECK_NAMES[3], NO, f"{ot} — малая самостоятельная образовательная ценность"))

    checks.append(_logistics_check(mf, obj))
    checks.append(_availability_check(a, today))

    open_n = sum(1 for c in checks[1:] if c.status != YES)
    if rel not in STRONG:
        prio = "LOW"
    elif open_n == 0:
        prio = "HIGH"
    elif open_n == 1:
        prio = "MEDIUM"
    else:
        prio = "LOW"
    return Acquisition(rel, reason, prio, checks)


def ideal_target_flags(mf: MuseumFile, obj: Exhibit | Exhibition) -> dict[str, str]:
    """The extra facts of the brief's IDEAL TARGET that are not part of the priority."""
    docs = list(getattr(obj, "photos", []) or []) + list(getattr(obj, "documentation", []) or [])
    person = next((c for c in mf.contacts if c.kind == "person" and (c.email or c.phone)), None)
    general = next((c for c in mf.contacts if c.email or c.phone), None)
    return {
        "photos_docs": "есть" if docs else "не собраны",
        "contact": (f"контактное лицо: {person.name}" if person else ("общий адрес" if general else "не найден")),
        "international": _v(mf.research.international_transfer),
    }


def newest_date(a: Assessment) -> dt.date:
    return max((parse_date(e.source_date) or dt.date.min for e in a.availability_evidence), default=dt.date.min)
