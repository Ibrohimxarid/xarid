"""Project paths and settings (``config/settings.yaml``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("MEF_ROOT", Path(__file__).resolve().parents[2]))


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT
    config: Path = ROOT / "config"
    data: Path = ROOT / "data"
    research: Path = ROOT / "research" / "museums"
    inbox: Path = ROOT / "research" / "inbox"
    sources: Path = ROOT / "sources"
    cache: Path = ROOT / "sources" / "cache"
    contacts: Path = ROOT / "contacts"
    reports: Path = ROOT / "reports"
    exports: Path = ROOT / "exports"

    @property
    def db(self) -> Path:
        return self.data / "museum_finder.db"

    @property
    def source_log(self) -> Path:
        return self.sources / "source_log.jsonl"


PATHS = Paths()


@dataclass
class Settings:
    museum_profile: dict = field(default_factory=dict)
    priority: dict = field(default_factory=dict)
    fetch: dict = field(default_factory=dict)
    search: dict = field(default_factory=dict)
    llm: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    @property
    def availability_max_age_years(self) -> int:
        return int(self.priority.get("availability_max_age_years", 3))


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def settings() -> Settings:
    raw = _read_yaml(PATHS.config / "settings.yaml")
    return Settings(
        museum_profile=raw.get("museum_profile", {}),
        priority=raw.get("priority", {}),
        fetch=raw.get("fetch", {}),
        search=raw.get("search", {}),
        llm=raw.get("llm", {}),
        raw=raw,
    )


def load_yaml(name: str) -> dict:
    return _read_yaml(PATHS.config / name)
