"""Model bergan raqam va sanalarni hujjat matni (OCR yoki PDF matni) bilan solishtirish.

Topilsa — "ok". Topilmasa — "unconfirmed" (masalan, qo'lda yozilgan shtamp): qiymat ko'rsatiladi,
lekin xodim uni alohida solishtiradi. Qiymat bo'lmasa — "empty".
"""
from __future__ import annotations

import re
from datetime import date

OK, UNCONFIRMED, EMPTY = "ok", "unconfirmed", "empty"

# OCR ko'pincha lotin va kirill harflarini aralashtiradi.
_LOOKALIKE = str.maketrans({
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p",
    "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ј": "j",
})

_UZ_LAT = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
_UZ_CYR = ["январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]
_RU = ["январ", "феврал", "март", "апрел", "мая", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"]


def compact(text: str) -> str:
    """Kichik harf, o'xshash kirill harflari lotinga, faqat harf va raqamlar qoladi."""
    lowered = str(text or "").lower().translate(_LOOKALIKE)
    return "".join(ch for ch in lowered if ch.isalnum())


def _found(haystack: str, needle: str) -> bool:
    """Qidiruv: raqam bilan boshlanib/tugasa, yonida boshqa raqam bo'lmasligi kerak (1.10 ≠ 21.10)."""
    if len(needle) < 2:
        return False
    pattern = re.escape(needle)
    if needle[0].isdigit():
        pattern = r"(?<!\d)" + pattern
    if needle[-1].isdigit():
        pattern += r"(?!\d)"
    return re.search(pattern, haystack) is not None


def date_variants(d: date) -> list[str]:
    numeric = [
        f"{d.day:02d}.{d.month:02d}.{d.year}", f"{d.day}.{d.month}.{d.year}",
        f"{d.day:02d}.{d.month:02d}.{d.year % 100:02d}", f"{d.day}.{d.month}.{d.year % 100:02d}",
        f"{d.year}-{d.month:02d}-{d.day:02d}",
    ]
    named = [f"{d.day} {names[d.month - 1]}" for names in (_UZ_LAT, _UZ_CYR, _RU)]
    return [compact(v) for v in numeric + named]


def check_value(text_compact: str, value: str) -> str:
    if not str(value or "").strip():
        return EMPTY
    return OK if _found(text_compact, compact(value)) else UNCONFIRMED


def check_date(text_compact: str, iso: str) -> str:
    if not iso:
        return EMPTY
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return EMPTY
    return OK if any(_found(text_compact, v) for v in date_variants(d)) else UNCONFIRMED


def check_fields(fields: dict, text: str) -> dict:
    """Raqam va sana maydonlari uchun holat; qolganlari faqat bo'sh/to'ldirilgan."""
    t = compact(text)
    checks = {
        "reg_no": check_value(t, fields.get("reg_no", "")),
        "out_no": check_value(t, fields.get("out_no", "")),
        "reg_date": check_date(t, fields.get("reg_date", "")),
        "due_date": check_date(t, fields.get("due_date", "")),
    }
    for name in ("resolution", "due_text", "summary", "emails"):
        checks[name] = OK if str(fields.get(name, "")).strip() else EMPTY
    return checks
