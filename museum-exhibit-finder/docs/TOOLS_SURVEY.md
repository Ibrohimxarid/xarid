# Обзор open-source инструментов (GitHub) для Exhibit Acquisition Finder

Дата обзора: 2026-09-30. Цель: не изобретать заново то, что уже существует, и взять
в проект только то, что реально нужно для цепочки
`MUSEUM → RENOVATION → OLD EXHIBITS → FATE → AVAILABILITY → CONTACT`.

## Итоговое решение (кратко)

| Задача | Берём | Почему | Статус в проекте |
|---|---|---|---|
| Поиск (search aggregation) | **ddgs** (deedy5/ddgs) | Метапоиск без API-ключей (DuckDuckGo, Bing, Brave, Google, Mojeek, Wikipedia…), MIT, `pip install ddgs` | backend `ddgs` в `mef.search` |
| Поиск на своём сервере | **SearXNG** (searxng/searxng) | Self-hosted метапоиск с JSON API; для больших объёмов и стабильности. AGPL — запускаем отдельным Docker-сервисом и ходим по HTTP, код не смешиваем | backend `searxng` в `mef.search` |
| Извлечение текста и даты со страниц | **trafilatura** (adbar/trafilatura) | Лучший по бенчмаркам extractor основного текста + метаданные (дата публикации, автор, заголовок); умеет sitemaps/RSS для обхода новостных разделов музеев. Apache-2.0 | `mef.parser` |
| PDF (годовые отчёты, board papers, тендеры) | **pypdf** (по умолчанию), **docling** (опционально) | pypdf лёгкий и без ML; docling (IBM) — для сложных таблиц/сканов, но тяжёлый (модели) | `mef.parser` (pypdf), docling — hook |
| Архивные страницы | **Wayback Machine API** (подход waybackpy / edgi wayback) | Страницы старых галерей часто исчезают после реконструкции — архив нужен именно для «что было раньше» | `mef.collector.wayback_snapshot()` (прямой вызов API без лишней зависимости) |
| JS-сайты | **Playwright** (microsoft/playwright-python), опц. **crawl4ai** | Некоторые сайты музеев рендерятся JS; Playwright — надёжный headless-браузер; crawl4ai — обёртка «сайт → Markdown для LLM» | опциональный fetch-backend |
| Дубликаты | **RapidFuzz** (rapidfuzz/RapidFuzz) + **tldextract** | Быстрый fuzzy matching названий (MIT), регистрируемый домен сайта как сильный ключ | `mef.dedupe` |
| Валидация структуры | **pydantic** | Строгая схема карточек музея/экспоната/доказательства; ошибки видны сразу | `mef.models` |
| Хранилище + полнотекстовый поиск | **SQLite + FTS5** (встроено в Python) | Ноль инфраструктуры; FTS5 даёт поиск по всем собранным страницам | `mef.db` |
| Просмотр базы командой | **Datasette** (simonw/datasette) | Одна команда — и база доступна в браузере с фильтрами/фасетами/CSV | `datasette data/museum_finder.db` |
| Excel | **openpyxl** | XLSX-экспорт с листами и фильтрами | `mef.exporter` |
| LLM-классификация (опционально) | **Anthropic Claude API** (`anthropic` SDK, structured outputs) | Ответы на 8 вопросов AI Research Logic в строгой JSON-схеме; каждая цитата проверяется на дословное присутствие в тексте страницы (анти-галлюцинации) | `mef.llm` |

## Что рассмотрели и НЕ взяли в ядро

| Репозиторий | Что это | Почему не в ядре |
|---|---|---|
| assafelovic/gpt-researcher | Автономный агент «планировщик → исполнители → отчёт» | Выдаёт нарративный отчёт; нам нужна **структурированная база** с доказательством на каждое утверждение и контролем дубликатов. Взяли идею: план → расширение запросов → сбор доказательств → отчёт с цитатами |
| stanford-oval/storm | LLM-система, пишущая статьи в стиле Википедии с цитатами | Та же причина; риск «гладких» выводов без подтверждения |
| unclecode/crawl4ai | Краулер «сайт → Markdown для LLM» | Хорош, но тянет браузер и тяжёлые зависимости; trafilatura хватает для 90% страниц. Оставлен как опциональный fallback |
| firecrawl/firecrawl | Scrape/crawl API | Хостинг/AGPL self-host с Redis/воркерами — избыточно для сотен страниц |
| ScrapeGraphAI/Scrapegraph-ai | LLM-скрапер по промпту | LLM-вызов на каждую страницу = дорого и недетерминированно; у нас правило-ориентированный классификатор + LLM только для кандидатов |
| browser-use/browser-use | Агент, управляющий браузером | Не нужен интерактив (логины, формы); статического чтения достаточно |
| scrapy/scrapy | Фреймворк краулинга | Оправдан для полного обхода тысяч сайтов; у нас точечные fetch'и. Путь масштабирования, если понадобится |
| dedupeio/dedupe, moj-analytical-services/splink | ML/вероятностная связка записей | Рассчитаны на десятки тысяч записей и обучение; на сотнях музеев RapidFuzz + домен + страна точнее и прозрачнее. Splink — путь масштабирования |
| TheScrapper и др. email/phone-скрейперы | Регулярки для email/телефонов | Маленькие неподдерживаемые скрипты; нам важнее **привязка контакта к URL-источнику** и деобфускация `name [at] museum.org` — реализовано в `mef.contacts` (~80 строк) |
| chroma-core/chroma, lancedb/lancedb | Векторные БД | Семантический поиск пригодится при >10k страниц; сейчас FTS5 достаточно. Точка расширения |

## Источники данных (не код, но ключевые «репозитории» информации)

Проверяются в ходе исследования и фиксируются в `research/museums/*.yaml` только при
наличии подтверждающего URL:

- UK: Museums Association — площадка **Find an Object** (объявления о передаче/утилизации объектов между музеями, обязательна по кодексу этики MA);
- Нидерланды: национальная база передачи музейных объектов (LAMO / Museumvereniging «Afstotingsdatabase»);
- ASTC (США) и Ecsite (Европа): каталоги touring exhibitions, форумы сообщества;
- ICOM, AAM, национальные музейные ассоциации — политики deaccession и объявления;
- Годовые отчёты, board papers, тендерная документация (TED, Contracts Finder, SAM.gov) — именно там пишут «existing exhibits will be removed / decommissioned».

## Ссылки на репозитории

- https://github.com/adbar/trafilatura
- https://github.com/deedy5/ddgs
- https://github.com/searxng/searxng
- https://github.com/unclecode/crawl4ai
- https://github.com/microsoft/playwright-python
- https://github.com/docling-project/docling
- https://github.com/rapidfuzz/RapidFuzz
- https://github.com/dedupeio/dedupe
- https://github.com/moj-analytical-services/splink
- https://github.com/akamhy/waybackpy
- https://github.com/edgi-govdata-archiving/wayback
- https://github.com/simonw/datasette
- https://github.com/assafelovic/gpt-researcher
- https://github.com/stanford-oval/storm
- https://github.com/firecrawl/firecrawl
- https://github.com/ScrapeGraphAI/Scrapegraph-ai
- https://github.com/browser-use/browser-use
- https://github.com/scrapy/scrapy
- https://github.com/chroma-core/chroma
- https://github.com/lancedb/lancedb
- https://github.com/champmq/TheScrapper
