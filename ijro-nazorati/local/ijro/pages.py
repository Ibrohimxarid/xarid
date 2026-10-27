"""PDF/rasmni sahifa rasmlariga aylantirish (PyMuPDF)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}


@dataclass
class Page:
    number: int          # hujjatdagi sahifa raqami (1 dan)
    image: Path          # ko'rish va OCR uchun
    llm_image: Path      # model uchun kichraytirilgan
    text_layer: str      # PDF ichidagi matn (skanerda bo'sh)


def select_pages(total: int, max_pages: int) -> list[int]:
    """Uzun hujjatdan birinchi sahifalar va oxirgisi (rezolyutsiya varag'i ko'pincha boshida yoki oxirida)."""
    if total <= max_pages:
        return list(range(total))
    if max_pages <= 1:
        return [0]
    return list(range(max_pages - 1)) + [total - 1]


def render(source: Path, out_dir: Path, dpi: int, llm_max_side: int, max_pages: int) -> tuple[list[Page], int]:
    """Tanlangan sahifalarni PNG qilib saqlaydi. Natija: (sahifalar, hujjatdagi jami sahifalar)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(source) as doc:
        if doc.needs_pass:
            raise ValueError("PDF parol bilan himoyalangan")
        total = doc.page_count
        if total == 0:
            raise ValueError("Hujjatda sahifa yo'q")
        pages = []
        for index in select_pages(total, max_pages):
            page = doc[index]
            image = out_dir / f"page-{index + 1}.png"
            page.get_pixmap(dpi=dpi).save(image)
            zoom = min(dpi / 72, llm_max_side / max(page.rect.width, page.rect.height))
            llm_image = out_dir / f"llm-{index + 1}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(llm_image)
            pages.append(Page(index + 1, image, llm_image, page.get_text() or ""))
    return pages, total
