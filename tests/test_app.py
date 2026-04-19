import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import app


REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_SCRIPT_PATH = REPO_ROOT / "njoy_veritabani.sql"


class AppCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._tmpdir.name) / "test.db"
        with sqlite3.connect(str(cls.db_path)) as conn:
            script = SQL_SCRIPT_PATH.read_text(encoding="utf-8")
            conn.executescript(script)

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

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


if __name__ == "__main__":
    unittest.main()
