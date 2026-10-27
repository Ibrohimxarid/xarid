"""To'liq oqim: papkadagi PDF → model (soxta Ollama) → tekshiruv oynasi → tasdiqlash → Google (soxta veb-ilova)."""
import base64
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import openpyxl
import pymupdf
import pytest

from ijro.config import Config
from ijro.contacts import ContactBook
from ijro.extract import Extractor
from ijro.llm import SCHEMA, Ollama
from ijro.ocr import Ocr
from ijro.pipeline import Pipeline
from ijro.remote import Remote
from ijro.storage import ERROR, READY, Store
from ijro.web import create_app

DOC_TEXT = [
    "O'ZAVTOSANOAT AJ   Kiruvchi No 488-PA   01.10.2026",
    "Toshkent turin politexnika universiteti",
    "2026-yil 30-sentabr  No 26-2850",
    "O'zbekiston Respublikasida robototexnika texnologiyalarini kompleks rivojlantirish",
    "chora-tadbirlari to'g'risida Farmon loyihasi kelishish uchun yuboriladi.",
    "Loyiha bo'yicha taklif va mulohazalaringizni belgilangan muddatda taqdim etishingizni so'raymiz.",
    "Rezolyutsiya: U.Xoshimova, TTPU, Karimov - 12-oktabrgacha ko'rib chiqilsin.",
]

MODEL_REPLY = {
    "royxat_raqami": "488-PA",
    "royxat_sanasi": "2026-10-01",
    "chiqish_raqami": "26-2851",            # matnda yo'q — "tasdiqlanmagan" bo'lishi kerak
    "ijrochilar": ["U.Xoshimova", "TTPU", "Karimov"],
    "ijro_muddati_sana": "2026-10-12",
    "ijro_muddati_matn": "12-oktabrgacha",
    "qisqacha_mazmun": "Farmon loyihasi kelishish uchun yuborilgan.",
    "izoh": None,
}


class FakeServer:
    """Soxta Ollama va Apps Script (javob 302 orqali, haqiqiysiga o'xshab)."""

    def __init__(self):
        self.chat_requests = []
        self.remote_requests = []
        self.model_reply = dict(MODEL_REPLY)
        self.chat_status = 200
        self.remote_reply = {"ok": True, "sheet": "Oktabr 2026", "row": 5}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _json(self, code, data):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/api/tags":
                    return self._json(200, {"models": [{"name": "qwen2.5vl:7b"}]})
                if self.path.startswith("/echo"):
                    return self._json(200, outer.remote_reply)
                self._json(404, {})

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/chat":
                    outer.chat_requests.append(data)
                    if outer.chat_status != 200:
                        return self._json(outer.chat_status, {"error": "boom"})
                    return self._json(200, {"message": {"role": "assistant",
                                                        "content": json.dumps(outer.model_reply)}})
                if self.path == "/exec":
                    outer.remote_requests.append(data)
                    self.send_response(302)
                    self.send_header("Location", "/echo?user_content_key=x")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._json(404, {})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def make_pdf(path: Path, lines=DOC_TEXT) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((50, 60 + 18 * i), line, fontsize=10)
    doc.save(path)


@pytest.fixture
def env(tmp_path):
    server = FakeServer()
    cfg = Config(inbox_dir=tmp_path / "Kiruvchi", work_dir=tmp_path / ".ish",
                 contacts_file=tmp_path / "kontaktlar.xlsx", ollama_url=server.url,
                 tesseract_cmd=str(tmp_path / "no-tesseract"),
                 remote_url=server.url + "/exec", remote_token="secret", open_browser=False)
    cfg.ensure_dirs()
    contacts = ContactBook(cfg.contacts_file)
    wb = openpyxl.load_workbook(cfg.contacts_file)
    wb.active.append(["U.Xoshimova", "u.xoshimova@corp.uz", "", ""])
    wb.active.append(["TTPU", "info@ttpu.uz", "", ""])
    wb.save(cfg.contacts_file)

    store = Store(cfg.docs_dir)
    ocr = Ocr(cfg.tesseract_cmd, cfg.ocr_languages)
    llm = Ollama(cfg.ollama_url, cfg.model, 30, cfg.num_ctx)
    pipeline = Pipeline(cfg, store, Extractor(cfg, ocr, llm, contacts))
    remote = Remote(cfg.remote_url, cfg.remote_token, timeout=10)
    app = create_app(cfg, store, pipeline, remote, lambda: [(True, "test")])
    client = app.test_client()
    client.environ_base["HTTP_HOST"] = f"127.0.0.1:{cfg.port}"
    yield {"cfg": cfg, "server": server, "store": store, "pipeline": pipeline, "client": client,
           "app": app}
    server.close()


