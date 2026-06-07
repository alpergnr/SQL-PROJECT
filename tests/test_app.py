import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path

import app


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_SCRIPT_PATH = REPO_ROOT / "njoy_veritabani.sql"


class AppCLITests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "test.db"
        with closing(sqlite3.connect(str(self.db_path))) as conn:
            script = SQL_SCRIPT_PATH.read_text(encoding="utf-8")
            conn.executescript(script)

    def tearDown(self):
        self._tmpdir.cleanup()

    def run_main(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = app.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_list_json_output(self):
        code, out, err = self.run_main(
            ["list", "--db", str(self.db_path), "--limit", "2", "--output", "json"]
        )
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertEqual(len(payload), 2)
        self.assertIn("IlanID", payload[0])

    def test_search_empty_state(self):
        code, out, err = self.run_main(
            [
                "search",
                "--db",
                str(self.db_path),
                "--district",
                "OlmayanIlce",
                "--output",
                "table",
            ]
        )
        self.assertEqual(code, 0, msg=err)
        self.assertIn("Filtrelere uygun kayıt bulunamadı.", out)

    def test_limit_upper_bound_validation(self):
        code, out, err = self.run_main(
            ["list", "--db", str(self.db_path), "--limit", "999"]
        )
        self.assertEqual(code, 2)
        self.assertIn("--limit en fazla", err)
        self.assertEqual(out, "")

    def test_limit_lower_bound_validation(self):
        code, out, err = self.run_main(["list", "--db", str(self.db_path), "--limit", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--limit pozitif", err)
        self.assertEqual(out, "")

    def test_benchmark_runs(self):
        code, out, err = self.run_main(
            [
                "benchmark",
                "--db",
                str(self.db_path),
                "--output",
                "json",
                "--bench-district",
                "Beyoğlu",
            ]
        )
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        keys = {row["Sorgu"] for row in payload}
        self.assertIn("list_ms", keys)
        self.assertIn("search_ms", keys)
        self.assertIn("stats_ms", keys)

    def test_benchmark_max_price_validation(self):
        code, out, err = self.run_main(
            [
                "benchmark",
                "--db",
                str(self.db_path),
                "--bench-max-price",
                "-1",
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--bench-max-price negatif olamaz.", err)
        self.assertEqual(out, "")

    def test_analytics_json_output(self):
        code, out, err = self.run_main(
            ["analytics", "--db", str(self.db_path), "--limit", "3", "--output", "json"]
        )
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertIn("region_analysis", payload)
        self.assertIn("listing_ranking", payload)
        self.assertGreaterEqual(len(payload["room_pivot"]), 1)

    def test_explain_uses_composite_index(self):
        code, out, err = self.run_main(
            ["explain", "--db", str(self.db_path), "--output", "json"]
        )
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        details = " ".join(row["detail"] for row in payload)
        self.assertIn("idx_emlaklar_ilce_fiyat", details)

    def test_update_price_creates_audit_log(self):
        code, out, err = self.run_main(
            [
                "update-price",
                "--db",
                str(self.db_path),
                "1000",
                "41000",
                "--note",
                "Birim test fiyat güncellemesi",
                "--output",
                "json",
            ]
        )
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertEqual(payload["IlanID"], 1000)
        self.assertEqual(payload["EskiFiyat"], 40000)
        self.assertEqual(payload["YeniFiyat"], 41000)
        self.assertEqual(payload["Aciklama"], "Birim test fiyat güncellemesi")

        code, out, err = self.run_main(
            ["price-history", "--db", str(self.db_path), "--output", "json"]
        )
        self.assertEqual(code, 0, msg=err)
        history = json.loads(out)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["IlanID"], 1000)

        repo = app.NjoyRepository(self.db_path)
        listing_history = repo.listing_history(limit=5)
        self.assertEqual(listing_history[0]["IslemTipi"], "FIYAT_GUNCELLEME")
        self.assertEqual(listing_history[0]["AlanAdi"], "Fiyat")

    def test_admin_create_listing_writes_history(self):
        repo = app.NjoyRepository(self.db_path)
        created = repo.create_listing(
            {
                "danisman_id": 1,
                "baslik": "TEST ADMIN PANEL İLANI",
                "fiyat": 25000,
                "il": "İstanbul",
                "ilce": "Kadıköy",
                "mahalle": "Moda Mh.",
                "emlak_tipi": "Kiralık Daire",
                "brut_m2": 70,
                "net_m2": 55,
                "oda_sayisi": "1+1",
            },
            user="admin@njoyemlak.com",
        )
        self.assertGreater(created["IlanID"], 1009)
        self.assertEqual(created["İlce"], "Kadıköy")

        history = repo.listing_history(limit=1)
        self.assertEqual(history[0]["IlanID"], created["IlanID"])
        self.assertEqual(history[0]["IslemTipi"], "EKLEME")

    def test_admin_create_listing_writes_selected_features(self):
        repo = app.NjoyRepository(self.db_path)
        created = repo.create_listing(
            {
                "danisman_id": 1,
                "baslik": "TEST ÖZELLİKLİ İLAN",
                "fiyat": 31500,
                "il": "İstanbul",
                "ilce": "Kadıköy",
                "mahalle": "Caferağa Mh.",
                "emlak_tipi": "Kiralık Daire",
                "brut_m2": 80,
                "net_m2": 62,
                "oda_sayisi": "2+1",
                "feature_ids": [1, 34, 78],
            },
            user="admin@njoyemlak.com",
        )
        self.assertEqual(created["FeatureIDs"], [1, 34, 78])
        features = repo.listing_features(created["IlanID"])
        flat_features = {feature for items in features.values() for feature in items}
        self.assertIn("ADSL", flat_features)
        self.assertIn("Klima", flat_features)
        self.assertIn("Doğu", flat_features)

    def test_admin_update_listing_writes_field_history(self):
        repo = app.NjoyRepository(self.db_path)
        updated = repo.update_listing(
            1000,
            {"mahalle": "Yeni Test Mahallesi"},
            user="admin@njoyemlak.com",
            note="Birim test ilan güncellemesi",
        )
        self.assertEqual(updated["Mahalle"], "Yeni Test Mahallesi")

        history = repo.listing_history(limit=1)
        self.assertEqual(history[0]["IlanID"], 1000)
        self.assertEqual(history[0]["IslemTipi"], "GUNCELLEME")
        self.assertEqual(history[0]["AlanAdi"], "Mahalle")
        self.assertEqual(history[0]["YeniDeger"], "Yeni Test Mahallesi")

    def test_admin_update_listing_can_replace_features_only(self):
        repo = app.NjoyRepository(self.db_path)
        updated = repo.update_listing(
            1003,
            {"feature_ids": [1, 78]},
            user="admin@njoyemlak.com",
            note="Özellikler test için güncellendi",
        )
        self.assertEqual(updated["FeatureIDs"], [1, 78])
        history = repo.listing_history(limit=1)
        self.assertEqual(history[0]["IlanID"], 1003)
        self.assertEqual(history[0]["IslemTipi"], "OZELLIK_GUNCELLEME")
        self.assertEqual(history[0]["AlanAdi"], "Özellikler")

    def test_customer_can_save_listing_and_ask_question(self):
        repo = app.NjoyRepository(self.db_path)
        user = repo.create_customer("Test Kullanıcı", "test@example.com", "hash")
        repo.save_listing(user["KullaniciID"], 1000)
        self.assertIn(1000, repo.saved_listing_ids(user["KullaniciID"]))

        question = repo.ask_question(user["KullaniciID"], 1000, "Depozito bilgisi nedir?")
        self.assertEqual(question["Durum"], "Açık")

        answered = repo.answer_question(
            question["SoruID"],
            "Depozito bilgisi için danışmanla görüşebilirsiniz.",
            "admin@njoyemlak.com",
        )
        self.assertEqual(answered["Durum"], "Cevaplandı")
        notifications = repo.notifications(user["KullaniciID"])
        self.assertTrue(any(n["Tip"] == "MESAJ" for n in notifications))

    def test_saved_listing_price_update_creates_customer_notification(self):
        repo = app.NjoyRepository(self.db_path)
        user = repo.create_customer("Fiyat Takip", "price@example.com", "hash")
        repo.save_listing(user["KullaniciID"], 1000)
        repo.update_listing_price(
            1000,
            41500,
            note="Bildirim testi",
            user="admin@njoyemlak.com",
        )
        notifications = repo.notifications(user["KullaniciID"])
        changes = [n for n in notifications if n["Tip"] == "ILAN_DEGISIKLIK"]
        self.assertEqual(len(changes), 1)
        self.assertIn("Fiyat", changes[0]["Mesaj"])

    def test_admin_delete_listing_soft_deletes_and_notifies_customer(self):
        repo = app.NjoyRepository(self.db_path)
        user = repo.create_customer("Silme Takip", "delete@example.com", "hash")
        repo.save_listing(user["KullaniciID"], 1000)

        deleted = repo.delete_listing(1000, user="admin@njoyemlak.com")

        self.assertEqual(deleted["IlanID"], 1000)
        self.assertEqual(deleted["Aktif"], 0)
        self.assertNotIn(1000, repo.saved_listing_ids(user["KullaniciID"]))
        self.assertTrue(all(item["IlanID"] != 1000 for item in repo.admin_listings()))
        self.assertTrue(
            all(item.ilan_id != 1000 for item in repo.list_listings(limit=50, sort_by="ilanid_asc"))
        )
        with self.assertRaises(app.AppError):
            repo.get_admin_listing(1000)

        history = repo.listing_history(limit=1)
        self.assertEqual(history[0]["IlanID"], 1000)
        self.assertEqual(history[0]["IslemTipi"], "SILME")

        notifications = repo.notifications(user["KullaniciID"])
        self.assertTrue(any(n["Tip"] == "ILAN_SILME" for n in notifications))

    def test_backup_creates_database_file(self):
        backup_path = Path(self._tmpdir.name) / "backup.db"
        code, out, err = self.run_main(
            [
                "backup",
                "--db",
                str(self.db_path),
                "--backup-path",
                str(backup_path),
                "--output",
                "json",
            ]
        )
        self.assertEqual(code, 0, msg=err)
        self.assertTrue(backup_path.exists())
        with closing(sqlite3.connect(str(backup_path))) as conn:
            count = conn.execute("SELECT COUNT(*) FROM Emlaklar").fetchone()[0]
        self.assertEqual(count, 10)


if __name__ == "__main__":
    unittest.main()
