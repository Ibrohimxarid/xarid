from datetime import date
from pathlib import Path

import openpyxl
import pytest

from ijro import evidence
from ijro.contacts import Contact, ContactBook, match_executors, name_tokens, split_emails
from ijro.defaults import DEFAULT_CONFIG
from ijro.pages import select_pages
from ijro.validate import (format_due_text, normalize_model_output, parse_date, registration_payload,
                           validate_for_registration)


def test_example_config_matches_built_in_default():
    example = Path(__file__).resolve().parents[1] / "config.example.yaml"
    assert example.read_text(encoding="utf-8") == DEFAULT_CONFIG


@pytest.mark.parametrize("total,limit,expected", [
    (1, 4, [0]), (4, 4, [0, 1, 2, 3]), (10, 4, [0, 1, 2, 9]), (10, 1, [0]), (3, 2, [0, 2]),
])
def test_select_pages(total, limit, expected):
    assert select_pages(total, limit) == expected


def test_name_tokens_handle_initials_order_apostrophes_and_cyrillic():
    assert name_tokens("U.Xoshimova") == ["u", "xoshimova"]
    assert name_tokens("Xoshimova U.") == name_tokens("U.Xoshimova") == name_tokens("У.Хошимова")
    assert name_tokens("G'ulomov") == name_tokens("Ғуломов")


def test_match_executors_multiple_partial_ambiguous_unknown():
    contacts = [
        Contact("U.Xoshimova", ["u.xoshimova@corp.uz"]),
        Contact("TTPU", ["info@ttpu.uz", "rektor@ttpu.uz"], ["Turin politexnika universiteti"]),
        Contact("A.Karimov", ["a.karimov@corp.uz"]),
        Contact("B.Karimov", ["b.karimov@corp.uz"]),
    ]
    emails, unmatched = match_executors(
        ["U.Xoshimova", "TTPU rektori", "Хошимова", "Karimov", "Noma'lum"], contacts)
    assert emails == ["u.xoshimova@corp.uz", "info@ttpu.uz", "rektor@ttpu.uz"]
    assert unmatched == ["Karimov (bir nechta kontaktga mos)", "Noma'lum"]


def test_contact_book_creates_template_and_reloads(tmp_path):
    path = tmp_path / "kontaktlar.xlsx"
    book = ContactBook(path)
    assert path.exists() and book.contacts() == []
    wb = openpyxl.load_workbook(path)
    wb.active.append(["U.Xoshimova", "U.Xoshimova@corp.uz; x@corp.uz", "Хошимова У.", ""])
    wb.active.append(["Emailsiz", "", "", ""])
    wb.save(path)
    import os
    os.utime(path, (1, 2))  # mtime o'zgarganini aniq qilish
    assert [(c.name, c.emails, c.aliases) for c in book.contacts()] == [
        ("U.Xoshimova", ["u.xoshimova@corp.uz", "x@corp.uz"], ["Хошимова У."])]


def test_split_emails():
    assert split_emails("A@x.uz, a@x.uz; b@y.uz\nnot-an-email") == ["a@x.uz", "b@y.uz"]


def test_evidence_numbers_respect_digit_boundaries_and_lookalikes():
    text = evidence.compact("Kiruvchi № 488-РА (kirill) 01.10.2026; chiqish 26-2850")
    assert evidence.check_value(text, "488-PA") == evidence.OK
    assert evidence.check_value(text, "88-PA") == evidence.UNCONFIRMED
    assert evidence.check_value(text, "26-2851") == evidence.UNCONFIRMED
    assert evidence.check_value(text, "") == evidence.EMPTY


@pytest.mark.parametrize("written", [
    "01.10.2026", "1.10.2026", "01.10.26", "2026-10-01", "1-oktabr 2026-yil", "1 октября 2026 г.", "1-октябрь",
])
def test_evidence_date_formats(written):
    assert evidence.check_date(evidence.compact(f"sana: {written}"), "2026-10-01") == evidence.OK


def test_evidence_date_does_not_match_other_day():
    assert evidence.check_date(evidence.compact("21.10.2026 va 11-oktabr"), "2026-10-01") == evidence.UNCONFIRMED
    assert evidence.check_date(evidence.compact("1 марта"), "2026-05-01") == evidence.UNCONFIRMED


def test_normalize_model_output_never_invents():
    fields, executors, notes = normalize_model_output({
        "royxat_raqami": " 488-PA ", "royxat_sanasi": "2026-02-30", "chiqish_raqami": None,
        "ijrochilar": ["U.Xoshimova", " ", None], "ijro_muddati_sana": "12.10.2026",
        "ijro_muddati_matn": None, "qisqacha_mazmun": "", "izoh": "Rezolyutsiya xira",
    })
    assert fields == {"reg_no": "488-PA", "reg_date": "", "out_no": "", "resolution": "U.Xoshimova",
                      "due_date": "", "due_text": "", "summary": ""}
    assert executors == ["U.Xoshimova"]
    assert notes[0] == "Rezolyutsiya xira"
    assert len(notes) == 3


def test_due_text_and_dates():
    assert format_due_text(date(2026, 10, 12)) == "12-oktabrga qadar"
    assert parse_date("12.10.2026") == date(2026, 10, 12)
    assert parse_date("2026-10-12") == date(2026, 10, 12)
    assert parse_date("31.02.2026") is None


def test_validation_and_payload():
    errors, _ = validate_for_registration({"emails": "x@, "})
    assert errors == ["Ro'yxat raqami bo'sh", "Ro'yxat sanasi bo'sh yoki noto'g'ri", "Rezolyutsiya bo'sh",
                      "Qisqacha mazmun bo'sh", "Noto'g'ri email: x@", "Ijrochilar emaili ko'rsatilmagan"]
    fields = {"reg_no": "488-PA", "reg_date": "2026-10-01", "out_no": "", "resolution": "TTPU",
              "due_date": "2026-10-12", "due_text": "12.10.2026", "summary": "Loyiha",
              "emails": "A@x.uz\nb@y.uz; a@x.uz"}
    errors, emails = validate_for_registration(fields)
    assert errors == [] and emails == ["a@x.uz", "b@y.uz"]
    payload = registration_payload(fields, emails)
    assert payload == {"regNo": "488-PA", "regDate": "2026-10-01", "outNo": "", "resolution": "TTPU",
                       "dueDate": "2026-10-12", "dueText": "12-oktabrga qadar", "summary": "Loyiha",
                       "emails": ["a@x.uz", "b@y.uz"]}
    payload = registration_payload({**fields, "due_date": "", "due_text": "har chorakda"}, emails)
    assert payload["dueDate"] is None and payload["dueText"] == "har chorakda"
