"""Dastur sozlamalari (config.yaml)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    inbox_dir: Path
    work_dir: Path
    contacts_file: Path
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5vl:7b"
    ollama_timeout: int = 900
    num_ctx: int = 16384
    tesseract_cmd: str = "tesseract"
    ocr_languages: str = "uzb+uzb_cyrl+rus"
    max_pages: int = 4
    render_dpi: int = 200
    llm_image_max_side: int = 1600
    remote_url: str = ""
    remote_token: str = ""
    send_pdf: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = True

    @property
    def docs_dir(self) -> Path:
        return self.work_dir / "docs"

    @property
    def journal_file(self) -> Path:
        return self.work_dir / "jurnal.csv"

    def ensure_dirs(self) -> None:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)


def load_config(path: Path) -> Config:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    paths = data.get("paths", {})
    ollama = data.get("ollama", {})
    ocr = data.get("ocr", {})
    pages = data.get("pages", {})
    remote = data.get("remote", {})
    ui = data.get("ui", {})
    base = Path(path).resolve().parent

    def p(value: str, default: str) -> Path:
        result = Path(value or default)
        return result if result.is_absolute() else base / result

    defaults = Config(Path(), Path(), Path())
    return Config(
        inbox_dir=p(paths.get("inbox"), "Kiruvchi"),
        work_dir=p(paths.get("work"), ".ish"),
        contacts_file=p(paths.get("contacts"), "kontaktlar.xlsx"),
        ollama_url=str(ollama.get("url", defaults.ollama_url)).rstrip("/"),
        model=str(ollama.get("model", defaults.model)),
        ollama_timeout=int(ollama.get("timeout_sec", defaults.ollama_timeout)),
        num_ctx=int(ollama.get("num_ctx", defaults.num_ctx)),
        tesseract_cmd=str(ocr.get("tesseract_cmd", defaults.tesseract_cmd)),
        ocr_languages=str(ocr.get("languages", defaults.ocr_languages)),
        max_pages=int(pages.get("max_pages", defaults.max_pages)),
        render_dpi=int(pages.get("dpi", defaults.render_dpi)),
        llm_image_max_side=int(pages.get("llm_image_max_side", defaults.llm_image_max_side)),
        remote_url=str(remote.get("url") or "").strip(),
        remote_token=str(remote.get("token") or "").strip(),
        send_pdf=bool(remote.get("send_pdf", defaults.send_pdf)),
        host=str(ui.get("host", defaults.host)),
        port=int(ui.get("port", defaults.port)),
        open_browser=bool(ui.get("open_browser", defaults.open_browser)),
    )
