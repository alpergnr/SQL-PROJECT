#!/usr/bin/env python3
"""Njoy Emlak — Flask Web Application.

Reuses the NjoyRepository from app.py to serve a rich single-page
web interface for the real estate database.
"""
from __future__ import annotations

import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import NjoyRepository, AppError, DEFAULT_DB_PATH, MAX_LIMIT

app = Flask(__name__)
app.secret_key = "njoy-emlak-demo-admin-secret"

repo = NjoyRepository(DEFAULT_DB_PATH)

ADMIN_EMAIL = "admin@njoyemlak.com"
ADMIN_PASSWORD = "admin123"


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _int_param(name: str, default: int) -> int:
    try:
        return min(int(request.args.get(name, default)), MAX_LIMIT)
    except (ValueError, TypeError):
        return default


def _listing_to_dict(listing) -> dict:
    return {
        "ilan_id": listing.ilan_id,
        "baslik": listing.baslik,
        "fiyat": listing.fiyat,
        "ilce": listing.ilce,
        "mahalle": listing.mahalle,
        "emlak_tipi": listing.emlak_tipi,
        "brut_m2": listing.brut_m2,
        "net_m2": listing.net_m2,
        "oda_sayisi": listing.oda_sayisi,
        "danisman": listing.danisman,
    }


def _admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin_email") != ADMIN_EMAIL:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin girişi gerekli"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def _customer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Kullanıcı girişi gerekli"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def _current_admin() -> str:
    return session.get("admin_email", ADMIN_EMAIL)


def _current_user_id() -> int:
    user_id = session.get("user_id")
    if user_id is None:
        raise AppError("Kullanıcı girişi gerekli")
    return int(user_id)


# ─── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_email"] = email
            return redirect(url_for("admin_panel"))
        user = repo.get_customer_by_email(email)
        if user and check_password_hash(user["SifreHash"], password):
            session.clear()
            session["user_id"] = user["KullaniciID"]
            return redirect(url_for("account_panel"))
        error = "E-posta veya şifre hatalı."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        name = request.form.get("name") or ""
        email = request.form.get("email") or ""
        password = request.form.get("password") or ""
        if len(password) < 4:
            error = "Şifre en az 4 karakter olmalıdır."
        else:
            try:
                user = repo.create_customer(
                    ad_soyad=name,
                    email=email,
                    password_hash=generate_password_hash(password),
                )
                session.clear()
                session["user_id"] = user["KullaniciID"]
                return redirect(url_for("account_panel"))
            except AppError as exc:
                error = str(exc)
    return render_template("register.html", error=error)


@app.route("/admin/login")
def admin_login_redirect():
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@_admin_required
def admin_panel():
    return render_template("admin.html", admin_email=_current_admin())


@app.route("/account")
@_customer_required
def account_panel():
    user = repo.get_customer(_current_user_id())
    return render_template("account.html", user=user)


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/listings")
def api_listings():
    limit = _int_param("limit", 20)
    sort_by = request.args.get("sort_by", "fiyat_desc")
    try:
        items = repo.list_listings(limit=limit, sort_by=sort_by)
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify([_listing_to_dict(i) for i in items])


@app.route("/api/search")
def api_search():
    limit = _int_param("limit", 20)
    max_price = request.args.get("max_price", type=float)
    districts = request.args.getlist("district") or None
    feature = request.args.get("feature") or None
    try:
        items = repo.search(
            max_price=max_price,
            districts=districts,
            feature=feature,
            limit=limit,
        )
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify([_listing_to_dict(i) for i in items])


@app.route("/api/stats")
def api_stats():
    stats = repo.agent_portfolios()
    return jsonify([
        {
            "ad_soyad": s.ad_soyad,
            "toplam_ilan": s.toplam_ilan,
            "toplam_portfoy": s.toplam_portfoy or 0,
        }
        for s in stats
    ])


@app.route("/listing/<int:ilan_id>")
def listing_detail(ilan_id: int):
    return render_template("detail.html", ilan_id=ilan_id)


@app.route("/api/listing/<int:ilan_id>")
def api_listing_detail(ilan_id: int):
    conn = repo._connect()
    try:
        row = conn.execute("""
            SELECT E.IlanID, E.Baslik, E.Fiyat, E.İl, E.İlce, E.Mahalle,
                   E.EmlakTipi, E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            WHERE E.IlanID = ?
        """, (ilan_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "İlan bulunamadı"}), 404
    return jsonify({
        "ilan_id": row["IlanID"],
        "baslik": row["Baslik"],
        "fiyat": row["Fiyat"],
        "il": row["İl"],
        "ilce": row["İlce"],
        "mahalle": row["Mahalle"],
        "emlak_tipi": row["EmlakTipi"],
        "brut_m2": row["BrutM2"],
        "net_m2": row["NetM2"],
        "oda_sayisi": row["OdaSayisi"],
        "danisman": row["Danisman"],
    })


@app.route("/api/listing/<int:ilan_id>/features")
def api_listing_features(ilan_id: int):
    features = repo.listing_features(ilan_id)
    return jsonify(features)


@app.route("/api/benchmark")
def api_benchmark():
    metrics = repo.benchmark()
    return jsonify(metrics)


@app.route("/api/analytics")
def api_analytics():
    limit = _int_param("limit", 10)
    return jsonify(repo.advanced_analytics(limit=limit))


