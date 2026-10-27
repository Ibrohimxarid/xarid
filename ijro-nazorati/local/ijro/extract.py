"""Bitta hujjatni o'qish: sahifalar → OCR → model → matn bilan solishtirish → kontaktlar."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import evidence
from .contacts import ContactBook
from .llm import Ollama
from .ocr import Ocr
from .pages import render
from .validate import normalize_model_output

# PDF ichidagi matn shuncha belgidan ko'p bo'lsa, OCR shart emas.
TEXT_LAYER_MIN_CHARS = 200


@dataclass
class Extraction:
    fields: dict
    checks: dict
    pages: int
    total_pages: int


class Extractor:
    def __init__(self, cfg, ocr: Ocr, llm: Ollama, contacts: ContactBook):
        self.cfg = cfg
        self.ocr = ocr
        self.llm = llm
        self.contacts = contacts

    def run(self, source: Path, out_dir: Path, model: str | None = None) -> Extraction:
        pages, total = render(source, out_dir, self.cfg.render_dpi, self.cfg.llm_image_max_side, self.cfg.max_pages)
        notes = []
        texts = []
        for page in pages:
            text = page.text_layer
            if len(text.strip()) < TEXT_LAYER_MIN_CHARS and self.ocr.available:
                text = self.ocr.image_to_text(page.image)
            texts.append(f"--- {page.number}-sahifa ---\n{text.strip()}")
        page_text = "\n\n".join(texts)
        if not self.ocr.available:
            notes.append("OCR ishlamayapti — raqam va sanalar matn bilan tekshirilmadi.")
        if total > len(pages):
            notes.append(f"Hujjatda {total} sahifa, o'qilgani: " + ", ".join(str(p.number) for p in pages) + ".")

        raw = self.llm.extract([p.llm_image for p in pages], page_text, model)
        fields, executors, model_notes = normalize_model_output(raw)
        emails, unmatched = self.contacts.match(executors)
        fields["emails"] = ", ".join(emails)
        fields["unmatched"] = "\n".join(unmatched)
        fields["ai_note"] = " ".join(model_notes + notes)
        # OCR ham, PDF matni ham bo'lmasa, raqamlar "tasdiqlanmagan" bo'lib qoladi.
        checks = evidence.check_fields(fields, page_text)
        return Extraction(fields, checks, len(pages), total)
