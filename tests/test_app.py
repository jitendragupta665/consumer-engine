"""Smoke tests using Python's standard library."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app

class DatabaseTests(unittest.TestCase):
    def test_empty_database(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(app, "DB", Path(directory) / "test.sqlite3"):
                app.initialize()
                self.assertEqual(app.findings(), [])

    def test_score_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(app, "DB", Path(directory) / "test.sqlite3"):
                app.initialize()
                import sqlite3
                with sqlite3.connect(app.DB) as db:
                    for title, score in [("low", 1), ("high", 5)]:
                        db.execute("INSERT INTO problems (title, reach, severity, feasibility, retention, payment) VALUES (?,?,?,?,?,?)", (title,)*1 + (score,)*5)
                result = app.findings()
                self.assertEqual([r["title"] for r in result], ["high", "low"])
                self.assertEqual(result[0]["score"], 100)

if __name__ == "__main__":
    unittest.main()
