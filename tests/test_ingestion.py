import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import ingestion

class IngestionTests(unittest.TestCase):
    def test_deduplication(self):
        item = {"platform":"reddit","external_id":"t3_test","url":"https://www.reddit.com/r/test/comments/test",
                "text":"Example problem", "context":"test"}
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            self.assertEqual(ingestion.store([item,item], db), 1)
            self.assertEqual(ingestion.store([item], db), 0)
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 1)

    @patch("ingestion.request_json")
    def test_youtube_normalization(self, request):
        request.return_value = {"items":[{"id":"Ugx123","snippet":{"topLevelComment":{"snippet":{
            "textDisplay":"I cannot export my notes", "publishedAt":"2026-01-01T00:00:00Z"}}}}]}
        items = ingestion.youtube_comments("abcdefghijk", "fake-key")
        self.assertEqual(items[0]["platform"], "youtube")
        self.assertEqual(items[0]["text"], "I cannot export my notes")

    @patch("ingestion.request_json")
    def test_reddit_normalization(self, request):
        request.return_value = {"data":{"children":[{"data":{"name":"t3_123","title":"Need better search",
            "selftext":"Current apps fail","permalink":"/r/test/comments/123","created_utc":123}}],"after":None}}
        items = ingestion.reddit_posts("test", "fake-token")
        self.assertEqual(items[0]["external_id"], "t3_123")
        self.assertIn("Current apps fail", items[0]["text"])

    def test_missing_credentials(self):
        with self.assertRaises(ValueError):
            ingestion.youtube_comments("abcdefghijk", None)
        with self.assertRaises(ValueError):
            ingestion.reddit_posts("test", None)

if __name__ == "__main__":
    unittest.main()
