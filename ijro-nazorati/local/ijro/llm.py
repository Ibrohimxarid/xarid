"""Kompyuterdagi model (Ollama) orqali hujjatdan maydonlarni ajratish."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

SYSTEM_PROMPT = """\
You extract registration data from ONE incoming official document received by JSC "O'zavtosanoat" (Uzbekistan).
You get the page images and OCR text of the same pages (OCR may contain errors). The document may be in Uzbek
(Latin or Cyrillic script) or Russian.

STRICT RULE: never guess or invent. Fill a field only with what is clearly visible in the document.
If a field is absent, unreadable, covered, or you are not sure about every character of a number or a date,
return null (an empty list for "ijrochilar") and say why in "izoh". An empty field is better than a wrong one:
an employee checks every document and fills empty fields by hand.

Fields:
- royxat_raqami: the INCOMING registration number from O'zavtosanoat's registration stamp (stamp or handwriting
  near words like "Kiruvchi", "Ro'yxatga olindi", "Кирувчи", "Вх. №"), for example "488-PA".
  It is NOT the sender's outgoing number.
- royxat_sanasi: the date from the same registration stamp, format YYYY-MM-DD.
- chiqish_raqami: the sender's OUTGOING number from the letterhead (next to the letter date, "№ ...", "...-son").
  Only the number, without the date.
- ijrochilar: the executors named in the resolution (rezolyutsiya): people and/or organizations the task is
  assigned to, one item each, spelled exactly as in the resolution (for example "U.Xoshimova", "TTPU").
  Do not include the person who signed the resolution. No resolution -> [].
- ijro_muddati_sana: the deadline, format YYYY-MM-DD. Prefer the deadline written in the resolution; otherwise an
  explicit deadline in the document text. If the year is missing, use the nearest such date that is not earlier than
  the registration date. If the deadline is not a specific date ("doimiy", "har oyda") or there is none -> null.
- ijro_muddati_matn: the deadline exactly as written ("12-oktabrga qadar", "12.10.2026"); null if there is none.
- qisqacha_mazmun: 1-2 sentences in Uzbek (Latin script), register style: what the document is and what is asked.
  Style example: "\"O'zbekiston Respublikasida robototexnika texnologiyalarini kompleks rivojlantirish
  chora-tadbirlari to'g'risida\"gi O'zR Prezidenti Farmoni loyihasi kelishish uchun yuborilgan."
  Only facts from the document, no conclusions of your own. Unreadable -> null.
- izoh: in Uzbek (Latin script), briefly: which fields could not be read and why, and any doubts
  (for example, the deadline in the resolution differs from the one in the text). null if there are none.
Answer with JSON only."""


def _nullable(kind: str) -> dict:
    return {"anyOf": [{"type": kind}, {"type": "null"}]}


SCHEMA = {
    "type": "object",
    "properties": {
        "royxat_raqami": _nullable("string"),
        "royxat_sanasi": _nullable("string"),
        "chiqish_raqami": _nullable("string"),
        "ijrochilar": {"type": "array", "items": {"type": "string"}},
        "ijro_muddati_sana": _nullable("string"),
        "ijro_muddati_matn": _nullable("string"),
        "qisqacha_mazmun": _nullable("string"),
        "izoh": _nullable("string"),
    },
    "required": ["royxat_raqami", "royxat_sanasi", "chiqish_raqami", "ijrochilar",
                 "ijro_muddati_sana", "ijro_muddati_matn", "qisqacha_mazmun", "izoh"],
    "additionalProperties": False,
}

MAX_OCR_CHARS = 12000


class LlmError(RuntimeError):
    pass


class Ollama:
    def __init__(self, url: str, model: str, timeout: int, num_ctx: int):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.num_ctx = num_ctx

    def status(self) -> tuple[bool, str]:
        try:
            resp = requests.get(self.url + "/api/tags", timeout=5)
            resp.raise_for_status()
        except requests.RequestException:
            return False, f"Ollama ishlamayapti ({self.url}). Ollama dasturini ishga tushiring."
        names = {m.get("name", "") for m in resp.json().get("models", [])}
        wanted = self.model if ":" in self.model else self.model + ":latest"
        if wanted not in names and self.model not in names:
            return False, f"Model yuklanmagan: buyruq satrida «ollama pull {self.model}» ni bajaring."
        return True, f"Model: {self.model}"

    def extract(self, images: list[Path], ocr_text: str, model: str | None = None) -> dict:
        payload = {
            "model": model or self.model,
            "stream": False,
            "format": SCHEMA,
            "keep_alive": "10m",
            "options": {"temperature": 0, "num_ctx": self.num_ctx},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "OCR text of the pages (may contain errors):\n" + ocr_text[:MAX_OCR_CHARS],
                    "images": [base64.b64encode(p.read_bytes()).decode("ascii") for p in images],
                },
            ],
        }
        try:
            resp = requests.post(self.url + "/api/chat", json=payload, timeout=self.timeout)
        except requests.ConnectionError as err:
            raise LlmError(f"Ollama ishlamayapti ({self.url})") from err
        except requests.Timeout as err:
            raise LlmError(f"Model {self.timeout} soniyada javob bermadi") from err
        if resp.status_code == 404:
            raise LlmError(f"Model topilmadi: «ollama pull {payload['model']}» ni bajaring")
        if resp.status_code != 200:
            raise LlmError(f"Ollama xatosi {resp.status_code}: {resp.text[:300]}")
        content = resp.json().get("message", {}).get("content", "")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as err:
            raise LlmError("Model JSON qaytarmadi") from err
        if not isinstance(data, dict):
            raise LlmError("Model javobi noto'g'ri formatda")
        return data
