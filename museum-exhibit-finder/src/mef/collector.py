"""[2] Source collector.

Polite page fetching: identifies itself, honours robots.txt, waits between
requests to the same host, caches every response on disk and logs every
fetch to ``sources/source_log.jsonl``. Falls back to the Wayback Machine for
pages that are gone (typical for old gallery pages after a renovation).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
import urllib.robotparser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .config import PATHS, settings
from .dedupe import canonical_url

_last_hit: dict[str, float] = {}


@dataclass
class Fetched:
    url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    via: str  # live | cache | wayback
    fetched_at: str


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(canonical_url(url).encode()).hexdigest()[:32]
    return PATHS.cache / h[:2] / h


@lru_cache(maxsize=512)
def _robots(host_root: str) -> urllib.robotparser.RobotFileParser | None:
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = requests.get(f"{host_root}/robots.txt", timeout=10,
                            headers={"User-Agent": settings().fetch.get("user_agent", "mef")})
        if resp.status_code >= 400:
            return None
        rp.parse(resp.text.splitlines())
        return rp
    except requests.RequestException:
        return None


def allowed(url: str) -> bool:
    if not settings().fetch.get("respect_robots_txt", True):
        return True
    p = urlsplit(url)
    rp = _robots(f"{p.scheme}://{p.netloc}")
    return True if rp is None else rp.can_fetch(settings().fetch.get("user_agent", "mef"), url)


def _log(entry: dict) -> None:
    PATHS.source_log.parent.mkdir(parents=True, exist_ok=True)
    with PATHS.source_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _throttle(url: str) -> None:
    host = urlsplit(url).netloc
    delay = float(settings().fetch.get("delay_seconds", 2.0))
    wait = _last_hit.get(host, 0) + delay - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def wayback_snapshot(url: str, timestamp: str | None = None) -> str | None:
    """Closest archived snapshot URL (Wayback availability API)."""
    params = {"url": url}
    if timestamp:
        params["timestamp"] = timestamp
    try:
        r = requests.get("https://archive.org/wayback/available", params=params, timeout=20)
        snap = r.json().get("archived_snapshots", {}).get("closest")
        return snap["url"] if snap and snap.get("available") else None
    except (requests.RequestException, ValueError):
        return None


def fetch(url: str, use_cache: bool = True) -> Fetched | None:
    cfg = settings().fetch
    path = _cache_path(url)
    meta_path = path.with_suffix(".json")
    if use_cache and path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return Fetched(url, meta["final_url"], meta["status"], meta["content_type"],
                       path.read_bytes(), "cache", meta["fetched_at"])

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    headers = {"User-Agent": cfg.get("user_agent", "mef"), "Accept-Language": "en,*;q=0.5"}
    result: Fetched | None = None
    if allowed(url):
        _throttle(url)
        try:
            resp = requests.get(url, headers=headers, timeout=float(cfg.get("timeout_seconds", 25)),
                                stream=True)
            body = resp.raw.read(int(cfg.get("max_bytes", 15_000_000)), decode_content=True)
            result = Fetched(url, resp.url, resp.status_code, resp.headers.get("content-type", ""),
                             body, "live", now)
        except requests.RequestException as exc:
            _log({"url": url, "at": now, "error": str(exc)})
    else:
        _log({"url": url, "at": now, "skipped": "robots.txt"})

    if (result is None or result.status >= 400) and cfg.get("wayback_fallback", True):
        snap = wayback_snapshot(url)
        if snap:
            try:
                _throttle(snap)
                resp = requests.get(snap, headers=headers, timeout=float(cfg.get("timeout_seconds", 25)))
                result = Fetched(url, snap, resp.status_code, resp.headers.get("content-type", ""),
                                 resp.content, "wayback", now)
            except requests.RequestException as exc:
                _log({"url": snap, "at": now, "error": str(exc)})

    if result is None:
        return None
    _log({"url": url, "final_url": result.final_url, "status": result.status, "via": result.via,
          "at": now, "bytes": len(result.body)})
    if result.status < 400:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.body)
        meta_path.write_text(json.dumps({"final_url": result.final_url, "status": result.status,
                                         "content_type": result.content_type, "fetched_at": now,
                                         "via": result.via}))
    return result