def csrf_of(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)


def ingest(env, name="hujjat.pdf", lines=DOC_TEXT):
    path = env["cfg"].inbox_dir / name
    make_pdf(path, lines)
    p = env["pipeline"]
    assert p.scan_inbox(now=1000.0) == []           # birinchi ko'rish — nusxalash tugaganini kutadi
    docs = p.scan_inbox(now=1010.0)
    assert len(docs) == 1
    return p.process(docs[0]), path


def test_full_flow_nothing_leaves_before_confirmation(env):
    doc, source = ingest(env)
    server, client, store = env["server"], env["client"], env["store"]
    assert doc.status == READY

    # Model so'rovi: sxema, temperature 0, sahifa rasmi va PDF matni.
    req = server.chat_requests[0]
    assert req["format"] == SCHEMA
    assert req["options"]["temperature"] == 0
    assert len(req["messages"][1]["images"]) == 1
    assert "Kiruvchi No 488-PA" in req["messages"][1]["content"]

    # Matn bilan solishtirish: model "o'ylab topgan" chiqish raqami ajratib ko'rsatiladi.
    assert doc.checks["reg_no"] == "ok"
    assert doc.checks["reg_date"] == "ok"
    assert doc.checks["due_date"] == "ok"
    assert doc.checks["out_no"] == "unconfirmed"
    assert doc.fields["resolution"] == "U.Xoshimova,\nTTPU,\nKarimov"
    assert doc.fields["emails"] == "u.xoshimova@corp.uz, info@ttpu.uz"
    assert doc.fields["unmatched"] == "Karimov"

    html = client.get(f"/doc/{doc.id}").get_data(as_text=True)
    assert re.search(r'name="out_no" value="26-2851" class="unconfirmed"', html)
    with client.get(f"/doc/{doc.id}/page/1.png") as image:   # fayl yopilsin (Windows)
        assert image.status_code == 200

    token = csrf_of(client, f"/doc/{doc.id}")
    form = {"_csrf": token, **{k: doc.fields[k] for k in
            ("reg_no", "reg_date", "out_no", "resolution", "due_date", "due_text", "summary", "emails")}}
    form["out_no"] = "26-2850"   # xodim tuzatdi
    page = client.post(f"/doc/{doc.id}/register", data=form)
    assert page.status_code == 200
    confirm_html = page.get_data(as_text=True)
    assert "u.xoshimova@corp.uz, info@ttpu.uz" in confirm_html
    assert server.remote_requests == []                  # tasdiqlashgacha hech narsa yuborilmagan
    assert source.exists()

    rev = re.search(r'name="rev" value="(\d+)"', confirm_html).group(1)
    resp = client.post(f"/doc/{doc.id}/confirm", data={"_csrf": token, "rev": rev})
    assert resp.status_code == 302

    sent = server.remote_requests[0]
    assert sent["token"] == "secret" and sent["action"] == "register"
    assert sent["doc"] == {
        "regNo": "488-PA", "regDate": "2026-10-01", "outNo": "26-2850",
        "resolution": "U.Xoshimova,\nTTPU,\nKarimov", "dueDate": "2026-10-12",
        "dueText": "12-oktabrga qadar", "summary": "Farmon loyihasi kelishish uchun yuborilgan.",
        "emails": ["u.xoshimova@corp.uz", "info@ttpu.uz"]}
    assert base64.b64decode(sent["file"]["base64"])[:5] == b"%PDF-"
    assert sent["file"]["mimeType"] == "application/pdf"

    # Kompyuterda hech narsa qolmadi; jurnalda mazmun yo'q.
    assert not source.exists()
    assert store.list() == []
    assert not store.doc_dir(doc.id).exists()
    log = env["cfg"].journal_file.read_text(encoding="utf-8-sig")
    assert "488-PA" in log and "Farmon" not in log
    assert "488-PA ro&#39;yxatga olindi" in client.get("/").get_data(as_text=True)


def test_edited_value_is_no_longer_marked_unconfirmed(env):
    doc, _ = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    client.post(f"/doc/{doc.id}/save", data={"_csrf": token, "out_no": "26-2850"})
    html = client.get(f"/doc/{doc.id}").get_data(as_text=True)
    assert re.search(r'name="out_no" value="26-2850" class=""', html)
    assert env["store"].get(doc.id).checks["out_no"] == "edited"


