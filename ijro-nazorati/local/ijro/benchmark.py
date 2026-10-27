"""Modellarni solishtirish: IjroNazorati.exe --benchmark <papka> [--models a,b]

Papkada hujjatlar va kutilgan.csv (";" bilan) bo'ladi:
    fayl;royxat_raqami;royxat_sanasi;chiqish_raqami;ijro_muddati_sana;ijrochilar
    488-PA.pdf;488-PA;2026-10-01;26-2850;2026-10-12;U.Xoshimova, TTPU
Asl fayllar o'zgartirilmaydi va o'chirilmaydi.
"""
from __future__ import annotations

import csv
import tempfile
import time
from pathlib import Path

from .contacts import name_tokens, split_list
from .evidence import compact
from .extract import Extractor

FIELDS = [
    ("royxat_raqami", "reg_no"),
    ("royxat_sanasi", "reg_date"),
    ("chiqish_raqami", "out_no"),
    ("ijro_muddati_sana", "due_date"),
    ("ijrochilar", "resolution"),
]


def _key(field: str, value: str) -> object:
    if field == "ijrochilar":
        return sorted(" ".join(name_tokens(x)) for x in split_list(value))
    return compact(value)


def _read_expected(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    delimiter = ";" if text.count(";") >= text.count(",") else ","
    return [row for row in csv.DictReader(text.splitlines(), delimiter=delimiter) if row.get("fayl")]


def run(extractor: Extractor, folder: Path, models: list[str]) -> str:
    expected = _read_expected(folder / "kutilgan.csv")
    lines = []
    for model in models:
        stats = {f: {"ok": 0, "empty": 0, "wrong": 0} for f, _ in FIELDS}
        seconds = []
        failures = 0
        for row in expected:
            with tempfile.TemporaryDirectory() as tmp:
                started = time.time()
                try:
                    result = extractor.run(folder / row["fayl"], Path(tmp), model)
                except Exception as err:  # noqa: BLE001
                    failures += 1
                    lines.append(f"  {model}: {row['fayl']} — xato: {err}")
                    continue
                seconds.append(time.time() - started)
            for field, key in FIELDS:
                got = str(result.fields.get(key, "")).strip()
                want = str(row.get(field) or "").strip()
                if not got:
                    stats[field]["ok" if not want else "empty"] += 1
                elif want and _key(field, got) == _key(field, want):
                    stats[field]["ok"] += 1
                else:
                    stats[field]["wrong"] += 1  # noto'g'ri yoki hujjatda yo'q narsa yozilgan
        avg = sum(seconds) / len(seconds) if seconds else 0
        lines.append(f"\n=== {model}: {len(expected)} hujjat, o'rtacha {avg:.0f} s, o'qilmadi: {failures}")
        lines.append(f"{'maydon':<20}{'togri':>8}{'bosh':>8}{'XATO':>8}")
        for field, _ in FIELDS:
            s = stats[field]
            lines.append(f"{field:<20}{s['ok']:>8}{s['empty']:>8}{s['wrong']:>8}")
    lines.append("\n«XATO» — model noto'g'ri qiymat yozgan (eng xavflisi). «bo'sh» — xodim qo'lda to'ldiradi.")
    return "\n".join(lines)
