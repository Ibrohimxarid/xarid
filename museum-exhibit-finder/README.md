# Tashkent Polytechnic Museum — Global Exhibit Acquisition Finder

Исследовательская система, которая ищет по всему миру **существующие** музейные экспонаты,
выведенные из экспозиции из-за модернизации (реконструкции, новые галереи, закрытия, переезды,
deaccession), и оценивает, могут ли они быть переданы / проданы / подарены
Tashkent Polytechnic Museum (TPM).

Главный принцип — искать **события**, а не «старые экспонаты»:

```
NEW EXHIBITION → OLD EXHIBITION REMOVED → OLD EXHIBITS NO LONGER NEEDED
→ STORED / DEACCESSIONED / SURPLUS → POSSIBLE TRANSFER → CONTACT → ACQUISITION
```

У каждого утверждения есть первоисточник (URL, дата источника, дата обращения, выдержка).
Приоритеты A/B/C вычисляются только из сигналов доказательств.

## Результаты (research run 2026-09-30)

| Показатель | Значение |
|---|---|
| Музеев исследовано | **102** |
| Стран | **29** |
| Записей-доказательств (источников) | **187** |
| Музеев с реконструкцией / заменой / закрытием | 87 |
| **A** — прямые возможности | 8 музеев, 12 экспонатов/лотов |
| **B** — потенциальные возможности | 53 |
| **C** — лиды | 35 |
| Контактов (email/телефон/страница) | 23 (14 музеев) |

- Отчёт: [`reports/2026-09-30-expansion-100/REPORT.md`](reports/2026-09-30-expansion-100/REPORT.md)
  (6 разделов: Exhibit Opportunities, Museum Leads, Contact List, Sources, Outreach Drafts, Statistics)
- Карточки музеев с ответами на 8 вопросов AI Research Logic:
  [`reports/2026-09-30-expansion-100/MUSEUM_CARDS.md`](reports/2026-09-30-expansion-100/MUSEUM_CARDS.md)
- Готовые письма: `reports/2026-09-30-expansion-100/outreach/*.md`
- База: `exports/museum_finder.xlsx` (листы Database, Exhibit Opportunities, Museum Leads,
  Contacts, Sources, Statistics) и CSV в `exports/`, контакты — `contacts/contacts.csv`
- Пилот (21 музей): `reports/2026-09-30-pilot/`

### ⚠️ Ограничение этого прогона

Среда, в которой выполнялось исследование, блокировала прямую загрузку веб-страниц (egress proxy).
Поэтому все доказательства получены из **сводок поисковой выдачи** и помечены
`verified_via: web_search_snippet`, а выдержки — пересказ (`excerpt_is_verbatim: false`).
**Перед отправкой любого письма откройте ссылку-источник и подтвердите факт.**
На машине с открытым интернетом `mef collect` загружает сами страницы (trafilatura/pypdf) и
сохраняет текст для проверки.

## Структура проекта

```
museum-exhibit-finder/
├── config/        settings.yaml, lexicon.yaml (14 языков), queries.yaml (шаблоны + watchlist)
├── data/          museum_finder.db (SQLite, генерируется)
├── research/
│   ├── museums/   1 YAML = 1 музей: museum → exhibitions → exhibits + evidence + contacts
│   └── inbox/     черновики от `mef triage` (до проверки)
├── sources/       кэш страниц и журнал загрузок
├── contacts/      contacts.csv
├── reports/       отчёты по прогонам + outreach-письма
├── exports/       CSV + XLSX
├── scripts/       run_pipeline.sh
├── docs/          TOOLS_SURVEY.md (обзор GitHub-проектов), ARCHITECTURE.md
├── src/mef/       код пайплайна
└── tests/         pytest
```

## Установка и запуск

```bash
cd museum-exhibit-finder
pip install -e ".[discovery,dev]"      # + ".[llm]" для Claude-классификатора
python -m pytest                        # 30 тестов

# Офлайн: база знаний → БД → экспорт → отчёт
mef all --label my-run

# Discovery (нужен интернет)
mef queries --group watchlist           # посмотреть запросы
mef search --group deaccession --limit 40
mef collect --min-relevance 2 --limit 100      # fetch + parse + classify (+ --llm)
mef triage                                     # черновики в research/inbox/
# проверить черновик → заполнить карточку → перенести в research/museums/ → mef all

# Просмотр базы в браузере (опционально)
pip install datasette && datasette data/museum_finder.db
```

Полный прогон: `scripts/run_pipeline.sh <label> [--discover]`.

## Модули (`src/mef/`)

| # | Модуль | Что делает |
|---|---|---|
| 1 | `search.py` | генерация запросов (шаблоны × языки × страны × типы экспонатов) и поиск через ddgs / SearXNG / импорт JSON-CSV |
| 2 | `collector.py` | вежливая загрузка страниц (robots.txt, задержки, кэш, журнал), fallback на Wayback Machine |
| 3 | `parser.py` | извлечение текста и даты: trafilatura (HTML), pypdf (PDF) |
| 4 | `classifier.py` | мультиязычные сигналы цепочки, «это музей?», фильтр коммерческих продавцов, стадия 0–5, кандидат A?/B?/C? |
| 5 | `dedupe.py` | канонические URL, регистрируемый домен, city-aware fuzzy-сравнение названий (RapidFuzz) |
| 6 | `contacts.py` | email (в т.ч. `name [at] domain`), телефоны, LinkedIn, должности — всегда с URL-источником |
| 7 | `exhibits.py` | предложения об экспонатах + категории (physics…automotive…simulator…) |
| 8 | `evidence.py` | загрузка/валидация базы знаний, агрегирование сигналов, первичный источник |
| 9 | `exporter.py` | CSV + XLSX со всеми обязательными полями DATABASE |
| 10 | `report.py` | 6 разделов отчёта, карточки музеев, outreach-письма, статистика |
| – | `priority.py` | A/B/C и 8 ответов AI Research Logic только из доказательств |
| – | `llm.py` | опциональная проверка страниц Claude (structured outputs + проверка дословности цитат) |

## Правила приоритета (строго по доказательствам)

- **A — DIRECT OPPORTUNITY**: источник прямо говорит, что объект продаётся / передаётся /
  предлагается другим музеям / в процессе deaccession, и предложение актуально.
- **B — POTENTIAL OPPORTUNITY**: старые экспонаты сняты/заменены/на складе, судьба неизвестна;
  а также: доступность устарела (>3 лет), **окно предложения закрыто** (`valid_until` в прошлом),
  или доступность известна **только из соцсетей/форумов** (нужно подтверждение на официальном сайте).
- **C — LEAD**: только реконструкция / новая экспозиция / переезд / опубликованная программа deaccession.

Если доступность не подтверждена: *«Potential lead — availability not confirmed.»*
Если поле неизвестно: *«Unknown — further research required.»*

## Как добавить музей вручную

Скопируйте любой файл из `research/museums/`, заполните поля; каждое утверждение — отдельная
запись `evidence` с `url`, `accessed`, `claim`, `signals`. Затем `mef validate && mef all`.
Схема строгая (`extra="forbid"`): опечатки в полях и ссылки на несуществующие доказательства
ловятся при валидации.

## Регулярный мониторинг

Регистры передачи объектов обновляются постоянно, а объявления живут ~2 месяца
(пример: BAC 1-11 в Шотландии предлагался 5 месяцев и был разрезан, когда никто не откликнулся).
Раз в неделю: `mef search --group watchlist && mef collect && mef triage`.
