"""Model javobini tozalash va ro'yxatga olishdan oldingi tekshiruv."""
from __future__ import annotations

from datetime import date

from .contacts import is_valid_email

UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
             "sentabr", "oktabr", "noyabr", "dekabr"]


def parse_date(value: str) -> date | None:
    """'YYYY-MM-DD' yoki 'DD.MM.YYYY'."""
    s = str(value or "").strip()
    try:
        if "." in s:
            d, m, y = s.split(".")
            return date(int(y), int(m), int(d))
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def format_due_text(d: date) -> str:
    """Reyestrdagi ko'rinish: "12-oktabrga qadar"."""
    return f"{d.day}-{UZ_MONTHS[d.month - 1]}ga qadar"


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def normalize_model_output(raw: dict) -> tuple[dict, list[str], list[str]]:
    """Natija: (maydonlar, ijrochilar ro'yxati, izohlar). Model to'ldirmagan joyni hech qachon to'ldirmaymiz."""
    notes = []
    if _text(raw.get("izoh")):
        notes.append(_text(raw.get("izoh")))

    def iso(key: str, label: str) -> str:
        value = _text(raw.get(key))
        if not value:
            return ""
        d = parse_date(value) if len(value) == 10 and value[4] == "-" else None
        if d is None:
            notes.append(f"{label} noto'g'ri formatda: {value}")
            return ""
        return d.isoformat()

    executors = [x for x in (_text(v) for v in (raw.get("ijrochilar") or [])) if x]
    fields = {
        "reg_no": _text(raw.get("royxat_raqami")),
        "reg_date": iso("royxat_sanasi", "Ro'yxat sanasi"),
        "out_no": _text(raw.get("chiqish_raqami")),
        "resolution": ",\n".join(executors),
        "due_date": iso("ijro_muddati_sana", "Muddat sanasi"),
        "due_text": _text(raw.get("ijro_muddati_matn")),
        "summary": _text(raw.get("qisqacha_mazmun")),
    }
    return fields, executors, notes


def validate_for_registration(fields: dict) -> tuple[list[str], list[str]]:
    """Natija: (xatolar, emaillar)."""
    errors = []
    if not _text(fields.get("reg_no")):
        errors.append("Ro'yxat raqami bo'sh")
    if not parse_date(fields.get("reg_date")):
        errors.append("Ro'yxat sanasi bo'sh yoki noto'g'ri")
    if not _text(fields.get("resolution")):
        errors.append("Rezolyutsiya bo'sh")
    if not _text(fields.get("summary")):
        errors.append("Qisqacha mazmun bo'sh")
    if _text(fields.get("due_date")) and not parse_date(fields.get("due_date")):
        errors.append("Muddat sanasi noto'g'ri")
    emails = []
    for token in _text(fields.get("emails")).replace(";", ",").replace("\n", ",").split(","):
        token = token.strip().lower()
        if not token:
            continue
        if not is_valid_email(token):
            errors.append(f"Noto'g'ri email: {token}")
        elif token not in emails:
            emails.append(token)
    if not emails:
        errors.append("Ijrochilar emaili ko'rsatilmagan")
    return errors, emails


def registration_payload(fields: dict, emails: list[str]) -> dict:
    """Google qismiga yuboriladigan yozuv (Apps Script validateRegistration bilan bir xil maydonlar)."""
    due = parse_date(fields.get("due_date"))
    due_text = _text(fields.get("due_text"))
    return {
        "regNo": _text(fields.get("reg_no")),
        "regDate": parse_date(fields.get("reg_date")).isoformat(),
        "outNo": _text(fields.get("out_no")),
        "resolution": _text(fields.get("resolution")),
        "dueDate": due.isoformat() if due else None,
        "dueText": format_due_text(due) if due else due_text,
        "summary": _text(fields.get("summary")),
        "emails": emails,
    }
