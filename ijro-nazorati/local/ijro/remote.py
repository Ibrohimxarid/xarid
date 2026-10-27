"""Google qismi (Apps Script veb-ilovasi) bilan aloqa. Faqat xodim tasdiqlagandan keyin chaqiriladi."""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

import requests

MAX_FILE_BYTES = 20 * 1024 * 1024


class RemoteError(RuntimeError):
    pass


class Remote:
    def __init__(self, url: str, token: str, timeout: int = 120):
        self.url = url
        self.token = token
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)

    def _post(self, body: dict) -> dict:
        if not self.configured:
            raise RemoteError("config.yaml da remote.url va remote.token ko'rsatilmagan")
        try:
            # Apps Script javobni 302 orqali beradi; requests uni GET bilan kuzatib boradi.
            resp = requests.post(self.url, json={"token": self.token, **body}, timeout=self.timeout)
        except requests.RequestException as err:
            raise RemoteError(f"Google bilan aloqa yo'q (internetni tekshiring): {err}") from err
        try:
            data = resp.json()
        except ValueError as err:
            raise RemoteError(f"Veb-ilova javobi noto'g'ri (HTTP {resp.status_code}). "
                              "URL va «Who has access: Anyone» sozlamasini tekshiring.") from err
        if not isinstance(data, dict):
            raise RemoteError("Veb-ilova javobi noto'g'ri")
        return data

    def ping(self) -> tuple[bool, str]:
        try:
            data = self._post({"action": "ping"})
        except RemoteError as err:
            return False, str(err)
        return bool(data.get("ok")), data.get("registryUrl") or data.get("error", "")

    def register(self, doc: dict, file: Path | None) -> dict:
        body = {"action": "register", "doc": doc, "file": None}
        if file is not None:
            data = file.read_bytes()
            if len(data) > MAX_FILE_BYTES:
                raise RemoteError("Fayl 20 MB dan katta — config.yaml da send_pdf: false qiling yoki faylni kichraytiring")
            body["file"] = {
                "name": file.name,
                "mimeType": mimetypes.guess_type(file.name)[0] or "application/octet-stream",
                "base64": base64.b64encode(data).decode("ascii"),
            }
        result = self._post(body)
        if not result.get("ok"):
            raise RemoteError(result.get("error") or "Noma'lum xato")
        return result
