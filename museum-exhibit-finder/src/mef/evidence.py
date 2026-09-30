"""[8] Evidence tracker.

Loads the curated knowledge base (``research/museums/*.yaml``), validates it
against :mod:`mef.models`, and aggregates the signals each museum / exhibit is
backed by. Nothing downstream (priority, report, export) reads free text to
make a decision — only these evidence-backed signals.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from .config import PATHS
from .models import Evidence, Exhibit, MuseumFile


@dataclass
class LoadResult:
    files: list[tuple[Path, MuseumFile]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


def load_research(directory: Path | None = None) -> LoadResult:
    directory = directory or PATHS.research
    result = LoadResult()
    for path in sorted(directory.glob("*.yaml")):
        try:
            with path.open(encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            result.files.append((path, MuseumFile.model_validate(raw)))
        except (ValidationError, yaml.YAMLError, ValueError) as exc:
            result.errors.append((path, str(exc)))
    return result


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    parts = [int(p) for p in value.split("-")]
    while len(parts) < 3:
        parts.append(1)
    return dt.date(*parts)


def age_years(ev: Evidence, today: dt.date | None = None) -> float | None:
    d = parse_date(ev.source_date)
    if d is None:
        return None
    today = today or dt.date.today()
    return (today - d).days / 365.25


def signals_of(evs: list[Evidence]) -> set[str]:
    out: set[str] = set()
    for e in evs:
        out.update(e.signals)
    return out


def exhibit_evidence(mf: MuseumFile, exhibit: Exhibit) -> list[Evidence]:
    by_id = mf.evidence_by_id()
    return [by_id[i] for i in exhibit.evidence if i in by_id]


def unattached_evidence(mf: MuseumFile) -> list[Evidence]:
    """Evidence not tied to any exhibition or exhibit — counts at museum level."""
    used: set[str] = set()
    for ex in mf.exhibitions:
        used.update(ex.evidence)
        for item in ex.exhibits:
            used.update(item.evidence)
    return [e for e in mf.evidence if e.id not in used]


def primary_source(evs: list[Evidence]) -> Evidence | None:
    """Most authoritative, most recent source among ``evs``."""
    rank = {
        "official_site": 0, "press_release": 0, "annual_report": 1, "board_document": 1,
        "procurement": 1, "government": 1, "collection_database": 1, "association": 2,
        "trade_press": 3, "news": 3, "archive": 4, "social_media": 5, "forum": 5, "other": 6,
    }
    if not evs:
        return None
    return sorted(
        evs,
        key=lambda e: (rank.get(e.source_type, 9), -(parse_date(e.source_date) or dt.date.min).toordinal()),
    )[0]
