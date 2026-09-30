"""[1] Search engine.

Generates queries from ``config/queries.yaml`` (templates × languages ×
geographies × exhibit types) and runs them through a pluggable backend:

* ``ddgs``    — metasearch library (no API key), https://github.com/deedy5/ddgs
* ``searxng`` — self-hosted SearXNG JSON API, https://github.com/searxng/searxng
* ``import``  — JSON/JSONL/CSV of results gathered elsewhere (by a person or
  an AI research agent), so every discovery path lands in the same table.

Results are de-duplicated by canonical URL per query and classified on the
snippet immediately, so the most promising URLs are fetched first.
"""

from __future__ import annotations

import csv
import datetime as dt
import itertools
import json
import time
from pathlib import Path
from typing import Iterable, Iterator

import requests

from .classifier import classify
from .config import load_yaml, settings
from .dedupe import canonical_url
from .models import SearchResult


def build_queries(
    groups: Iterable[str] | None = None,
    languages: Iterable[str] | None = None,
    countries: Iterable[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Expand query templates. Returns dicts: {query, group, lang, country}."""
    cfg = load_yaml("queries.yaml")
    langs = set(languages) if languages else None
    wanted_groups = set(groups) if groups else None
    geo = cfg.get("geography", {})
    selected_countries = list(countries) if countries else list(geo)
    out: list[dict] = []
    seen: set[str] = set()

    def push(q: str, group: str, lang: str, country: str | None) -> None:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            out.append({"query": q, "group": group, "lang": lang, "country": country})

    for group, spec in cfg.get("groups", {}).items():
        if wanted_groups and group not in wanted_groups:
            continue
        for lang, templates in spec.items():
            if langs and lang not in langs:
                continue
            for t in templates:
                if "{country}" in t or "{city}" in t or "{institution}" in t:
                    for country in selected_countries:
                        g = geo.get(country, {})
                        if lang != "en" and g.get("lang") != lang:
                            continue
                        for city in (g.get("cities") or [None]) if "{city}" in t else [None]:
                            for inst in (g.get("institutions") or [None]) if "{institution}" in t else [None]:
                                q = t.format(country=g.get("name", country), city=city or "", institution=inst or "")
                                push(" ".join(q.split()), group, lang, country)
                else:
                    push(t, group, lang, None)
    for combo in cfg.get("exhibit_type_combos", []):
        for a, b in itertools.product(combo["events"], combo["types"]):
            push(f"{a} {b}", "exhibit_types", "en", None)
    return out[:limit] if limit else out


# ---- backends -----------------------------------------------------------------


def _ddgs(query: str, n: int, region: str = "wt-wt") -> Iterator[dict]:
    try:
        from ddgs import DDGS
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise SystemExit("ddgs is not installed: pip install ddgs") from exc
    for r in DDGS().text(query, region=region, max_results=n):
        yield {"url": r.get("href") or r.get("url"), "title": r.get("title"), "snippet": r.get("body")}


def _searxng(query: str, n: int, lang: str | None = None) -> Iterator[dict]:
    base = settings().search.get("searxng_url", "http://localhost:8888").rstrip("/")
    params = {"q": query, "format": "json"}
    if lang:
        params["language"] = lang
    resp = requests.get(f"{base}/search", params=params, timeout=30)
    resp.raise_for_status()
    for r in resp.json().get("results", [])[:n]:
        yield {"url": r.get("url"), "title": r.get("title"), "snippet": r.get("content")}


def run_search(queries: list[dict], backend: str | None = None, per_query: int | None = None) -> list[SearchResult]:
    backend = backend or settings().search.get("backend", "ddgs")
    per_query = per_query or int(settings().search.get("results_per_query", 10))
    delay = float(settings().search.get("delay_seconds", 2.0))
    today = dt.date.today().isoformat()
    results: list[SearchResult] = []
    for q in queries:
        try:
            if backend == "ddgs":
                hits = list(_ddgs(q["query"], per_query))
            elif backend == "searxng":
                hits = list(_searxng(q["query"], per_query, q.get("lang")))
            else:
                raise SystemExit(f"unknown search backend {backend!r}")
        except SystemExit:
            raise
        except Exception as exc:  # network errors, rate limits: log and continue
            print(f"  ! search failed for {q['query']!r}: {exc}")
            hits = []
        for rank, h in enumerate(hits, start=1):
            if not h.get("url"):
                continue
            results.append(SearchResult(query=q["query"], url=h["url"], title=h.get("title"),
                                        snippet=h.get("snippet"), engine=backend, rank=rank,
                                        lang=q.get("lang"), retrieved=today))
        time.sleep(delay)
    return results


def import_results(path: Path) -> list[SearchResult]:
    """Load results collected outside the pipeline (JSON list, JSONL or CSV)."""
    today = dt.date.today().isoformat()
    rows: list[dict]
    if path.suffix == ".csv":
        with path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    elif path.suffix == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for r in rows:
        out.append(SearchResult(query=r.get("query", "imported"), url=r["url"], title=r.get("title"),
                                snippet=r.get("snippet"), engine=r.get("engine", "import"),
                                rank=int(r["rank"]) if r.get("rank") else None, lang=r.get("lang"),
                                retrieved=r.get("retrieved", today)))
    return out


def store_results(conn, results: list[SearchResult]) -> int:
    """Insert results (dedup by query + canonical URL) with a snippet classification."""
    added = 0
    for r in results:
        c = classify(r.url, r.snippet or "", r.title or "")
        cur = conn.execute(
            "INSERT OR IGNORE INTO search_results (query,url,canonical_url,title,snippet,engine,rank,lang,"
            "retrieved,classification,relevance,priority) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (r.query, r.url, canonical_url(r.url), r.title, r.snippet, r.engine, r.rank, r.lang,
             r.retrieved, c.model_dump_json(), c.relevance, c.priority),
        )
        added += cur.rowcount
    conn.commit()
    return added
