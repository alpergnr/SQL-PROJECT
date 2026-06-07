#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_DB_PATH = Path(__file__).with_name("njoyemlak.db")
MAX_LIMIT = 200

logger = logging.getLogger("njoy_cli")


class AppError(Exception):
    """Application-level controlled error."""


@dataclass(frozen=True)
class Listing:
    ilan_id: int
    baslik: str
    fiyat: float
    ilce: str
    mahalle: str
    emlak_tipi: str
    brut_m2: int | None
    net_m2: int | None
    oda_sayisi: str | None
    danisman: str


@dataclass(frozen=True)
class AgentPortfolio:
    ad_soyad: str
    toplam_ilan: int
    toplam_portfoy: float | None


class NjoyRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        if not self._db_path.exists():
            raise AppError(f"Veritabanı bulunamadı: {self._db_path}")
        self._ensure_runtime_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        # Keep relational integrity checks active for every connection.
        conn.execute("PRAGMA foreign_keys = ON;")
        # Reduce transient lock errors during concurrent reads/writes.
        conn.execute("PRAGMA busy_timeout = 3000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_runtime_schema(self) -> None:
        schema = """
            CREATE TABLE IF NOT EXISTS Kullanicilar (
                KullaniciID INTEGER PRIMARY KEY AUTOINCREMENT,
                AdSoyad VARCHAR(100) NOT NULL,
                Email VARCHAR(120) NOT NULL UNIQUE,
                SifreHash TEXT NOT NULL,
                Rol VARCHAR(20) NOT NULL DEFAULT 'musteri',
                KayitTarihi TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS Kaydedilen_Ilanlar (
                KullaniciID INT NOT NULL,
                IlanID INT NOT NULL,
                KayitTarihi TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                PRIMARY KEY (KullaniciID, IlanID),
                FOREIGN KEY (KullaniciID) REFERENCES Kullanicilar(KullaniciID),
                FOREIGN KEY (IlanID) REFERENCES Emlaklar(IlanID)
            );

            CREATE TABLE IF NOT EXISTS Musteri_Sorulari (
                SoruID INTEGER PRIMARY KEY AUTOINCREMENT,
                KullaniciID INT NOT NULL,
                IlanID INT,
                SoruMetni TEXT NOT NULL,
                CevapMetni TEXT,
                Durum VARCHAR(20) NOT NULL DEFAULT 'Açık',
                SoruTarihi TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                CevapTarihi TEXT,
                Cevaplayan VARCHAR(100),
                FOREIGN KEY (KullaniciID) REFERENCES Kullanicilar(KullaniciID),
                FOREIGN KEY (IlanID) REFERENCES Emlaklar(IlanID)
            );

            CREATE TABLE IF NOT EXISTS Bildirimler (
                BildirimID INTEGER PRIMARY KEY AUTOINCREMENT,
                KullaniciID INT NOT NULL,
                IlanID INT,
                Tip VARCHAR(30) NOT NULL,
                Baslik VARCHAR(160) NOT NULL,
                Mesaj TEXT NOT NULL,
                Okundu INTEGER NOT NULL DEFAULT 0,
                OlusturmaTarihi TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (KullaniciID) REFERENCES Kullanicilar(KullaniciID),
                FOREIGN KEY (IlanID) REFERENCES Emlaklar(IlanID)
            );
        """
        with closing(self._connect()) as conn:
            conn.executescript(schema)
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(Emlaklar)").fetchall()
            }
            if "Aktif" not in columns:
                conn.execute(
                    "ALTER TABLE Emlaklar ADD COLUMN Aktif INTEGER NOT NULL DEFAULT 1"
                )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emlaklar_aktif ON Emlaklar(Aktif)")
            conn.commit()

    def _timed_fetchall(
        self, conn: sqlite3.Connection, query: str, params: Sequence[object], op_name: str
    ) -> list[sqlite3.Row]:
        start = time.perf_counter()
        rows = conn.execute(query, params).fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s completed in %.2f ms", op_name, elapsed_ms)
        return rows

    def list_listings(self, limit: int, sort_by: str) -> list[Listing]:
        query_map = {
            "fiyat_desc": """
                SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                       E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
                FROM Emlaklar E
                INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
                WHERE E.Aktif = 1
                ORDER BY E.Fiyat DESC
                LIMIT ?
            """,
            "fiyat_asc": """
                SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                       E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
                FROM Emlaklar E
                INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
                WHERE E.Aktif = 1
                ORDER BY E.Fiyat ASC
                LIMIT ?
            """,
            "m2_desc": """
                SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                       E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
                FROM Emlaklar E
                INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
                WHERE E.Aktif = 1
                ORDER BY E.NetM2 DESC
                LIMIT ?
            """,
            "ilanid_asc": """
                SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                       E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
                FROM Emlaklar E
                INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
                WHERE E.Aktif = 1
                ORDER BY E.IlanID ASC
                LIMIT ?
            """,
        }
        query = query_map.get(sort_by)
        if query is None:
            raise AppError(f"Geçersiz sıralama: {sort_by}")
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (limit,), "list_listings")
        return [self._row_to_listing(row) for row in rows]

    def search(
        self,
        max_price: float | None,
        districts: Sequence[str] | None,
        feature: str | None,
        limit: int,
    ) -> list[Listing]:
        params: list[object] = []
        where_clauses: list[str] = ["E.Aktif = 1"]
        joins = ""

        if max_price is not None:
            where_clauses.append("E.Fiyat <= ?")
            params.append(max_price)

        if districts:
            placeholders = ", ".join("?" for _ in districts)
            where_clauses.append("E.İlce IN (" + placeholders + ")")
            params.extend(districts)

        if feature:
            joins = """
                INNER JOIN Emlak_Ozellikleri EO ON EO.IlanID = E.IlanID
                INNER JOIN Ozellikler O ON O.OzellikID = EO.OzellikID
            """
            where_clauses.append("O.OzellikAdi = ?")
            params.append(feature)

        where_sql = "WHERE " + " AND ".join(where_clauses)
        query_parts = [
            """
            SELECT DISTINCT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                            E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            """.strip()
        ]
        if joins:
            query_parts.append(joins.strip())
        if where_sql:
            query_parts.append(where_sql)
        query_parts.append("ORDER BY E.Fiyat DESC")
        query_parts.append("LIMIT ?")
        query = "\n".join(query_parts)
        params.append(limit)
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, params, "search")
        return [self._row_to_listing(row) for row in rows]

    def agent_portfolios(self) -> list[AgentPortfolio]:
        query = """
            SELECT K.AdSoyad, COUNT(E.IlanID) AS ToplamIlan,
                   SUM(E.Fiyat) AS ToplamPortfoy
            FROM Ekip K
            LEFT JOIN Emlaklar E ON E.DanismanID = K.DanismanID AND E.Aktif = 1
            GROUP BY K.AdSoyad
            ORDER BY ToplamPortfoy DESC
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (), "agent_portfolios")
        return [
            AgentPortfolio(
                ad_soyad=row["AdSoyad"],
                toplam_ilan=row["ToplamIlan"],
                toplam_portfoy=row["ToplamPortfoy"],
            )
            for row in rows
        ]

    def listing_features(self, ilan_id: int) -> dict[str, list[str]]:
        query = """
            SELECT OK.KategoriAdi, O.OzellikAdi
            FROM Emlak_Ozellikleri EO
            INNER JOIN Emlaklar E ON E.IlanID = EO.IlanID
            INNER JOIN Ozellikler O ON O.OzellikID = EO.OzellikID
            INNER JOIN Ozellik_Kategorileri OK ON OK.KategoriID = O.KategoriID
            WHERE EO.IlanID = ? AND E.Aktif = 1
            ORDER BY OK.KategoriID, O.OzellikAdi
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (ilan_id,), "listing_features")
        result: dict[str, list[str]] = {}
        for row in rows:
            cat = row["KategoriAdi"]
            if cat not in result:
                result[cat] = []
            result[cat].append(row["OzellikAdi"])
        return result

    def benchmark(
        self, limit: int = 20, max_price: float = 50000, district: str = "Beyoğlu"
    ) -> dict[str, float]:
        metrics: dict[str, float] = {}
        start = time.perf_counter()
        self.list_listings(limit=limit, sort_by="fiyat_desc")
        metrics["list_ms"] = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        self.search(max_price=max_price, districts=[district], feature=None, limit=limit)
        metrics["search_ms"] = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        self.agent_portfolios()
        metrics["stats_ms"] = (time.perf_counter() - start) * 1000
        return metrics

    def advanced_analytics(self, limit: int = 10) -> dict[str, list[dict[str, object]]]:
        queries = {
            "region_analysis": """
                WITH BolgeOzet AS (
                    SELECT
                        İlce,
                        COUNT(*) AS IlanSayisi,
                        ROUND(AVG(Fiyat), 2) AS OrtalamaFiyat,
                        MIN(Fiyat) AS EnDusukFiyat,
                        MAX(Fiyat) AS EnYuksekFiyat,
                        ROUND(AVG(Fiyat / NULLIF(NetM2, 0)), 2) AS OrtalamaNetM2Fiyati
                    FROM Emlaklar
                    WHERE Aktif = 1
                    GROUP BY İlce
                )
                SELECT İlce, IlanSayisi, OrtalamaFiyat, EnDusukFiyat, EnYuksekFiyat,
                       OrtalamaNetM2Fiyati,
                       ROUND(EnYuksekFiyat - EnDusukFiyat, 2) AS FiyatAraligi
                FROM BolgeOzet
                ORDER BY OrtalamaFiyat DESC
                LIMIT ?
            """,
            "listing_ranking": """
                SELECT IlanID, Baslik, Fiyat, İlce, IlceIciFiyatSirasi, GenelFiyatSirasi
                FROM (
                    SELECT
                        IlanID,
                        Baslik,
                        Fiyat,
                        İlce,
                        RANK() OVER (PARTITION BY İlce ORDER BY Fiyat DESC) AS IlceIciFiyatSirasi,
                        ROW_NUMBER() OVER (ORDER BY Fiyat DESC) AS GenelFiyatSirasi
                    FROM Emlaklar
                    WHERE Aktif = 1
                )
                ORDER BY GenelFiyatSirasi
                LIMIT ?
            """,
            "agent_ranking": """
                SELECT AdSoyad, ToplamIlan, ToplamPortfoy, OrtalamaFiyat,
                       PortfoyDegeriSirasi, IlanSayisiSirasi
                FROM (
                    SELECT
                        AdSoyad,
                        ToplamIlan,
                        ToplamPortfoy,
                        OrtalamaFiyat,
                        RANK() OVER (ORDER BY ToplamPortfoy DESC) AS PortfoyDegeriSirasi,
                        RANK() OVER (ORDER BY ToplamIlan DESC) AS IlanSayisiSirasi
                    FROM (
                        SELECT
                            K.AdSoyad,
                            COUNT(E.IlanID) AS ToplamIlan,
                            COALESCE(SUM(E.Fiyat), 0) AS ToplamPortfoy,
                            ROUND(COALESCE(AVG(E.Fiyat), 0), 2) AS OrtalamaFiyat
                        FROM Ekip K
                        LEFT JOIN Emlaklar E
                            ON E.DanismanID = K.DanismanID AND E.Aktif = 1
                        GROUP BY K.DanismanID, K.AdSoyad
                    )
                )
                ORDER BY PortfoyDegeriSirasi
                LIMIT ?
            """,
            "room_pivot": """
                SELECT
                    İlce,
                    SUM(CASE WHEN OdaSayisi = '1+1' THEN 1 ELSE 0 END) AS Oda_1_1,
                    SUM(CASE WHEN OdaSayisi = '2+1' THEN 1 ELSE 0 END) AS Oda_2_1,
                    SUM(CASE WHEN OdaSayisi NOT IN ('1+1', '2+1') OR OdaSayisi IS NULL THEN 1 ELSE 0 END) AS Diger,
                    COUNT(*) AS Toplam
                FROM Emlaklar
                WHERE Aktif = 1
                GROUP BY İlce
                ORDER BY Toplam DESC, İlce
                LIMIT ?
            """,
        }
        with closing(self._connect()) as conn:
            return {
                name: self._dict_rows(self._timed_fetchall(conn, query, (limit,), name))
                for name, query in queries.items()
            }

    def explain_search_plan(
        self, max_price: float = 50000, district: str = "Beyoğlu", limit: int = 20
    ) -> list[dict[str, object]]:
        query = """
            EXPLAIN QUERY PLAN
            SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce
            FROM Emlaklar E
            WHERE E.Aktif = 1 AND E.Fiyat <= ? AND E.İlce = ?
            ORDER BY E.Fiyat DESC
            LIMIT ?
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(
                conn, query, (max_price, district, limit), "explain_search_plan"
            )
        return self._dict_rows(rows)

    def price_history(self, limit: int = 20) -> list[dict[str, object]]:
        query = """
            SELECT LogID, IlanID, Baslik, EskiFiyat, YeniFiyat,
                   DegisimYuzdesi, DegisimTarihi, Aciklama
            FROM v_fiyat_gecmisi
            LIMIT ?
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (limit,), "price_history")
        return self._dict_rows(rows)

    def listing_history(self, limit: int = 20) -> list[dict[str, object]]:
        query = """
            SELECT LogID, IlanID, Baslik, IslemTipi, AlanAdi, EskiDeger, YeniDeger,
                   DegisimTarihi, Kullanici, Aciklama
            FROM v_ilan_gecmisi
            LIMIT ?
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (limit,), "listing_history")
        return self._dict_rows(rows)

    def admin_listings(self, limit: int = 200) -> list[dict[str, object]]:
        query = """
            SELECT E.IlanID, E.DanismanID, E.Baslik, E.Fiyat, E.İl, E.İlce, E.Mahalle,
                   E.EmlakTipi, E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            WHERE E.Aktif = 1
            ORDER BY E.IlanID DESC
            LIMIT ?
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (limit,), "admin_listings")
            items = self._dict_rows(rows)
            feature_map = self._feature_ids_by_listing(
                conn, [int(item["IlanID"]) for item in items]
            )
        for item in items:
            item["FeatureIDs"] = feature_map.get(int(item["IlanID"]), [])
        return items

    def agents(self) -> list[dict[str, object]]:
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(
                conn,
                "SELECT DanismanID, AdSoyad, Unvan, Telefon FROM Ekip ORDER BY DanismanID",
                (),
                "agents",
            )
        return self._dict_rows(rows)

    def feature_catalog(self) -> list[dict[str, object]]:
        query = """
            SELECT OK.KategoriID, OK.KategoriAdi, O.OzellikID, O.OzellikAdi
            FROM Ozellik_Kategorileri OK
            INNER JOIN Ozellikler O ON O.KategoriID = OK.KategoriID
            ORDER BY OK.KategoriID, O.OzellikAdi
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (), "feature_catalog")

        groups: dict[int, dict[str, object]] = {}
        for row in rows:
            category_id = int(row["KategoriID"])
            if category_id not in groups:
                groups[category_id] = {
                    "kategori_id": category_id,
                    "kategori_adi": row["KategoriAdi"],
                    "features": [],
                }
            groups[category_id]["features"].append(
                {
                    "ozellik_id": row["OzellikID"],
                    "ozellik_adi": row["OzellikAdi"],
                }
            )
        return list(groups.values())

    def create_customer(
        self, ad_soyad: str, email: str, password_hash: str
    ) -> dict[str, object]:
        name = ad_soyad.strip()
        normalized_email = email.strip().lower()
        if not name:
            raise AppError("Ad soyad boş olamaz.")
        if "@" not in normalized_email:
            raise AppError("Geçerli bir e-posta girilmelidir.")
        if not password_hash:
            raise AppError("Şifre bilgisi boş olamaz.")

        with closing(self._connect()) as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO Kullanicilar (AdSoyad, Email, SifreHash, Rol)
                    VALUES (?, ?, ?, 'musteri')
                    """,
                    (name, normalized_email, password_hash),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise AppError("Bu e-posta ile kayıtlı kullanıcı var.") from None
        return self.get_customer(int(cur.lastrowid))

    def get_customer_by_email(self, email: str) -> dict[str, object] | None:
        normalized_email = email.strip().lower()
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT KullaniciID, AdSoyad, Email, SifreHash, Rol, KayitTarihi
                FROM Kullanicilar
                WHERE Email = ?
                """,
                (normalized_email,),
            ).fetchone()
        return dict(row) if row else None

    def get_customer(self, user_id: int) -> dict[str, object]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                """
                SELECT KullaniciID, AdSoyad, Email, Rol, KayitTarihi
                FROM Kullanicilar
                WHERE KullaniciID = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            raise AppError("Kullanıcı bulunamadı.")
        return dict(row)

    def saved_listing_ids(self, user_id: int) -> list[int]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT IlanID
                FROM Kaydedilen_Ilanlar
                WHERE KullaniciID = ?
                ORDER BY KayitTarihi DESC
                """,
                (user_id,),
            ).fetchall()
        return [int(row["IlanID"]) for row in rows]

    def saved_listings(self, user_id: int) -> list[dict[str, object]]:
        query = """
            SELECT E.IlanID, E.Baslik, E.Fiyat, E.İlce, E.Mahalle, E.EmlakTipi,
                   E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman,
                   KI.KayitTarihi
            FROM Kaydedilen_Ilanlar KI
            INNER JOIN Emlaklar E ON E.IlanID = KI.IlanID
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            WHERE KI.KullaniciID = ? AND E.Aktif = 1
            ORDER BY KI.KayitTarihi DESC
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (user_id,), "saved_listings")
        return self._dict_rows(rows)

    def save_listing(self, user_id: int, ilan_id: int) -> dict[str, object]:
        with closing(self._connect()) as conn:
            try:
                self._ensure_customer_exists(conn, user_id)
                self._ensure_listing_exists(conn, ilan_id)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO Kaydedilen_Ilanlar (KullaniciID, IlanID)
                    VALUES (?, ?)
                    """,
                    (user_id, ilan_id),
                )
                self._insert_notification(
                    conn,
                    user_id=user_id,
                    ilan_id=ilan_id,
                    tip="ILAN_KAYIT",
                    baslik="İlan kaydedildi",
                    mesaj=f"#{ilan_id} numaralı ilan kaydedilen ilanlarınıza eklendi.",
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_admin_listing(ilan_id)

    def unsave_listing(self, user_id: int, ilan_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "DELETE FROM Kaydedilen_Ilanlar WHERE KullaniciID = ? AND IlanID = ?",
                (user_id, ilan_id),
            )
            conn.commit()

    def ask_question(
        self, user_id: int, ilan_id: int | None, question: str
    ) -> dict[str, object]:
        text = question.strip()
        if not text:
            raise AppError("Soru metni boş olamaz.")
        with closing(self._connect()) as conn:
            try:
                self._ensure_customer_exists(conn, user_id)
                if ilan_id is not None:
                    self._ensure_listing_exists(conn, ilan_id)
                cur = conn.execute(
                    """
                    INSERT INTO Musteri_Sorulari (KullaniciID, IlanID, SoruMetni)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, ilan_id, text),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_question(int(cur.lastrowid))

    def customer_questions(self, user_id: int) -> list[dict[str, object]]:
        query = """
            SELECT S.SoruID, S.KullaniciID, S.IlanID, E.Baslik, S.SoruMetni,
                   S.CevapMetni, S.Durum, S.SoruTarihi, S.CevapTarihi, S.Cevaplayan
            FROM Musteri_Sorulari S
            LEFT JOIN Emlaklar E ON E.IlanID = S.IlanID
            WHERE S.KullaniciID = ?
            ORDER BY S.SoruTarihi DESC, S.SoruID DESC
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (user_id,), "customer_questions")
        return self._dict_rows(rows)

    def admin_questions(self) -> list[dict[str, object]]:
        query = """
            SELECT S.SoruID, S.KullaniciID, U.AdSoyad, U.Email, S.IlanID, E.Baslik,
                   S.SoruMetni, S.CevapMetni, S.Durum, S.SoruTarihi, S.CevapTarihi,
                   S.Cevaplayan
            FROM Musteri_Sorulari S
            INNER JOIN Kullanicilar U ON U.KullaniciID = S.KullaniciID
            LEFT JOIN Emlaklar E ON E.IlanID = S.IlanID
            ORDER BY CASE WHEN S.Durum = 'Açık' THEN 0 ELSE 1 END, S.SoruTarihi DESC
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (), "admin_questions")
        return self._dict_rows(rows)

    def get_question(self, question_id: int) -> dict[str, object]:
        query = """
            SELECT S.SoruID, S.KullaniciID, U.AdSoyad, U.Email, S.IlanID, E.Baslik,
                   S.SoruMetni, S.CevapMetni, S.Durum, S.SoruTarihi, S.CevapTarihi,
                   S.Cevaplayan
            FROM Musteri_Sorulari S
            INNER JOIN Kullanicilar U ON U.KullaniciID = S.KullaniciID
            LEFT JOIN Emlaklar E ON E.IlanID = S.IlanID
            WHERE S.SoruID = ?
        """
        with closing(self._connect()) as conn:
            row = conn.execute(query, (question_id,)).fetchone()
        if row is None:
            raise AppError("Soru bulunamadı.")
        return dict(row)

    def answer_question(
        self, question_id: int, answer: str, admin_user: str
    ) -> dict[str, object]:
        text = answer.strip()
        if not text:
            raise AppError("Cevap metni boş olamaz.")
        with closing(self._connect()) as conn:
            try:
                row = conn.execute(
                    "SELECT SoruID, KullaniciID, IlanID FROM Musteri_Sorulari WHERE SoruID = ?",
                    (question_id,),
                ).fetchone()
                if row is None:
                    raise AppError("Soru bulunamadı.")
                conn.execute(
                    """
                    UPDATE Musteri_Sorulari
                    SET CevapMetni = ?, Durum = 'Cevaplandı',
                        CevapTarihi = datetime('now', 'localtime'), Cevaplayan = ?
                    WHERE SoruID = ?
                    """,
                    (text, admin_user, question_id),
                )
                self._insert_notification(
                    conn,
                    user_id=int(row["KullaniciID"]),
                    ilan_id=row["IlanID"],
                    tip="MESAJ",
                    baslik="Sorunuz cevaplandı",
                    mesaj=f"#{question_id} numaralı sorunuza admin cevap verdi.",
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_question(question_id)

    def notifications(self, user_id: int, limit: int = 50) -> list[dict[str, object]]:
        query = """
            SELECT B.BildirimID, B.KullaniciID, B.IlanID, E.Baslik AS IlanBaslik,
                   B.Tip, B.Baslik, B.Mesaj, B.Okundu, B.OlusturmaTarihi
            FROM Bildirimler B
            LEFT JOIN Emlaklar E ON E.IlanID = B.IlanID
            WHERE B.KullaniciID = ?
            ORDER BY B.Okundu ASC, B.OlusturmaTarihi DESC, B.BildirimID DESC
            LIMIT ?
        """
        with closing(self._connect()) as conn:
            rows = self._timed_fetchall(conn, query, (user_id, limit), "notifications")
        return self._dict_rows(rows)

    def mark_notifications_read(self, user_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE Bildirimler SET Okundu = 1 WHERE KullaniciID = ?", (user_id,)
            )
            conn.commit()

    def customer_dashboard(self, user_id: int) -> dict[str, object]:
        return {
            "user": self.get_customer(user_id),
            "listings": self.admin_listings(limit=200),
            "saved_ids": self.saved_listing_ids(user_id),
            "saved_listings": self.saved_listings(user_id),
            "questions": self.customer_questions(user_id),
            "notifications": self.notifications(user_id),
        }

    def create_listing(self, payload: dict[str, object], user: str) -> dict[str, object]:
        data = self._normalize_listing_payload(payload, partial=False)
        feature_ids = self._normalize_feature_ids(payload.get("feature_ids"))
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                self._ensure_agent_exists(conn, int(data["DanismanID"]))
                self._ensure_features_exist(conn, feature_ids)
                cur = conn.execute(
                    """
                    INSERT INTO Emlaklar (
                        DanismanID, Baslik, Fiyat, İl, İlce, Mahalle,
                        EmlakTipi, BrutM2, NetM2, OdaSayisi
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["DanismanID"],
                        data["Baslik"],
                        data["Fiyat"],
                        data["İl"],
                        data["İlce"],
                        data["Mahalle"],
                        data["EmlakTipi"],
                        data["BrutM2"],
                        data["NetM2"],
                        data["OdaSayisi"],
                    ),
                )
                ilan_id = int(cur.lastrowid)
                self._insert_listing_log(
                    conn,
                    ilan_id=ilan_id,
                    islem_tipi="EKLEME",
                    alan_adi=None,
                    eski_deger=None,
                    yeni_deger=f"{data['Baslik']} | {data['Fiyat']} TL",
                    user=user,
                    note="Admin panelinden yeni ilan eklendi.",
                )
                self._replace_listing_features(conn, ilan_id, feature_ids)
                if feature_ids:
                    self._insert_listing_log(
                        conn,
                        ilan_id=ilan_id,
                        islem_tipi="OZELLIK_GUNCELLEME",
                        alan_adi="Özellikler",
                        eski_deger=None,
                        yeni_deger=", ".join(self._feature_names(conn, feature_ids)),
                        user=user,
                        note="Yeni ilan özellikleri eklendi.",
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_admin_listing(ilan_id)

    def update_listing(
        self, ilan_id: int, payload: dict[str, object], user: str, note: str | None = None
    ) -> dict[str, object]:
        data = self._normalize_listing_payload(payload, partial=True)
        has_feature_update = "feature_ids" in payload
        feature_ids = (
            self._normalize_feature_ids(payload.get("feature_ids"))
            if has_feature_update
            else None
        )
        if not data and not has_feature_update:
            raise AppError("Güncellenecek alan bulunamadı.")

        field_labels = {
            "DanismanID": "Danışman",
            "Baslik": "Başlık",
            "Fiyat": "Fiyat",
            "İl": "İl",
            "İlce": "İlçe",
            "Mahalle": "Mahalle",
            "EmlakTipi": "Emlak Tipi",
            "BrutM2": "Brüt m²",
            "NetM2": "Net m²",
            "OdaSayisi": "Oda Sayısı",
        }

        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT * FROM Emlaklar WHERE IlanID = ? AND Aktif = 1",
                    (ilan_id,),
                ).fetchone()
                if row is None:
                    raise AppError(f"İlan bulunamadı: {ilan_id}")
                if "DanismanID" in data:
                    self._ensure_agent_exists(conn, int(data["DanismanID"]))
                if feature_ids is not None:
                    self._ensure_features_exist(conn, feature_ids)

                changes: list[tuple[str, object, object]] = []
                for db_field, new_value in data.items():
                    old_value = row[db_field]
                    if self._values_equal(old_value, new_value):
                        continue
                    changes.append((db_field, old_value, new_value))

                old_feature_ids: list[int] = []
                feature_changed = False
                if feature_ids is not None:
                    old_feature_ids = self._feature_ids_by_listing(conn, [ilan_id]).get(
                        ilan_id, []
                    )
                    feature_changed = set(old_feature_ids) != set(feature_ids)

                if not changes and not feature_changed:
                    raise AppError("Gönderilen bilgiler mevcut ilanla aynı.")

                if changes:
                    set_sql = ", ".join(f"{field} = ?" for field, _, _ in changes)
                    params = [new for _, _, new in changes]
                    params.append(ilan_id)
                    conn.execute(f"UPDATE Emlaklar SET {set_sql} WHERE IlanID = ?", params)

                for db_field, old_value, new_value in changes:
                    islem_tipi = "FIYAT_GUNCELLEME" if db_field == "Fiyat" else "GUNCELLEME"
                    field_label = field_labels[db_field]
                    self._insert_listing_log(
                        conn,
                        ilan_id=ilan_id,
                        islem_tipi=islem_tipi,
                        alan_adi=field_label,
                        eski_deger=self._display_value(old_value),
                        yeni_deger=self._display_value(new_value),
                        user=user,
                        note=note or "Admin panelinden ilan güncellendi.",
                    )
                    self._notify_saved_listing_watchers(
                        conn,
                        ilan_id=ilan_id,
                        alan_adi=field_label,
                        eski_deger=self._display_value(old_value),
                        yeni_deger=self._display_value(new_value),
                    )
                if feature_changed and feature_ids is not None:
                    self._replace_listing_features(conn, ilan_id, feature_ids)
                    self._insert_listing_log(
                        conn,
                        ilan_id=ilan_id,
                        islem_tipi="OZELLIK_GUNCELLEME",
                        alan_adi="Özellikler",
                        eski_deger=", ".join(self._feature_names(conn, old_feature_ids)) or None,
                        yeni_deger=", ".join(self._feature_names(conn, feature_ids)) or None,
                        user=user,
                        note=note or "Admin panelinden ilan özellikleri güncellendi.",
                    )
                    self._notify_saved_listing_watchers(
                        conn,
                        ilan_id=ilan_id,
                        alan_adi="Özellikler",
                        eski_deger=", ".join(self._feature_names(conn, old_feature_ids)) or None,
                        yeni_deger=", ".join(self._feature_names(conn, feature_ids)) or None,
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return self.get_admin_listing(ilan_id)

    def delete_listing(self, ilan_id: int, user: str, note: str | None = None) -> dict[str, object]:
        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT IlanID, Baslik, Fiyat
                    FROM Emlaklar
                    WHERE IlanID = ? AND Aktif = 1
                    """,
                    (ilan_id,),
                ).fetchone()
                if row is None:
                    raise AppError(f"İlan bulunamadı: {ilan_id}")

                watchers = conn.execute(
                    """
                    SELECT KullaniciID
                    FROM Kaydedilen_Ilanlar
                    WHERE IlanID = ?
                    """,
                    (ilan_id,),
                ).fetchall()
                for watcher in watchers:
                    self._insert_notification(
                        conn,
                        user_id=int(watcher["KullaniciID"]),
                        ilan_id=ilan_id,
                        tip="ILAN_SILME",
                        baslik="Kaydettiğiniz ilan kaldırıldı",
                        mesaj=f"Kaydettiğiniz #{ilan_id} numaralı ilan yayından kaldırıldı.",
                    )

                conn.execute("DELETE FROM Kaydedilen_Ilanlar WHERE IlanID = ?", (ilan_id,))
                conn.execute("UPDATE Emlaklar SET Aktif = 0 WHERE IlanID = ?", (ilan_id,))
                self._insert_listing_log(
                    conn,
                    ilan_id=ilan_id,
                    islem_tipi="SILME",
                    alan_adi="İlan",
                    eski_deger=f"{row['Baslik']} | {self._display_value(row['Fiyat'])} TL",
                    yeni_deger="Yayından kaldırıldı",
                    user=user,
                    note=note or "Admin panelinden ilan silindi.",
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return {
            "IlanID": ilan_id,
            "Baslik": row["Baslik"],
            "Aktif": 0,
            "BildirimSayisi": len(watchers),
        }

    def get_admin_listing(self, ilan_id: int) -> dict[str, object]:
        query = """
            SELECT E.IlanID, E.DanismanID, E.Baslik, E.Fiyat, E.İl, E.İlce, E.Mahalle,
                   E.EmlakTipi, E.BrutM2, E.NetM2, E.OdaSayisi, K.AdSoyad AS Danisman
            FROM Emlaklar E
            INNER JOIN Ekip K ON K.DanismanID = E.DanismanID
            WHERE E.IlanID = ? AND E.Aktif = 1
        """
        with closing(self._connect()) as conn:
            row = conn.execute(query, (ilan_id,)).fetchone()
            feature_ids = self._feature_ids_by_listing(conn, [ilan_id]).get(ilan_id, [])
        if row is None:
            raise AppError(f"İlan bulunamadı: {ilan_id}")
        result = dict(row)
        result["FeatureIDs"] = feature_ids
        return result

    def update_listing_price(
        self, ilan_id: int, new_price: float, note: str | None = None, user: str = "CLI"
    ) -> dict[str, object]:
        if new_price <= 0:
            raise AppError("Yeni fiyat pozitif olmalıdır.")

        with closing(self._connect()) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT IlanID, Baslik, Fiyat FROM Emlaklar WHERE IlanID = ? AND Aktif = 1",
                    (ilan_id,),
                ).fetchone()
                if row is None:
                    raise AppError(f"İlan bulunamadı: {ilan_id}")
                old_price = float(row["Fiyat"])
                if old_price == new_price:
                    raise AppError("Yeni fiyat mevcut fiyatla aynı olamaz.")

                conn.execute(
                    "UPDATE Emlaklar SET Fiyat = ? WHERE IlanID = ?",
                    (new_price, ilan_id),
                )
                self._insert_listing_log(
                    conn,
                    ilan_id=ilan_id,
                    islem_tipi="FIYAT_GUNCELLEME",
                    alan_adi="Fiyat",
                    eski_deger=self._display_value(old_price),
                    yeni_deger=self._display_value(new_price),
                    user=user,
                    note=note or "Fiyat güncellendi.",
                )
                self._notify_saved_listing_watchers(
                    conn,
                    ilan_id=ilan_id,
                    alan_adi="Fiyat",
                    eski_deger=self._display_value(old_price),
                    yeni_deger=self._display_value(new_price),
                )
                log_row = conn.execute(
                    """
                    SELECT LogID, IlanID, EskiFiyat, YeniFiyat, DegisimYuzdesi,
                           DegisimTarihi, Aciklama
                    FROM Fiyat_Degisim_Log
                    WHERE IlanID = ?
                    ORDER BY LogID DESC
                    LIMIT 1
                    """,
                    (ilan_id,),
                ).fetchone()
                if note and log_row is not None:
                    conn.execute(
                        "UPDATE Fiyat_Degisim_Log SET Aciklama = ? WHERE LogID = ?",
                        (note, log_row["LogID"]),
                    )
                    log_row = conn.execute(
                        """
                        SELECT LogID, IlanID, EskiFiyat, YeniFiyat, DegisimYuzdesi,
                               DegisimTarihi, Aciklama
                        FROM Fiyat_Degisim_Log
                        WHERE LogID = ?
                        """,
                        (log_row["LogID"],),
                    ).fetchone()
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        if log_row is None:
            raise AppError("Fiyat güncellendi ancak audit kaydı oluşturulamadı.")
        result = dict(log_row)
        result["Baslik"] = row["Baslik"]
        return result

    def backup_database(self, output_path: Path) -> Path:
        target = output_path.expanduser()
        if target.exists() and target.is_dir():
            raise AppError("Backup hedefi dosya olmalıdır, klasör değil.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as source, closing(sqlite3.connect(str(target))) as dest:
            source.backup(dest)
            dest.commit()
        return target.resolve()

    @staticmethod
    def _row_to_listing(row: sqlite3.Row) -> Listing:
        return Listing(
            ilan_id=row["IlanID"],
            baslik=row["Baslik"],
            fiyat=row["Fiyat"],
            ilce=row["İlce"],
            mahalle=row["Mahalle"],
            emlak_tipi=row["EmlakTipi"],
            brut_m2=row["BrutM2"],
            net_m2=row["NetM2"],
            oda_sayisi=row["OdaSayisi"],
            danisman=row["Danisman"],
        )

    @staticmethod
    def _dict_rows(rows: Sequence[sqlite3.Row]) -> list[dict[str, object]]:
        return [dict(row) for row in rows]

    @staticmethod
    def _insert_listing_log(
        conn: sqlite3.Connection,
        ilan_id: int,
        islem_tipi: str,
        alan_adi: str | None,
        eski_deger: str | None,
        yeni_deger: str | None,
        user: str,
        note: str | None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO Ilan_Degisim_Log (
                IlanID, IslemTipi, AlanAdi, EskiDeger, YeniDeger, Kullanici, Aciklama
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ilan_id, islem_tipi, alan_adi, eski_deger, yeni_deger, user, note),
        )

    @staticmethod
    def _values_equal(old_value: object, new_value: object) -> bool:
        if old_value is None and new_value in (None, ""):
            return True
        if isinstance(old_value, (int, float)) or isinstance(new_value, (int, float)):
            try:
                return float(old_value) == float(new_value)
            except (TypeError, ValueError):
                return False
        return str(old_value or "") == str(new_value or "")

    @staticmethod
    def _display_value(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _normalize_listing_payload(
        payload: dict[str, object], partial: bool
    ) -> dict[str, object]:
        key_map = {
            "danisman_id": "DanismanID",
            "baslik": "Baslik",
            "fiyat": "Fiyat",
            "il": "İl",
            "ilce": "İlce",
            "mahalle": "Mahalle",
            "emlak_tipi": "EmlakTipi",
            "brut_m2": "BrutM2",
            "net_m2": "NetM2",
            "oda_sayisi": "OdaSayisi",
        }
        required = {
            "danisman_id",
            "baslik",
            "fiyat",
            "ilce",
            "mahalle",
            "emlak_tipi",
            "brut_m2",
            "net_m2",
            "oda_sayisi",
        }
        normalized: dict[str, object] = {}

        for input_key, db_key in key_map.items():
            if input_key not in payload:
                if not partial and input_key in required:
                    raise AppError(f"{input_key} alanı zorunludur.")
                continue
            value = payload.get(input_key)
            if isinstance(value, str):
                value = value.strip()
            if value in (None, ""):
                if not partial and input_key in required:
                    raise AppError(f"{input_key} alanı boş olamaz.")
                normalized[db_key] = None
                continue

            if input_key == "danisman_id":
                try:
                    normalized[db_key] = int(value)
                except (TypeError, ValueError):
                    raise AppError("danisman_id sayısal olmalıdır.") from None
            elif input_key == "fiyat":
                try:
                    price = float(value)
                except (TypeError, ValueError):
                    raise AppError("fiyat sayısal olmalıdır.") from None
                if price <= 0:
                    raise AppError("fiyat pozitif olmalıdır.")
                normalized[db_key] = price
            elif input_key in {"brut_m2", "net_m2"}:
                try:
                    m2 = int(value)
                except (TypeError, ValueError):
                    raise AppError(f"{input_key} sayısal olmalıdır.") from None
                if m2 <= 0:
                    raise AppError(f"{input_key} pozitif olmalıdır.")
                normalized[db_key] = m2
            else:
                normalized[db_key] = str(value)

        if not partial and "İl" not in normalized:
            normalized["İl"] = "İstanbul"
        return normalized

    @staticmethod
    def _ensure_agent_exists(conn: sqlite3.Connection, danisman_id: int) -> None:
        row = conn.execute(
            "SELECT DanismanID FROM Ekip WHERE DanismanID = ?", (danisman_id,)
        ).fetchone()
        if row is None:
            raise AppError(f"Danışman bulunamadı: {danisman_id}")

    @staticmethod
    def _ensure_customer_exists(conn: sqlite3.Connection, user_id: int) -> None:
        row = conn.execute(
            "SELECT KullaniciID FROM Kullanicilar WHERE KullaniciID = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise AppError("Kullanıcı bulunamadı.")

    @staticmethod
    def _ensure_listing_exists(conn: sqlite3.Connection, ilan_id: int) -> None:
        row = conn.execute(
            "SELECT IlanID FROM Emlaklar WHERE IlanID = ? AND Aktif = 1",
            (ilan_id,),
        ).fetchone()
        if row is None:
            raise AppError(f"İlan bulunamadı: {ilan_id}")

    @staticmethod
    def _insert_notification(
        conn: sqlite3.Connection,
        user_id: int,
        ilan_id: int | None,
        tip: str,
        baslik: str,
        mesaj: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO Bildirimler (KullaniciID, IlanID, Tip, Baslik, Mesaj)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, ilan_id, tip, baslik, mesaj),
        )

    @classmethod
    def _notify_saved_listing_watchers(
        cls,
        conn: sqlite3.Connection,
        ilan_id: int,
        alan_adi: str,
        eski_deger: str | None,
        yeni_deger: str | None,
    ) -> None:
        users = conn.execute(
            """
            SELECT KullaniciID
            FROM Kaydedilen_Ilanlar
            WHERE IlanID = ?
            """,
            (ilan_id,),
        ).fetchall()
        if not users:
            return
        message = (
            f"Kaydettiğiniz #{ilan_id} numaralı ilanda {alan_adi} değişti: "
            f"{eski_deger or '-'} → {yeni_deger or '-'}."
        )
        for user in users:
            cls._insert_notification(
                conn,
                user_id=int(user["KullaniciID"]),
                ilan_id=ilan_id,
                tip="ILAN_DEGISIKLIK",
                baslik="Kaydettiğiniz ilan güncellendi",
                mesaj=message,
            )

    @staticmethod
    def _normalize_feature_ids(value: object) -> list[int]:
        if value in (None, ""):
            return []
        raw_values: list[object]
        if isinstance(value, (list, tuple, set)):
            raw_values = list(value)
        else:
            raw_values = [value]

        result: list[int] = []
        seen: set[int] = set()
        for raw in raw_values:
            if raw in (None, ""):
                continue
            try:
                feature_id = int(raw)
            except (TypeError, ValueError):
                raise AppError("feature_ids sayısal değerlerden oluşmalıdır.") from None
            if feature_id <= 0:
                raise AppError("feature_ids pozitif değerlerden oluşmalıdır.")
            if feature_id not in seen:
                seen.add(feature_id)
                result.append(feature_id)
        return result

    @staticmethod
    def _ensure_features_exist(conn: sqlite3.Connection, feature_ids: Sequence[int]) -> None:
        if not feature_ids:
            return
        placeholders = ", ".join("?" for _ in feature_ids)
        rows = conn.execute(
            f"SELECT OzellikID FROM Ozellikler WHERE OzellikID IN ({placeholders})",
            tuple(feature_ids),
        ).fetchall()
        found = {int(row["OzellikID"]) for row in rows}
        missing = [feature_id for feature_id in feature_ids if feature_id not in found]
        if missing:
            raise AppError(f"Geçersiz özellik ID: {', '.join(map(str, missing))}")

    @staticmethod
    def _feature_ids_by_listing(
        conn: sqlite3.Connection, listing_ids: Sequence[int]
    ) -> dict[int, list[int]]:
        if not listing_ids:
            return {}
        placeholders = ", ".join("?" for _ in listing_ids)
        rows = conn.execute(
            f"""
            SELECT IlanID, OzellikID
            FROM Emlak_Ozellikleri
            WHERE IlanID IN ({placeholders})
            ORDER BY IlanID, OzellikID
            """,
            tuple(listing_ids),
        ).fetchall()
        result = {int(listing_id): [] for listing_id in listing_ids}
        for row in rows:
            result[int(row["IlanID"])].append(int(row["OzellikID"]))
        return result

    @staticmethod
    def _replace_listing_features(
        conn: sqlite3.Connection, ilan_id: int, feature_ids: Sequence[int]
    ) -> None:
        conn.execute("DELETE FROM Emlak_Ozellikleri WHERE IlanID = ?", (ilan_id,))
        conn.executemany(
            "INSERT INTO Emlak_Ozellikleri (IlanID, OzellikID) VALUES (?, ?)",
            [(ilan_id, feature_id) for feature_id in feature_ids],
        )

    @staticmethod
    def _feature_names(conn: sqlite3.Connection, feature_ids: Sequence[int]) -> list[str]:
        if not feature_ids:
            return []
        placeholders = ", ".join("?" for _ in feature_ids)
        rows = conn.execute(
            f"""
            SELECT OzellikID, OzellikAdi
            FROM Ozellikler
            WHERE OzellikID IN ({placeholders})
            """,
            tuple(feature_ids),
        ).fetchall()
        names_by_id = {int(row["OzellikID"]): row["OzellikAdi"] for row in rows}
        return [names_by_id[feature_id] for feature_id in feature_ids if feature_id in names_by_id]


def format_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    str_rows = [[str(c) if c is not None else "-" for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def _fmt(row: Sequence[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    line = "-+-".join("-" * w for w in widths)
    rendered = [_fmt(list(headers)), line]
    rendered.extend(_fmt(row) for row in str_rows)
    return "\n".join(rendered)


def _add_common_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite db yolu")
    parser.add_argument("--limit", type=int, default=20, help="Maksimum kayıt sayısı")
    parser.add_argument(
        "--output",
        choices=["table", "json", "csv"],
        default="table",
        help="Çıktı formatı",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Njoy Emlak SQLite veritabanı için profesyonel CLI aracı"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="İlanları listele")
    _add_common_filters(list_cmd)
    list_cmd.add_argument(
        "--sort-by",
        choices=["fiyat_desc", "fiyat_asc", "m2_desc", "ilanid_asc"],
        default="fiyat_desc",
        help="Sıralama tipi",
    )

    search_cmd = sub.add_parser("search", help="Filtreli ilan araması")
    _add_common_filters(search_cmd)
    search_cmd.add_argument("--max-price", type=float, help="Maksimum fiyat")
    search_cmd.add_argument(
        "--district",
        action="append",
        dest="districts",
        help="İlçe filtresi (birden fazla verilebilir)",
    )
    search_cmd.add_argument("--feature", help="Özellik adına göre filtre")

    stats_cmd = sub.add_parser("stats", help="Danışman portföy istatistikleri")
    _add_common_filters(stats_cmd)

    benchmark_cmd = sub.add_parser("benchmark", help="Temel sorgu performans ölçümü")
    _add_common_filters(benchmark_cmd)
    benchmark_cmd.add_argument(
        "--bench-max-price",
        type=float,
        default=50000,
        help="Benchmark arama adımı için maksimum fiyat",
    )
    benchmark_cmd.add_argument(
        "--bench-district",
        default="Beyoğlu",
        help="Benchmark arama adımı için ilçe",
    )

    analytics_cmd = sub.add_parser("analytics", help="CTE, window ve pivot analizleri")
    _add_common_filters(analytics_cmd)

    explain_cmd = sub.add_parser("explain", help="Index kullanımını EXPLAIN ile göster")
    _add_common_filters(explain_cmd)
    explain_cmd.add_argument(
        "--explain-max-price",
        type=float,
        default=50000,
        help="EXPLAIN araması için maksimum fiyat",
    )
    explain_cmd.add_argument(
        "--explain-district",
        default="Beyoğlu",
        help="EXPLAIN araması için ilçe",
    )

    history_cmd = sub.add_parser("price-history", help="Trigger ile oluşan fiyat geçmişi")
    _add_common_filters(history_cmd)

    update_cmd = sub.add_parser(
        "update-price", help="Fiyatı transaction içinde güncelle ve audit triggerını çalıştır"
    )
    update_cmd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite db yolu")
    update_cmd.add_argument("--output", choices=["table", "json", "csv"], default="table")
    update_cmd.add_argument("ilan_id", type=int, help="Güncellenecek ilan ID")
    update_cmd.add_argument("new_price", type=float, help="Yeni fiyat")
    update_cmd.add_argument("--note", help="Audit kaydına yazılacak açıklama")

    backup_cmd = sub.add_parser("backup", help="SQLite backup dosyası oluştur")
    backup_cmd.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite db yolu")
    backup_cmd.add_argument("--output", choices=["table", "json", "csv"], default="table")
    backup_cmd.add_argument(
        "--backup-path",
        type=Path,
        default=Path("backups") / "njoyemlak_backup.db",
        help="Oluşturulacak backup dosyası",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if hasattr(args, "limit"):
        if args.limit <= 0:
            raise AppError("--limit pozitif bir sayı olmalıdır.")
        if args.limit > MAX_LIMIT:
            raise AppError(f"--limit en fazla {MAX_LIMIT} olabilir.")
    if getattr(args, "max_price", None) is not None and args.max_price < 0:
        raise AppError("--max-price negatif olamaz.")
    if hasattr(args, "districts") and args.districts is not None:
        districts = [d.strip() for d in args.districts if d and d.strip()]
        if len(districts) != len(args.districts):
            raise AppError("İlçe değerleri boş veya sadece boşluk karakterlerinden oluşamaz.")
        seen: set[str] = set()
        deduped: list[str] = []
        for district in districts:
            if district not in seen:
                seen.add(district)
                deduped.append(district)
        args.districts = deduped
    if hasattr(args, "feature") and args.feature is not None:
        feature = args.feature.strip()
        if not feature:
            raise AppError("--feature boş olamaz.")
        args.feature = feature
    if hasattr(args, "bench_district"):
        args.bench_district = args.bench_district.strip()
        if not args.bench_district:
            raise AppError("--bench-district boş veya sadece boşluk olamaz.")
    if hasattr(args, "bench_max_price") and args.bench_max_price < 0:
        raise AppError("--bench-max-price negatif olamaz.")
    if hasattr(args, "explain_district"):
        args.explain_district = args.explain_district.strip()
        if not args.explain_district:
            raise AppError("--explain-district boş veya sadece boşluk olamaz.")
    if hasattr(args, "explain_max_price") and args.explain_max_price < 0:
        raise AppError("--explain-max-price negatif olamaz.")
    if hasattr(args, "ilan_id") and args.ilan_id <= 0:
        raise AppError("ilan_id pozitif bir sayı olmalıdır.")
    if hasattr(args, "new_price") and args.new_price <= 0:
        raise AppError("new_price pozitif bir sayı olmalıdır.")
    if hasattr(args, "note") and args.note is not None:
        args.note = args.note.strip()
        if not args.note:
            raise AppError("--note boş olamaz.")


def _render_output(
    headers: Sequence[str], rows: list[Sequence[object]], output: str, empty_message: str
) -> str:
    if not rows:
        return empty_message
    if output == "table":
        return format_table(headers, rows)
    if output == "json":
        payload = [dict(zip(headers, row)) for row in rows]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if output == "csv":
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(headers)
        writer.writerows(rows)
        return out.getvalue().strip()
    raise AppError(f"Geçersiz çıktı formatı: {output}")


def cmd_list(repo: NjoyRepository, args: argparse.Namespace) -> str:
    items = repo.list_listings(limit=args.limit, sort_by=args.sort_by)
    headers = ["IlanID", "Başlık", "Fiyat", "İlçe", "Mahalle", "Tip", "Danışman"]
    rows = [
        (
            i.ilan_id,
            i.baslik,
            f"{i.fiyat:,.0f}",
            i.ilce,
            i.mahalle,
            i.emlak_tipi,
            i.danisman,
        )
        for i in items
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=args.output,
        empty_message="Kayıt bulunamadı.",
    )


def cmd_search(repo: NjoyRepository, args: argparse.Namespace) -> str:
    items = repo.search(
        max_price=args.max_price,
        districts=args.districts,
        feature=args.feature,
        limit=args.limit,
    )
    headers = ["IlanID", "Başlık", "Fiyat", "İlçe", "Mahalle", "Tip"]
    rows = [
        (i.ilan_id, i.baslik, f"{i.fiyat:,.0f}", i.ilce, i.mahalle, i.emlak_tipi)
        for i in items
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=args.output,
        empty_message="Filtrelere uygun kayıt bulunamadı.",
    )


def cmd_stats(repo: NjoyRepository, _args: argparse.Namespace) -> str:
    stats = repo.agent_portfolios()
    headers = ["Danışman", "İlan Sayısı", "Toplam Portföy (TL)"]
    rows = [
        (s.ad_soyad, s.toplam_ilan, f"{(s.toplam_portfoy or 0):,.0f}") for s in stats
    ]
    return _render_output(
        headers=headers,
        rows=rows,
        output=_args.output,
        empty_message="İstatistik bulunamadı.",
    )


def cmd_benchmark(repo: NjoyRepository, args: argparse.Namespace) -> str:
    metrics = repo.benchmark(
        limit=args.limit,
        max_price=args.bench_max_price,
        district=args.bench_district,
    )
    rows = [(name, f"{value:.2f}") for name, value in metrics.items()]
    return _render_output(
        headers=["Sorgu", "Süre (ms)"],
        rows=rows,
        output=args.output,
        empty_message="Benchmark verisi bulunamadı.",
    )


def cmd_analytics(repo: NjoyRepository, args: argparse.Namespace) -> str:
    data = repo.advanced_analytics(limit=args.limit)
    if args.output == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)

    rows: list[Sequence[object]] = []
    for row in data["region_analysis"]:
        rows.append(
            (
                "CTE Bölge",
                row["İlce"],
                f"İlan: {row['IlanSayisi']}",
                f"Ort. fiyat: {float(row['OrtalamaFiyat']):,.0f}",
                f"Ort. net m²: {float(row['OrtalamaNetM2Fiyati'] or 0):,.0f}",
            )
        )
    for row in data["listing_ranking"]:
        rows.append(
            (
                "Window İlan",
                f"#{row['IlanID']}",
                f"Genel sıra: {row['GenelFiyatSirasi']}",
                f"İlçe sıra: {row['IlceIciFiyatSirasi']}",
                f"Fiyat: {float(row['Fiyat']):,.0f}",
            )
        )
    for row in data["agent_ranking"]:
        rows.append(
            (
                "Window Danışman",
                row["AdSoyad"],
                f"Portföy sıra: {row['PortfoyDegeriSirasi']}",
                f"İlan: {row['ToplamIlan']}",
                f"Toplam: {float(row['ToplamPortfoy']):,.0f}",
            )
        )
    for row in data["room_pivot"]:
        rows.append(
            (
                "Pivot Oda",
                row["İlce"],
                f"1+1: {row['Oda_1_1']}",
                f"2+1: {row['Oda_2_1']}",
                f"Toplam: {row['Toplam']}",
            )
        )

    return _render_output(
        headers=["Analiz", "Anahtar", "Metrik 1", "Metrik 2", "Metrik 3"],
        rows=rows,
        output=args.output,
        empty_message="Analiz verisi bulunamadı.",
    )


def cmd_explain(repo: NjoyRepository, args: argparse.Namespace) -> str:
    rows_dict = repo.explain_search_plan(
        max_price=args.explain_max_price,
        district=args.explain_district,
        limit=args.limit,
    )
    if args.output == "json":
        return json.dumps(rows_dict, ensure_ascii=False, indent=2)
    rows = [
        (row["id"], row["parent"], row["notused"], row["detail"]) for row in rows_dict
    ]
    return _render_output(
        headers=["id", "parent", "notused", "detail"],
        rows=rows,
        output=args.output,
        empty_message="Query plan bulunamadı.",
    )


def cmd_price_history(repo: NjoyRepository, args: argparse.Namespace) -> str:
    rows_dict = repo.price_history(limit=args.limit)
    if args.output == "json":
        return json.dumps(rows_dict, ensure_ascii=False, indent=2)
    rows = [
        (
            row["LogID"],
            row["IlanID"],
            f"{float(row['EskiFiyat']):,.0f}",
            f"{float(row['YeniFiyat']):,.0f}",
            f"{float(row['DegisimYuzdesi']):.2f}%",
            row["DegisimTarihi"],
        )
        for row in rows_dict
    ]
    return _render_output(
        headers=["LogID", "IlanID", "Eski Fiyat", "Yeni Fiyat", "Değişim", "Tarih"],
        rows=rows,
        output=args.output,
        empty_message="Fiyat geçmişi bulunamadı.",
    )


def cmd_update_price(repo: NjoyRepository, args: argparse.Namespace) -> str:
    row = repo.update_listing_price(
        ilan_id=args.ilan_id,
        new_price=args.new_price,
        note=args.note,
    )
    if args.output == "json":
        return json.dumps(row, ensure_ascii=False, indent=2)
    rows = [
        (
            row["LogID"],
            row["IlanID"],
            f"{float(row['EskiFiyat']):,.0f}",
            f"{float(row['YeniFiyat']):,.0f}",
            f"{float(row['DegisimYuzdesi']):.2f}%",
            row["Aciklama"],
        )
    ]
    return _render_output(
        headers=["LogID", "IlanID", "Eski Fiyat", "Yeni Fiyat", "Değişim", "Açıklama"],
        rows=rows,
        output=args.output,
        empty_message="Fiyat güncelleme sonucu bulunamadı.",
    )


def cmd_backup(repo: NjoyRepository, args: argparse.Namespace) -> str:
    backup_path = repo.backup_database(args.backup_path)
    rows = [(str(backup_path), "OK")]
    return _render_output(
        headers=["Backup Dosyası", "Durum"],
        rows=rows,
        output=args.output,
        empty_message="Backup oluşturulamadı.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        validate_args(args)
        repo = NjoyRepository(args.db)
        handlers = {
            "list": cmd_list,
            "search": cmd_search,
            "stats": cmd_stats,
            "benchmark": cmd_benchmark,
            "analytics": cmd_analytics,
            "explain": cmd_explain,
            "price-history": cmd_price_history,
            "update-price": cmd_update_price,
            "backup": cmd_backup,
        }
        handler = handlers.get(args.command)
        if handler is None:
            raise AppError(f"Desteklenmeyen komut: {args.command}")
        output = handler(repo, args)
        print(output)
        return 0
    except AppError as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2
    except sqlite3.DatabaseError as exc:
        print(f"Veritabanı hatası: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