@app.route("/api/explain")
def api_explain():
    limit = _int_param("limit", 20)
    max_price = request.args.get("max_price", default=50000, type=float)
    district = request.args.get("district", default="Beyoğlu")
    return jsonify(
        repo.explain_search_plan(
            max_price=max_price,
            district=district,
            limit=limit,
        )
    )


@app.route("/api/price-history")
def api_price_history():
    limit = _int_param("limit", 20)
    return jsonify(repo.price_history(limit=limit))


@app.route("/api/listing-history")
def api_listing_history():
    limit = _int_param("limit", 20)
    return jsonify(repo.listing_history(limit=limit))


@app.route("/api/account/bootstrap")
@_customer_required
def api_account_bootstrap():
    return jsonify(repo.customer_dashboard(_current_user_id()))


@app.route("/api/account/save-listing", methods=["POST"])
@_customer_required
def api_account_save_listing():
    payload = request.get_json(silent=True) or {}
    try:
        ilan_id = int(payload.get("ilan_id"))
        result = repo.save_listing(_current_user_id(), ilan_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Geçersiz ilan ID"}), 400
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/account/save-listing/<int:ilan_id>", methods=["DELETE"])
@_customer_required
def api_account_unsave_listing(ilan_id: int):
    repo.unsave_listing(_current_user_id(), ilan_id)
    return jsonify({"ok": True})


@app.route("/api/account/questions", methods=["POST"])
@_customer_required
def api_account_question():
    payload = request.get_json(silent=True) or {}
    ilan_raw = payload.get("ilan_id")
    try:
        ilan_id = int(ilan_raw) if ilan_raw not in (None, "") else None
        result = repo.ask_question(
            user_id=_current_user_id(),
            ilan_id=ilan_id,
            question=payload.get("question") or "",
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Geçersiz ilan ID"}), 400
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


@app.route("/api/account/notifications/read", methods=["POST"])
@_customer_required
def api_account_notifications_read():
    repo.mark_notifications_read(_current_user_id())
    return jsonify({"ok": True})


@app.route("/api/update-price", methods=["POST"])
def api_update_price():
    payload = request.get_json(silent=True) or {}
    try:
        ilan_id = int(payload.get("ilan_id"))
        new_price = float(payload.get("new_price"))
        note = payload.get("note")
        result = repo.update_listing_price(ilan_id=ilan_id, new_price=new_price, note=note)
    except (TypeError, ValueError):
        return jsonify({"error": "Geçersiz ilan ID veya fiyat"}), 400
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/admin/bootstrap")
@_admin_required
def api_admin_bootstrap():
    return jsonify({
        "admin": _current_admin(),
        "agents": repo.agents(),
        "features": repo.feature_catalog(),
        "listings": repo.admin_listings(limit=200),
        "history": repo.listing_history(limit=50),
        "questions": repo.admin_questions(),
    })


@app.route("/api/admin/listings", methods=["POST"])
@_admin_required
def api_admin_create_listing():
    payload = request.get_json(silent=True) or {}
    try:
        result = repo.create_listing(payload, user=_current_admin())
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result), 201


@app.route("/api/admin/listings/<int:ilan_id>", methods=["PUT"])
@_admin_required
def api_admin_update_listing(ilan_id: int):
    payload = request.get_json(silent=True) or {}
    note = payload.pop("note", None)
    try:
        result = repo.update_listing(
            ilan_id=ilan_id,
            payload=payload,
            user=_current_admin(),
            note=note,
        )
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/admin/listings/<int:ilan_id>/price", methods=["POST"])
@_admin_required
def api_admin_update_price(ilan_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        new_price = float(payload.get("new_price"))
        result = repo.update_listing_price(
            ilan_id=ilan_id,
            new_price=new_price,
            note=payload.get("note") or "Admin panelinden fiyat güncellendi.",
            user=_current_admin(),
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Geçersiz fiyat"}), 400
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/admin/questions/<int:question_id>/answer", methods=["POST"])
@_admin_required
def api_admin_answer_question(question_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        result = repo.answer_question(
            question_id=question_id,
            answer=payload.get("answer") or "",
            admin_user=_current_admin(),
        )
    except AppError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@app.route("/api/meta")
def api_meta():
    """Return available filter options for the UI."""
    conn = repo._connect()
    try:
        districts = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT İlce FROM Emlaklar ORDER BY İlce"
            ).fetchall()
        ]
        features = [
            row[0] for row in conn.execute(
                "SELECT OzellikAdi FROM Ozellikler ORDER BY OzellikAdi"
            ).fetchall()
        ]
        emlak_tipleri = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT EmlakTipi FROM Emlaklar ORDER BY EmlakTipi"
            ).fetchall()
        ]
    finally:
        conn.close()
    return jsonify({
        "districts": districts,
        "features": features,
        "emlak_tipleri": emlak_tipleri,
        "sort_options": [
            {"value": "fiyat_desc", "label": "Fiyat (Yüksek → Düşük)"},
            {"value": "fiyat_asc", "label": "Fiyat (Düşük → Yüksek)"},
            {"value": "m2_desc", "label": "m² (Büyük → Küçük)"},
            {"value": "ilanid_asc", "label": "İlan No (Eski → Yeni)"},
        ],
    })


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Sayfa bulunamadı"}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({"error": "Sunucu hatası"}), 500


if __name__ == "__main__":
    print("\n  [*] Njoy Emlak Web -- http://localhost:5000\n")
    app.run(debug=True, port=5000, use_reloader=False)
