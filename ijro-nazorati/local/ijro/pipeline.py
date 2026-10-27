"""Kiruvchi papkani kuzatish va hujjatlarni navbat bilan o'qish (fon oqimida)."""
from __future__ import annotations

import csv
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from .extract import Extractor
from .pages import SUPPORTED_EXTENSIONS
from .storage import ERROR, PROCESSING, QUEUED, READY, Doc, Store

log = logging.getLogger(__name__)

# Fayl shuncha soniya o'zgarmasa, nusxalash tugagan deb hisoblanadi.
STABLE_SECONDS = 3


def journal(path: Path, action: str, reg_no: str = "", details: str = "") -> None:
    """Mahalliy jurnal: faqat vaqt, amal va ro'yxat raqami — hujjat mazmuni yozilmaydi."""
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(["Vaqt", "Amal", "Ro'yxat raqami", "Tafsilot"])
        w.writerow([datetime.now().isoformat(sep=" ", timespec="seconds"), action, reg_no, details])


def _ignored(path: Path) -> bool:
    name = path.name
    return (name.startswith((".", "~$")) or path.suffix.lower() in {".tmp", ".part", ".crdownload"})


class Pipeline:
    def __init__(self, cfg, store: Store, extractor: Extractor):
        self.cfg = cfg
        self.store = store
        self.extractor = extractor
        self._seen: dict[str, tuple[int, float, float]] = {}
        self._stop = threading.Event()
        self._wake = threading.Event()
        # Dastur to'satdan yopilgan bo'lsa, chala qolgan hujjat qayta navbatga qo'yiladi.
        for doc in self.store.list():
            if doc.status == PROCESSING:
                doc.status = QUEUED
                self.store.save(doc)

    def scan_inbox(self, now: float | None = None) -> list[Doc]:
        """Yangi, nusxalanib bo'lgan fayllar uchun navbatga yozuv yaratadi."""
        now = time.time() if now is None else now
        known = {d.source_path for d in self.store.list()}
        created = []
        for path in sorted(self.cfg.inbox_dir.iterdir()):
            if not path.is_file() or _ignored(path) or str(path) in known:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            key = str(path)
            size, mtime, first = self._seen.get(key, (-1, -1.0, now))
            if (size, mtime) != (stat.st_size, stat.st_mtime):
                self._seen[key] = (stat.st_size, stat.st_mtime, now)
                continue
            if now - first < STABLE_SECONDS:
                continue
            self._seen.pop(key, None)
            doc = self.store.create(path)
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                doc.status = ERROR
                doc.message = ("Bu format o'qilmaydi. PDF, JPG, PNG yoki TIFF yuklang "
                               "yoki maydonlarni qo'lda to'ldiring.")
                self.store.save(doc)
            created.append(doc)
        return created

    def next_queued(self) -> Doc | None:
        return next((d for d in self.store.list() if d.status == QUEUED), None)

    def process(self, doc: Doc) -> Doc:
        model = doc.model or None
        doc.status = PROCESSING
        doc.message = "O'qilmoqda..."
        self.store.save(doc)
        started = time.time()
        try:
            result = self.extractor.run(Path(doc.source_path), self.store.doc_dir(doc.id), model)
        except Exception as err:  # noqa: BLE001 — har qanday xato xodimga ko'rsatiladi
            log.exception("Hujjatni o'qib bo'lmadi: %s", doc.file_name)
            doc = self.store.get(doc.id) or doc
            doc.status = ERROR
            doc.message = f"Avtomatik o'qib bo'lmadi: {err}. Maydonlarni qo'lda to'ldiring yoki qayta o'qing."
            self.store.save(doc)
            return doc
        doc = self.store.get(doc.id) or doc
        doc.fields.update(result.fields)
        doc.checks = result.checks
        doc.pages = result.pages
        doc.model = model or self.cfg.model
        doc.status = READY
        doc.message = f"O'qildi ({int(time.time() - started)} s). Hujjat bilan solishtiring."
        doc.rev += 1
        self.store.save(doc)
        return doc

    def request_reread(self, doc_id: str, model: str | None = None) -> None:
        doc = self.store.get(doc_id)
        if not doc or doc.status == PROCESSING:
            return
        doc.status = QUEUED
        doc.model = model or ""
        doc.message = "Navbatda"
        self.store.save(doc)
        self._wake.set()

    def run_forever(self, interval: float = 2.0) -> None:
        while not self._stop.is_set():
            try:
                self.scan_inbox()
                doc = self.next_queued()
                if doc:
                    self.process(doc)
                    continue
            except Exception:  # noqa: BLE001
                log.exception("Kuzatuvda xato")
            self._wake.wait(interval)
            self._wake.clear()

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run_forever, name="ijro-pipeline", daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