def test_send_pdf_false_keeps_document_off_google(env):
    env["cfg"].send_pdf = False
    doc, _ = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    form = {"_csrf": token, **doc.fields}
    page = client.post(f"/doc/{doc.id}/register", data=form).get_data(as_text=True)
    rev = re.search(r'name="rev" value="(\d+)"', page).group(1)
    client.post(f"/doc/{doc.id}/confirm", data={"_csrf": token, "rev": rev})
    assert env["server"].remote_requests[0]["file"] is None


def test_validation_errors_block_registration(env):
    doc, source = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    form = {"_csrf": token, **doc.fields, "reg_no": "", "emails": "noto'g'ri"}
    html = client.post(f"/doc/{doc.id}/register", data=form).get_data(as_text=True)
    assert "Ro&#39;yxat raqami bo&#39;sh" in html
    assert "Noto&#39;g&#39;ri email" in html
    assert env["server"].remote_requests == []
    assert source.exists()


def test_google_error_keeps_file_and_record(env):
    doc, source = ingest(env)
    env["server"].remote_reply = {"ok": False, "error": "Bu ro'yxat raqami reyestrda allaqachon bor: 488-PA"}
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    page = client.post(f"/doc/{doc.id}/register", data={"_csrf": token, **doc.fields}).get_data(as_text=True)
    rev = re.search(r'name="rev" value="(\d+)"', page).group(1)
    html = client.post(f"/doc/{doc.id}/confirm", data={"_csrf": token, "rev": rev}).get_data(as_text=True)
    assert "allaqachon bor" in html
    assert source.exists()
    assert env["store"].get(doc.id) is not None


def test_stale_confirmation_is_refused(env):
    doc, source = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    client.post(f"/doc/{doc.id}/register", data={"_csrf": token, **doc.fields})
    client.post(f"/doc/{doc.id}/save", data={"_csrf": token, "summary": "boshqa matn"})
    resp = client.post(f"/doc/{doc.id}/confirm", data={"_csrf": token, "rev": "1"})
    assert resp.status_code == 302
    assert env["server"].remote_requests == []


def test_reject_deletes_everything(env):
    doc, source = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    assert client.post(f"/doc/{doc.id}/reject", data={"_csrf": token}).status_code == 302
    assert not source.exists()
    assert env["store"].list() == []
    assert env["server"].remote_requests == []


def test_model_failure_leaves_fields_empty_for_manual_entry(env):
    env["server"].chat_status = 500
    doc, _ = ingest(env)
    assert doc.status == ERROR
    assert "qo'lda" in doc.message
    assert all(v == "" for v in doc.fields.values())
    # Qo'lda to'ldirib ro'yxatga olish mumkin.
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    form = {"_csrf": token, "reg_no": "1-PA", "reg_date": "2026-10-01", "resolution": "TTPU",
            "summary": "Xat", "emails": "info@ttpu.uz", "out_no": "", "due_date": "", "due_text": ""}
    page = client.post(f"/doc/{doc.id}/register", data=form)
    assert "Tasdiqlash va yuborish" in page.get_data(as_text=True)


def test_reread_uses_requested_model(env):
    doc, _ = ingest(env)
    client = env["client"]
    token = csrf_of(client, f"/doc/{doc.id}")
    client.post(f"/doc/{doc.id}/reread", data={"_csrf": token, "model": "gemma3:4b"})
    queued = env["pipeline"].next_queued()
    assert queued.id == doc.id
    env["pipeline"].process(queued)
    assert env["server"].chat_requests[-1]["model"] == "gemma3:4b"


def test_csrf_and_host_checks(env):
    doc, _ = ingest(env)
    client = env["client"]
    assert client.post(f"/doc/{doc.id}/reject", data={}).status_code == 400
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert env["store"].get(doc.id) is not None


def test_unsupported_file_and_growing_file(env):
    cfg, p = env["cfg"], env["pipeline"]
    (cfg.inbox_dir / "xat.docx").write_bytes(b"PK")
    (cfg.inbox_dir / "~$xat.docx").write_bytes(b"lock")
    growing = cfg.inbox_dir / "katta.pdf"
    growing.write_bytes(b"%PDF-1")
    p.scan_inbox(now=1000.0)
    growing.write_bytes(b"%PDF-1.4 more")
    docs = p.scan_inbox(now=1010.0)
    assert [d.file_name for d in docs] == ["xat.docx"]
    assert docs[0].status == ERROR


def test_invented_dates_are_dropped(env):
    env["server"].model_reply = {**MODEL_REPLY, "royxat_sanasi": "2026-02-30", "ijro_muddati_sana": "12 oktabr"}
    doc, _ = ingest(env)
    assert doc.fields["reg_date"] == "" and doc.fields["due_date"] == ""
    assert doc.checks["reg_date"] == "empty"
    assert "noto'g'ri formatda" in doc.fields["ai_note"]
