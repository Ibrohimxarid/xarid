"""Tesseract OCR (kompyuterda, internetsiz)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Windows'da qora konsol oynasi chiqmasin.
_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


WINDOWS_DEFAULT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class Ocr:
    def __init__(self, cmd: str, languages: str):
        if cmd == "tesseract" and not shutil.which(cmd) and WINDOWS_DEFAULT.is_file():
            cmd = str(WINDOWS_DEFAULT)
        self.cmd = cmd
        self.wanted = [lang for lang in languages.split("+") if lang]
        self.languages: list[str] = []
        self.problem = ""
        self._detect()

    def _run(self, args: list[str], timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run([self.cmd, *args], capture_output=True, timeout=timeout,
                              creationflags=_NO_WINDOW)

    def _detect(self) -> None:
        try:
            out = self._run(["--list-langs"], 30)
        except (OSError, subprocess.SubprocessError) as err:
            self.problem = f"Tesseract topilmadi ({self.cmd}): {err}"
            return
        installed = {line.strip() for line in out.stdout.decode("utf-8", "replace").splitlines()[1:]}
        self.languages = [lang for lang in self.wanted if lang in installed]
        missing = [lang for lang in self.wanted if lang not in installed]
        if not self.languages:
            self.problem = "Tesseract'da kerakli tillar yo'q: " + ", ".join(self.wanted)
        elif missing:
            self.problem = "Tesseract'da tillar yetishmaydi: " + ", ".join(missing)

    @property
    def available(self) -> bool:
        return bool(self.languages)

    def image_to_text(self, image: Path) -> str:
        if not self.available:
            return ""
        out = self._run([str(image), "stdout", "-l", "+".join(self.languages), "--psm", "3"], 300)
        if out.returncode != 0:
            raise RuntimeError("OCR xatosi: " + out.stderr.decode("utf-8", "replace")[:300])
        return out.stdout.decode("utf-8", "replace")
