"""Build 90-master-table.md from partners.csv (sorted by priority, then country rank, then id)."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIORITY = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
# Order of country blocks: China (stage 1), then stage-3 countries in ranking order.
BLOCK_ORDER = ["CN", "RU", "TR", "DE", "UK", "IT"]

rows = list(csv.DictReader(open(ROOT / "partners.csv", encoding="utf-8")))


def key(r):
    prefix, num = r["id"].split("-")
    block = BLOCK_ORDER.index(prefix) if prefix in BLOCK_ORDER else len(BLOCK_ORDER)
    return (PRIORITY[r["priority"]], block, int(num))


rows.sort(key=key)
counts = {p: sum(r["priority"] == p for r in rows) for p in PRIORITY}

out = [
    "# Сводная таблица всех партнёров (по приоритету)",
    "",
    "Генерируется из [partners.csv](partners.csv) скриптом `tools/build_master_table.py`. "
    "Дата обращения к источникам: 2026-10-02.",
    "",
    f"Всего: **{len(rows)}** — HIGH {counts['HIGH']}, MEDIUM {counts['MEDIUM']}, LOW {counts['LOW']}.",
    "",
    "| № | ID | Организация | Страна | Тип | Приоритет | Ключевая просьба | Контакт (e-mail) | Карточка |",
    "|---|---|---|---|---|---|---|---|---|",
]
for i, r in enumerate(rows, 1):
    name = r["name_en"] + (f" — {r['name_local']}" if r["name_local"] and r["name_local"] != r["name_en"] else "")
    contact = r["contact_email"] or "e-mail не опубликован — см. карточку"
    out.append(
        f"| {i} | {r['id']} | {name} | {r['country']} | {r['type'].replace(';', ', ')} | "
        f"**{r['priority']}** | {r['key_ask']} | {contact} | [{r['file']}]({r['file']}) |"
    )
(ROOT / "90-master-table.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} rows")
