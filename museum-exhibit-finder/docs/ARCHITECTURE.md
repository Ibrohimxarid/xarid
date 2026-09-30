# Архитектура: Tashkent Polytechnic Museum — Global Exhibit Acquisition Finder

## Главный принцип

Система ищет не «старые экспонаты», а **события** и строит цепочку:

```
MUSEUM ──► NEW EXHIBITION / RENOVATION ──► OLD EXHIBITION REMOVED ──► OLD EXHIBITS
   │                                                                         │
   │                               FATE: stored / deaccessioned / surplus / sold / donated
   │                                                                         │
   └────────────── CONTACT ◄──── AVAILABILITY EVIDENCE ◄─────────────────────┘
                      │
                      ▼
         OUTREACH → ACQUISITION for Tashkent Polytechnic Museum
```

Каждое звено цепочки — это **сигнал**, и каждый сигнал обязан ссылаться на запись
`evidence` с URL первоисточника, датой источника, датой обращения и цитатой/выдержкой.
Приоритет A/B/C вычисляется **только** из сигналов доказательств — не из свободного текста.

## Два контура

```
                  ┌──────────────────── DISCOVERY (нужен интернет) ─────────────────────┐
config/queries.yaml ─► [1] search.py ─► search_results ─► [2] collector.py ─► sources/cache
 (шаблоны × языки ×        (ddgs | SearXNG |                (кэш, robots.txt,       │
  география × типы)         import JSON)                     rate-limit, Wayback)   ▼
                                                                          [3] parser.py
                                                                  (trafilatura HTML, pypdf PDF)
                                                                                    │
      research/inbox/*.yaml  ◄── [7] exhibits.py + [6] contacts.py ◄── [4] classifier.py
      (черновики-кандидаты          (таксономия экспонатов,            (мультиязычные сигналы,
       для проверки)                 email/тел./LinkedIn + URL)          коммерческий фильтр,
                                                                        опц. Claude — llm.py)
                  └─────────────────────────────────────────────────────────────────────┘
                                          │ человек / AI-исследователь проверяет,
                                          ▼ дополняет и переносит в research/museums/
                  ┌──────────────── KNOWLEDGE BASE (работает офлайн) ───────────────────┐
research/museums/*.yaml ─► ingest (pydantic-валидация) ─► [5] dedupe.py ─► SQLite
 (1 файл = 1 музей:           [8] evidence.py: у каждого утверждения есть источник     │
  museum → exhibitions →                                                               ▼
  exhibits, evidence,            priority.py: A / B / C + ответы на 8 вопросов AI Logic
  contacts)                                                                            │
                        [9] exporter.py ─► exports/*.csv, exports/museum_finder.xlsx   │
                       [10] report.py  ─► reports/<run>/REPORT.md + outreach/*.md ◄────┘
                  └─────────────────────────────────────────────────────────────────────┘
```

## Модули (`src/mef/`)

| # | Модуль | Назначение |
|---|---|---|
| 1 | `search.py` | Search engine: генерация запросов из `config/queries.yaml` (EN/DE/FR/NL/SV/DA/NO/FI/ES/IT/PL/CS/JA/KO), бэкенды `ddgs`, `searxng`, `import` (JSON/CSV результатов, собранных вручную или AI-агентом) |
| 2 | `collector.py` | Source collector: вежливая загрузка (User-Agent, robots.txt, задержки), кэш на диске, fallback на Wayback Machine, журнал `sources/source_log.jsonl` |
| 3 | `parser.py` | Page parser: trafilatura (текст + дата + заголовок), pypdf для PDF |
| 4 | `classifier.py` | Relevance classifier: мультиязычные лексиконы сигналов (renovation, new_exhibition, exhibit_replaced, closure, storage, deaccession, availability, willing_transfer, willing_sale, accepts_requests, touring, international), детектор «это музей?», фильтр коммерческих продавцов новых экспонатов, стадия цепочки 0–5 |
| 5 | `dedupe.py` | Duplicate detector: канонизация URL, регистрируемый домен, fuzzy-сравнение названий (RapidFuzz) + страна |
| 6 | `contacts.py` | Contact extractor: email (включая `name [at] domain`), телефоны, LinkedIn, должности (Registrar, Collections Manager, Head of Exhibitions…) — всегда с URL источника |
| 7 | `exhibits.py` | Exhibit extractor: таксономия (physics/engineering/automotive/transport/digital/STEM) и упоминания объектов |
| 8 | `evidence.py` | Evidence tracker: нормализация доказательств, связь claim ↔ source, агрегирование сигналов |
| 9 | `exporter.py` | CSV/Excel: таблица DATABASE (все обязательные поля), музеи, экспонаты, доказательства, контакты |
| 10 | `report.py` | Report generator: 6 разделов финального отчёта + outreach-письма + статистика |
| – | `priority.py` | A/B/C и ответы на 8 вопросов AI Research Logic только из доказательств |
| – | `llm.py` | Опционально: Claude API (structured outputs) для разбора страниц-кандидатов; цитаты проверяются на дословное вхождение в текст |
| – | `db.py`, `models.py`, `config.py`, `cli.py` | SQLite-схема, pydantic-модели, настройки, CLI `mef` |

## Модель данных (защита от дубликатов)

```
museums (1) ──< exhibitions (N) ──< exhibits (N)
   │                                   │
   ├──< contacts (N)                   └──< exhibit_evidence >── evidence
   └──< evidence (N)  (url, source_date, accessed, claim, excerpt, signals[], verified_via)
search_results, pages (+ FTS5) — сырьё discovery-контура
```

- Ключ музея — slug (`science-museum-london`); дубликаты ловятся по домену сайта и
  fuzzy-названию внутри страны; один музей → много выставок → много экспонатов.
- Ключ доказательства — канонический URL + claim.

## Правила приоритета

| Приоритет | Условие (только по сигналам доказательств) |
|---|---|
| **A — DIRECT OPPORTUNITY** | есть `availability`, `for_sale`, `for_donation`, `willing_transfer`, `willing_sale` или `deaccession_in_progress` по конкретному объекту/коллекции |
| **B — POTENTIAL OPPORTUNITY** | есть `exhibit_replaced` / `exhibits_removed` / `closure` / `storage` (старые экспонаты сняты), но судьба неизвестна |
| **C — LEAD** | только `renovation` / `new_exhibition` / `relocation` |

Если доступность не подтверждена, система пишет: **«Potential lead — availability not confirmed.»**
Если поле неизвестно: **«Unknown — further research required.»**

## Почему два контура

Discovery-контур (поиск и загрузка страниц) требует открытого интернета. Контур базы знаний
работает офлайн и детерминированно: из YAML-файлов исследований строит одну и ту же базу,
экспорт и отчёт. Это позволяет:
- вести исследование и вручную, и AI-агентом, и скриптами — формат один;
- ревьюить изменения в git (каждое новое доказательство — diff в YAML);
- не терять первоисточник ни одного утверждения.
