"""SQLite storage.

Knowledge tables (museums, exhibitions, exhibits, evidence, contacts) are
rebuilt from ``research/museums/*.yaml`` on every ``mef build`` so the YAML
files stay the single source of truth. Discovery tables (search_results,
pages) persist between runs.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import PATHS
from .dedupe import canonical_url, registered_domain
from .evidence import load_research
from .models import MuseumFile
from .priority import assess_exhibit, assess_museum

KNOWLEDGE_SCHEMA = """
DROP TABLE IF EXISTS exhibit_evidence;
DROP TABLE IF EXISTS exhibits;
DROP TABLE IF EXISTS exhibitions;
DROP TABLE IF EXISTS evidence;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS museums;

CREATE TABLE museums (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, name_local TEXT, aliases TEXT,
  country TEXT, city TEXT, website TEXT, domain TEXT, type TEXT, parent_org TEXT,
  general_email TEXT, phone TEXT, linkedin TEXT, notes TEXT,
  priority TEXT, stage INTEGER, availability TEXT,
  outreach_status TEXT, next_step TEXT, last_updated TEXT, file TEXT
);
CREATE TABLE exhibitions (
  pk INTEGER PRIMARY KEY, museum_id TEXT REFERENCES museums(id), id TEXT, name TEXT,
  gallery TEXT, opening_year TEXT, replacement_year TEXT, new_exhibition TEXT,
  old_exhibition TEXT, status TEXT, notes TEXT, UNIQUE(museum_id, id)
);
CREATE TABLE exhibits (
  pk INTEGER PRIMARY KEY, museum_id TEXT REFERENCES museums(id), exhibition_pk INTEGER
  REFERENCES exhibitions(pk), id TEXT, name TEXT, description TEXT, category TEXT,
  manufacturer TEXT, year TEXT, approx_age TEXT, dimensions TEXT, weight TEXT,
  interactive INTEGER, condition TEXT, educational_purpose TEXT, quantity TEXT,
  photos TEXT, video TEXT, documentation TEXT, status TEXT, fit_for_tpm TEXT, notes TEXT,
  priority TEXT, availability TEXT, UNIQUE(exhibition_pk, id)
);
CREATE TABLE evidence (
  pk INTEGER PRIMARY KEY, museum_id TEXT REFERENCES museums(id), id TEXT, url TEXT,
  canonical_url TEXT, title TEXT, publisher TEXT, source_type TEXT, source_date TEXT,
  accessed TEXT, language TEXT, claim TEXT, excerpt TEXT, excerpt_is_verbatim INTEGER,
  signals TEXT, verified_via TEXT, notes TEXT, UNIQUE(museum_id, id)
);
CREATE TABLE exhibit_evidence (
  exhibit_pk INTEGER REFERENCES exhibits(pk), evidence_pk INTEGER REFERENCES evidence(pk),
  PRIMARY KEY (exhibit_pk, evidence_pk)
);
CREATE TABLE contacts (
  pk INTEGER PRIMARY KEY, museum_id TEXT REFERENCES museums(id), name TEXT, position TEXT,
  email TEXT, phone TEXT, linkedin TEXT, contact_page TEXT, kind TEXT, source_url TEXT
);
"""

DISCOVERY_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_results (
  pk INTEGER PRIMARY KEY, query TEXT, url TEXT, canonical_url TEXT, title TEXT,
  snippet TEXT, engine TEXT, rank INTEGER, lang TEXT, retrieved TEXT,
  classification TEXT, relevance REAL, priority TEXT,
  UNIQUE(query, canonical_url)
);
CREATE TABLE IF NOT EXISTS pages (
  canonical_url TEXT PRIMARY KEY, url TEXT, fetched_at TEXT, status INTEGER,
  content_type TEXT, via TEXT, title TEXT, date TEXT, text TEXT,
  classification TEXT, relevance REAL, priority TEXT, contacts TEXT, mentions TEXT
);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(canonical_url UNINDEXED, title, text);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or PATHS.db
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DISCOVERY_SCHEMA)
    try:
        conn.executescript(FTS_SCHEMA)
    except sqlite3.OperationalError:
        pass  # SQLite built without FTS5 — full-text search just isn't available
    return conn


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def insert_museum_file(conn: sqlite3.Connection, mf: MuseumFile, file: str = "") -> None:
    m = mf.museum
    a = assess_museum(mf)
    conn.execute(
        "INSERT INTO museums VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            m.id, m.name, m.name_local, _j(m.aliases), m.country, m.city, m.website,
            registered_domain(m.website), m.type, m.parent_org, m.general_email, m.phone,
            m.linkedin, m.notes, a.priority, a.stage, a.availability,
            mf.research.outreach_status, mf.research.next_step, mf.research.last_updated, file,
        ),
    )
    ev_pk: dict[str, int] = {}
    for e in mf.evidence:
        cur = conn.execute(
            "INSERT INTO evidence (museum_id,id,url,canonical_url,title,publisher,source_type,"
            "source_date,accessed,language,claim,excerpt,excerpt_is_verbatim,signals,verified_via,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                m.id, e.id, e.url, canonical_url(e.url), e.title, e.publisher, e.source_type,
                e.source_date, e.accessed, e.language, e.claim, e.excerpt, int(e.excerpt_is_verbatim),
                _j(list(e.signals)), e.verified_via, e.notes,
            ),
        )
        ev_pk[e.id] = cur.lastrowid
    for ex in mf.exhibitions:
        cur = conn.execute(
            "INSERT INTO exhibitions (museum_id,id,name,gallery,opening_year,replacement_year,"
            "new_exhibition,old_exhibition,status,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (m.id, ex.id, ex.name, ex.gallery, ex.opening_year, ex.replacement_year,
             ex.new_exhibition, ex.old_exhibition, ex.status, ex.notes),
        )
        exhibition_pk = cur.lastrowid
        for item in ex.exhibits:
            ia = assess_exhibit(mf, item)
            cur = conn.execute(
                "INSERT INTO exhibits (museum_id,exhibition_pk,id,name,description,category,manufacturer,"
                "year,approx_age,dimensions,weight,interactive,condition,educational_purpose,quantity,"
                "photos,video,documentation,status,fit_for_tpm,notes,priority,availability)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    m.id, exhibition_pk, item.id, item.name, item.description, _j(item.category),
                    item.manufacturer, item.year, item.approx_age, item.dimensions, item.weight,
                    None if item.interactive is None else int(item.interactive), item.condition,
                    item.educational_purpose, item.quantity, _j(item.photos), _j(item.video),
                    _j(item.documentation), item.status, item.fit_for_tpm, item.notes,
                    ia.priority, ia.availability,
                ),
            )
            for ref in item.evidence:
                conn.execute("INSERT OR IGNORE INTO exhibit_evidence VALUES (?,?)", (cur.lastrowid, ev_pk[ref]))
    for c in mf.contacts:
        src = c.source if c.source.startswith("http") else next(
            (e.url for e in mf.evidence if e.id == c.source), c.source
        )
        conn.execute(
            "INSERT INTO contacts (museum_id,name,position,email,phone,linkedin,contact_page,kind,source_url)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (m.id, c.name, c.position, c.email, c.phone, c.linkedin, c.contact_page, c.kind, src),
        )


def build(conn: sqlite3.Connection | None = None) -> tuple[int, list[tuple[Path, str]]]:
    """Rebuild knowledge tables from YAML. Returns (museums loaded, errors)."""
    conn = conn or connect()
    loaded = load_research()
    conn.executescript(KNOWLEDGE_SCHEMA)
    ids: set[str] = set()
    errors = list(loaded.errors)
    for path, mf in loaded.files:
        if mf.museum.id in ids:
            errors.append((path, f"duplicate museum id {mf.museum.id!r}"))
            continue
        ids.add(mf.museum.id)
        insert_museum_file(conn, mf, path.name)
    conn.commit()
    return len(ids), errors
