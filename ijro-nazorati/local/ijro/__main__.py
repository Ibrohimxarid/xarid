"""Ishga tushirish: python -m ijro  yoki  IjroNazorati.exe"""
from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from .config import load_config
from .contacts import ContactBook
from .defaults import DEFAULT_CONFIG
from .extract import Extractor
from .llm import Ollama
from .ocr import Ocr
from .pipeline import Pipeline
from .remote import Remote
from .storage import Store


def app_dir() -> Path:
    """exe yonidagi papka (yoki python bilan ishga tushirilganda joriy papka)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def port_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="IjroNazorati", description="Kiruvchi hujjatlarni tekshirish")
    parser.add_argument("--config", help="config.yaml yo'li (standart: dastur yonida)")
    parser.add_argument("--check", action="store_true", help="tizimni tekshirib, chiqish")
    parser.add_argument("--benchmark", metavar="PAPKA", help="modellarni namunaviy hujjatlarda solishtirish")
    parser.add_argument("--models", help="--benchmark uchun modellar, vergul bilan (standart: config'dagi)")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")  # Windows konsolida o'zbek/rus harflari xato bermasin

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(args.config) if args.config else app_dir() / "config.yaml"
    if not config_path.exists():
        config_path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        print(f"Sozlamalar fayli yaratildi: {config_path}")
    cfg = load_config(config_path)
    cfg.ensure_dirs()

    store = Store(cfg.docs_dir)
    ocr = Ocr(cfg.tesseract_cmd, cfg.ocr_languages)
    llm = Ollama(cfg.ollama_url, cfg.model, cfg.ollama_timeout, cfg.num_ctx)
    contacts = ContactBook(cfg.contacts_file)
    remote = Remote(cfg.remote_url, cfg.remote_token)
    pipeline = Pipeline(cfg, store, Extractor(cfg, ocr, llm, contacts))

    cache: dict = {"at": 0.0, "value": []}

    def system_status() -> list[tuple[bool, str]]:
        # Faqat shu kompyuterdagi tekshiruvlar: Google'ga hech qanday so'rov yuborilmaydi.
        if time.time() - cache["at"] > 20:
            cache["value"] = [
                llm.status(),
                (ocr.available and not ocr.problem,
                 ocr.problem or "OCR: " + "+".join(ocr.languages)),
                (remote.configured, "Google: sozlangan" if remote.configured
                 else "Google sozlanmagan (config.yaml → remote)"),
                (bool(contacts.contacts()), f"Kontaktlar: {len(contacts.contacts())}" if contacts.contacts()
                 else f"Kontaktlar fayli bo'sh: {cfg.contacts_file}"),
            ]
            cache["at"] = time.time()
        return cache["value"]

    url = f"http://{cfg.host}:{cfg.port}/"
    if args.check:
        for ok, text in system_status():
            print(("[OK]  " if ok else "[!!]  ") + text)
        print(f"Kiruvchi papka: {cfg.inbox_dir}")
        return 0

    if args.benchmark:
        from .benchmark import run as run_benchmark

        models = [m.strip() for m in (args.models or cfg.model).split(",") if m.strip()]
        print(run_benchmark(pipeline.extractor, Path(args.benchmark), models))
        return 0

    if port_busy(cfg.host, cfg.port):
        print("Dastur allaqachon ishlayapti — oyna brauzerda ochiladi.")
        webbrowser.open(url)
        return 0

    from waitress import serve

    from .web import create_app

    app = create_app(cfg, store, pipeline, remote, system_status)
    pipeline.start()
    print("=" * 60)
    print("  Ijro nazorati ishlayapti. Bu oynani yopmang.")
    print(f"  Tekshiruv oynasi: {url}")
    print(f"  Kiruvchi papka:   {cfg.inbox_dir}")
    print("=" * 60)
    for ok, text in system_status():
        print(("  [OK]  " if ok else "  [!!]  ") + text)
    if cfg.open_browser:
        threading.Timer(1.5, webbrowser.open, [url]).start()
    serve(app, host=cfg.host, port=cfg.port, threads=4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
