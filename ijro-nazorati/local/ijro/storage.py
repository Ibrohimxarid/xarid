"""Tekshiruvni kutayotgan hujjatlar: har biri uchun ish papkasida doc.json va sahifa rasmlari.

Ro'yxatga olingan yoki rad etilgan hujjatning papkasi butunlay o'chiriladi.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

FIELD_NAMES = [
    "reg_no", "reg_date", "out_no", "resolution", "due_date", "due_text",
    "summary", "emails", "unmatched", "ai_note",
]

QUEUED, PROCESSING, READY, ERROR = "queued", "processing", "ready", "error"


def empty_fields() -> dict:
    return {name: "" for name in FIELD_NAMES}


@dataclass
class Doc:
    id: str
    source_path: str
    file_name: str
    size: int
    status: str = QUEUED
    message: str = ""
    fields: dict = field(default_factory=empty_fields)
    checks: dict = field(default_factory=dict)
    pages: int = 0
    model: str = ""
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    rev: int = 0

    @property
    def source_exists(self) -> bool:
        return Path(self.source_path).is_file()


class Store:
    def __init__(self, docs_dir: Path):
        self.docs_dir = Path(docs_dir)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        # Oldin o'chirib bo'lmagan qoldiqlar (doc.json yo'q papkalar) tozalanadi.
        for leftover in self.docs_dir.iterdir():
            if leftover.is_dir() and not (leftover / "doc.json").exists():
                shutil.rmtree(leftover, ignore_errors=True)

    def doc_dir(self, doc_id: str) -> Path:
        return self.docs_dir / doc_id

    def create(self, source: Path) -> Doc:
        doc = Doc(id=uuid.uuid4().hex[:12], source_path=str(source), file_name=source.name,
                  size=source.stat().st_size)
        self.doc_dir(doc.id).mkdir(parents=True, exist_ok=True)
        self.save(doc)
        return doc

    def save(self, doc: Doc) -> None:
        with self._lock:
            path = self.doc_dir(doc.id) / "doc.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(asdict(doc), ensure_ascii=False, indent=1), encoding="utf-8")
            for attempt in range(10):
                try:
                    os.replace(tmp, path)
                    return
                except PermissionError:  # Windows: antivirus faylni bir lahza band qilishi mumkin
                    if attempt == 9:
                        raise
                    time.sleep(0.2)

    def get(self, doc_id: str) -> Doc | None:
        if not doc_id.isalnum():
            return None
        path = self.doc_dir(doc_id) / "doc.json"
        with self._lock:
            if not path.is_file():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
        fields = empty_fields()
        fields.update(data.pop("fields", {}))
        return Doc(fields=fields, **data)

    def list(self) -> list[Doc]:
        with self._lock:
            ids = [p.name for p in self.docs_dir.iterdir() if (p / "doc.json").is_file()]
        docs = [d for d in (self.get(i) for i in ids) if d]
        return sorted(docs, key=lambda d: d.created)

    def find_by_source(self, source: Path) -> Doc | None:
        source = str(source)
        return next((d for d in self.list() if d.source_path == source), None)

    def delete(self, doc_id: str) -> bool:
        """Hujjat papkasini o'chiradi. Windows'da fayl band bo'lsa, bir necha marta urinadi."""
        path = self.doc_dir(doc_id)
        for _ in range(10):
            with self._lock:
                shutil.rmtree(path, ignore_errors=True)
            if not path.exists():
                return True
            time.sleep(0.3)
        return False
