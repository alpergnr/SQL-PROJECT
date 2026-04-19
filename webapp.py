#!/usr/bin/env python3
"""Njoy Emlak — Flask Web Application.

Reuses the NjoyRepository from app.py to serve a rich single-page
web interface for the real estate database.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from app import NjoyRepository, AppError, DEFAULT_DB_PATH, MAX_LIMIT

app = Flask(__name__)

repo = NjoyRepository(DEFAULT_DB_PATH)


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


# ─── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


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


@app.route("/api/benchmark")
def api_benchmark():
    metrics = repo.benchmark()
    return jsonify(metrics)


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
    app.run(debug=True, port=5000)
