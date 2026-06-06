import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as core_app
import webapp


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_SCRIPT_PATH = REPO_ROOT / "njoy_veritabani.sql"


class WebCustomerFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "test.db"
        with closing(sqlite3.connect(str(self.db_path))) as conn:
            conn.executescript(SQL_SCRIPT_PATH.read_text(encoding="utf-8"))

        self._old_repo = webapp.repo
        webapp.repo = core_app.NjoyRepository(self.db_path)
        webapp.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = webapp.app.test_client()

    def tearDown(self):
        webapp.repo = self._old_repo
        self._tmpdir.cleanup()

    def test_customer_login_stays_on_homepage(self):
        user = webapp.repo.create_customer(
            "Test Kullanıcı",
            "customer@example.com",
            generate_password_hash("pass123"),
        )

        response = self.client.post(
            "/login",
            data={"email": "customer@example.com", "password": "pass123"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], user["KullaniciID"])

        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        home_html = home.get_data(as_text=True)
        self.assertIn("Mesajlar", home_html)
        self.assertIn("Bildirimler", home_html)
        self.assertIn("/static/app.js?v=", home_html)

    def test_account_route_redirects_to_homepage(self):
        user = webapp.repo.create_customer(
            "Yönlendirme Test",
            "redirect@example.com",
            generate_password_hash("pass123"),
        )
        with self.client.session_transaction() as session:
            session["user_id"] = user["KullaniciID"]

        response = self.client.get("/account", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def test_admin_delete_listing_route(self):
        with self.client.session_transaction() as session:
            session["admin_email"] = webapp.ADMIN_EMAIL

        response = self.client.delete("/api/admin/listings/1000", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["Aktif"], 0)
        listing_ids = [item["IlanID"] for item in webapp.repo.admin_listings(limit=200)]
        self.assertNotIn(1000, listing_ids)

    def test_admin_page_exposes_delete_listing_form(self):
        with self.client.session_transaction() as session:
            session["admin_email"] = webapp.ADMIN_EMAIL

        response = self.client.get("/admin")

        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="delete-listing-form"', html)
        self.assertIn('id="delete-ilan-select"', html)
        self.assertIn("/static/admin.js?v=", html)


if __name__ == "__main__":
    unittest.main()
