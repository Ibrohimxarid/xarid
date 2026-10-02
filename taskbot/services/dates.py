"""Parsing and formatting of dates entered in Russian."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

MONTHS_GEN = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
MONTHS_NOM = [
    "", "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
]

_TIME_RE = re.compile(r"(?:^|\s)(?:в\s*)?(\d{1,2})[:.](\d{2})\s*$")
_NUMERIC_RE = re.compile(r"^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$")
_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_WORDS_RE = re.compile(r"^(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?(?:\s*г\.?)?$")
_IN_DAYS_RE = re.compile(r"^(?:\+\s*(\d{1,3})|через\s+(\d{1,3})\s*(?:дн[яейь]*|д\.?))$")


def parse_deadline(text: str, now: datetime, default_hour: int = 18) -> datetime | None:
    """Parse a deadline in the user's local time.

    ``now`` must be timezone-aware in the user's zone. Supported forms:
    ``05.10``, ``5.10.2026``, ``2026-10-05``, ``5 октября``, ``сегодня``, ``завтра``,
    ``послезавтра``, ``+3``, ``через 3 дня``; each optionally followed by a time ``18:00``.
    A date without a year that has already passed this year refers to the next year.
    """
    raw = " ".join(text.strip().lower().replace("ё", "е").split())
    if not raw:
        return None

    hour, minute = default_hour, 0
    explicit_time = False
    m = _TIME_RE.search(raw)
    if m and m.start() > 0:
        hour, minute = int(m.group(1)), int(m.group(2))
        raw = raw[: m.start()].strip().rstrip(",")
        explicit_time = True
    elif m and m.start() == 0 and ":" in raw:
        # Only a time was given ("15:00") – means today.
        hour, minute = int(m.group(1)), int(m.group(2))
        raw = "сегодня"
        explicit_time = True
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    today = now.date()
    d: date | None = None
    if raw == "сегодня":
        d = today
    elif raw == "завтра":
        d = today + timedelta(days=1)
    elif raw == "послезавтра":
        d = today + timedelta(days=2)
    elif m2 := _IN_DAYS_RE.match(raw):
        d = today + timedelta(days=int(m2.group(1) or m2.group(2)))
    elif m2 := _ISO_RE.match(raw):
        d = _safe_date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    elif m2 := _NUMERIC_RE.match(raw):
        day, month, year = int(m2.group(1)), int(m2.group(2)), m2.group(3)
        d = _with_year(day, month, year, today)
    elif m2 := _WORDS_RE.match(raw):
        month = MONTHS_GEN.get(m2.group(2))
        if month is None:
            return None
        d = _with_year(int(m2.group(1)), month, m2.group(3), today)
    if d is None:
        return None

    result = datetime.combine(d, time(hour, minute), tzinfo=now.tzinfo)
    if not explicit_time and d == today and result <= now:
        # "сегодня" after the default hour – give the end of the day instead.
        result = datetime.combine(d, time(23, 59), tzinfo=now.tzinfo)
    return result


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _with_year(day: int, month: int, year: str | None, today: date) -> date | None:
    if year:
        y = int(year)
        if y < 100:
            y += 2000
        return _safe_date(y, month, day)
    d = _safe_date(today.year, month, day)
    if d is not None and d < today:
        d = _safe_date(today.year + 1, month, day)
    return d


def end_of_month(d: date) -> date:
    first_next = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_next - timedelta(days=1)


def quick_deadlines(now: datetime, default_hour: int) -> list[tuple[str, datetime]]:
    """Ready-made deadline options shown as buttons."""
    def at(d: date) -> datetime:
        return datetime.combine(d, time(default_hour, 0), tzinfo=now.tzinfo)

    today = now.date()
    friday = today + timedelta(days=(4 - today.weekday()) % 7)
    options = []
    if at(today) > now:
        options.append(("Сегодня", at(today)))
    options += [
        ("Завтра", at(today + timedelta(days=1))),
        ("Через 3 дня", at(today + timedelta(days=3))),
        ("Пятница" if friday != today else "Через неделю", at(friday if friday != today else today + timedelta(days=7))),
        ("Конец месяца", at(end_of_month(today))),
    ]
    return options


def to_local(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt.astimezone(tz)


def fmt_dt(dt: datetime | None, tz: ZoneInfo) -> str:
    if dt is None:
        return "—"
    return dt.astimezone(tz).strftime("%d.%m.%Y %H:%M")


def fmt_date(dt: datetime | None, tz: ZoneInfo) -> str:
    if dt is None:
        return "—"
    return dt.astimezone(tz).strftime("%d.%m.%Y")


def humanize_left(deadline: datetime, now: datetime) -> str:
    """'через 2 дн.', 'через 5 ч', 'просрочено на 1 дн.'"""
    delta = deadline - now
    seconds = delta.total_seconds()
    if seconds >= 0:
        if seconds < 3600:
            return f"через {max(1, int(seconds // 60))} мин"
        if seconds < 86400:
            return f"через {int(seconds // 3600)} ч"
        return f"через {int(seconds // 86400)} дн."
    seconds = -seconds
    if seconds < 86400:
        return f"просрочено на {max(1, int(seconds // 3600))} ч"
    return f"просрочено на {int(seconds // 86400)} дн."


def utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)
