"""Tekshiruv oynasi: brauzerda, faqat shu kompyuterda (127.0.0.1)."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from .pipeline import journal
from .remote import Remote, RemoteError
from .storage import FIELD_NAMES, PROCESSING, QUEUED, READY, Store
from .validate import registration_payload, validate_for_registration

EDITABLE = ["reg_no", "reg_date", "out_no", "resolution", "due_date", "due_text", "summary", "emails"]

LABELS = {
    "reg_no": "Ro'yxatga olingan raqami",
    "reg_date": "Ro'yxatga olingan sana",
    "out_no": "Chiqish raqami",
    "resolution": "Rezolyutsiya (ijrochilar)",
    "due_date": "Ijro muddati (sana)",
    "due_text": "Ijro muddati (matn, sana bo'lmasa)",
    "summary": "Hujjatning qisqacha mazmuni",
    "emails": "Ijrochilar emaili (vergul bilan)",
    "unmatched": "Kontaktlarda topilmadi",
    "ai_note": "AI izohi",
}


def create_app(cfg, store: Store, pipeline, remote: Remote, system_status) -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    csrf_token = secrets.token_urlsafe(32)
    allowed_hosts = {f"127.0.0.1:{cfg.port}", f"localhost:{cfg.port}", "127.0.0.1", "localhost"}

    @app.before_request
    def guard():
        # Boshqa saytlar brauzer orqali bu oynaga buyruq yubora olmasin.
        if request.host not in allowed_hosts:
            abort(400)
        if request.method == "POST" and not secrets.compare_digest(request.form.get("_csrf", ""), csrf_token):
            abort(400)

    @app.context_processor
    def common():
        return {"csrf": csrf_token, "labels": LABELS}

    def load(doc_id: str):
        doc = store.get(doc_id)
        if not doc:
            abort(404)
        return doc

    def page_numbers(doc_id: str) -> list[int]:
        files = store.doc_dir(doc_id).glob("page-*.png")
        return sorted(int(p.stem.split("-")[1]) for p in files)

    def save_form(doc) -> None:
        for name in EDITABLE:
            if name in request.form:
                value = request.form[name].strip()
                if value != doc.fields.get(name, ""):
                    doc.checks[name] = "edited"  # xodim tuzatgan qiymat endi "tasdiqlanmagan" emas
                doc.fields[name] = value
        doc.rev += 1
        store.save(doc)

    def delete_source(doc) -> None:
        path = Path(doc.source_path)
        if path.is_file():
            os.remove(path)  # savatga emas — butunlay

    @app.get("/")
    def index():
        docs = store.list()
        busy = any(d.status in (QUEUED, PROCESSING) for d in docs)
        return render_template("index.html", docs=docs, busy=busy, status=system_status(), inbox=cfg.inbox_dir)

    @app.get("/doc/<doc_id>")
    def view(doc_id):
        doc = load(doc_id)
        return render_template("doc.html", doc=doc, pages=page_numbers(doc_id), errors=[],
                               editable=EDITABLE, model=cfg.model)

    @app.get("/doc/<doc_id>/page/<int:number>.png")
    def page(doc_id, number):
        load(doc_id)
        path = store.doc_dir(doc_id) / f"page-{number}.png"
        if not path.is_file():
            abort(404)
        return send_file(path, mimetype="image/png", max_age=0)

    @app.post("/doc/<doc_id>/save")
    def save(doc_id):
        doc = load(doc_id)
        save_form(doc)
        flash("Saqlandi")
        return redirect(url_for("view", doc_id=doc_id))

    @app.post("/doc/<doc_id>/register")
    def register(doc_id):
        """1-qadam: tekshiruv va tasdiqlash sahifasi. Hali hech narsa yuborilmaydi."""
        doc = load(doc_id)
        if doc.status in (QUEUED, PROCESSING):
            flash("Hujjat hali o'qilmoqda")
            return redirect(url_for("view", doc_id=doc_id))
        save_form(doc)
        errors, emails = validate_for_registration(doc.fields)
        if cfg.send_pdf and not doc.source_exists:
            errors.append("Asl fayl kiruvchi papkada topilmadi")
        if not remote.configured:
            errors.append("Google bilan aloqa sozlanmagan (config.yaml → remote)")
        if errors:
            return render_template("doc.html", doc=doc, pages=page_numbers(doc_id), errors=errors,
                                   editable=EDITABLE, model=cfg.model)
        return render_template("confirm.html", doc=doc, emails=emails,
                               payload=registration_payload(doc.fields, emails), send_pdf=cfg.send_pdf)

    @app.post("/doc/<doc_id>/confirm")
    def confirm(doc_id):
        """2-qadam: xodim tasdiqladi — yozuv Google'ga yuboriladi, keyin fayl o'chiriladi."""
        doc = load(doc_id)
        if request.form.get("rev") != str(doc.rev):
            flash("Hujjat o'zgargan — qaytadan tekshiring")
            return redirect(url_for("view", doc_id=doc_id))
        errors, emails = validate_for_registration(doc.fields)
        if errors:
            return render_template("doc.html", doc=doc, pages=page_numbers(doc_id), errors=errors,
                                   editable=EDITABLE, model=cfg.model)
        payload = registration_payload(doc.fields, emails)
        try:
            result = remote.register(payload, Path(doc.source_path) if cfg.send_pdf else None)
        except (RemoteError, OSError) as err:
            journal(cfg.journal_file, "Xato", payload["regNo"], str(err)[:200])
            return render_template("doc.html", doc=doc, pages=page_numbers(doc_id),
                                   errors=[f"Yuborilmadi: {err}"], editable=EDITABLE, model=cfg.model)
        note = ""
        try:
            delete_source(doc)
        except OSError as err:
            note = f" Faylni o'chirib bo'lmadi: {err}"
        if not store.delete(doc.id):
            note += f" Vaqtinchalik fayllar qoldi (dastur qayta ishga tushganda o'chiriladi): {store.doc_dir(doc.id)}"
        journal(cfg.journal_file, "Ro'yxatga olindi", payload["regNo"],
                f"{result.get('sheet')}, {result.get('row')}-qator" + note)
        flash(f"{payload['regNo']} ro'yxatga olindi: {result.get('sheet')}, {result.get('row')}-qator. "
              f"Xat yuborildi: {', '.join(emails)}.{note}")
        return redirect(url_for("index"))

    @app.post("/doc/<doc_id>/reject")
    def reject(doc_id):
        doc = load(doc_id)
        if doc.status == PROCESSING:
            flash("Hujjat hali o'qilmoqda")
            return redirect(url_for("view", doc_id=doc_id))
        try:
            delete_source(doc)
        except OSError as err:
            flash(f"Faylni o'chirib bo'lmadi: {err}")
            return redirect(url_for("view", doc_id=doc_id))
        if not store.delete(doc.id):
            flash(f"Vaqtinchalik fayllar qoldi (dastur qayta ishga tushganda o'chiriladi): {store.doc_dir(doc.id)}")
        journal(cfg.journal_file, "Rad etildi", doc.fields.get("reg_no", ""))
        flash("Hujjat rad etildi va o'chirildi")
        return redirect(url_for("index"))

    @app.post("/doc/<doc_id>/reread")
    def reread(doc_id):
        doc = load(doc_id)
        if not doc.source_exists:
            flash("Asl fayl topilmadi")
            return redirect(url_for("view", doc_id=doc_id))
        pipeline.request_reread(doc_id, request.form.get("model", "").strip() or None)
        flash("Qayta o'qish navbatga qo'yildi")
        return redirect(url_for("index"))

    app.jinja_env.filters["dmy"] = lambda iso: ".".join(reversed(str(iso).split("-")))
    app.jinja_env.globals.update(READY=READY, QUEUED=QUEUED, PROCESSING=PROCESSING, FIELD_NAMES=FIELD_NAMES)
    return app
