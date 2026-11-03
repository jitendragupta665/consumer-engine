"""Local-first evidence registry. Run: python app.py (Python 3.9+)."""
import csv
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

DB = Path(__file__).with_name("research.sqlite3")
FIELDS = ("sector", "category", "subcategory", "title", "description", "country", "source")
RATINGS = ("reach", "severity", "feasibility", "retention", "payment")
SECTORS = ("Education", "Health", "Finance", "Shopping", "Productivity", "Travel",
           "Food", "Home", "Entertainment", "Communication", "Accessibility",
           "Career", "Security", "Environment", "Other")

def initialize():
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY, sector TEXT, category TEXT, subcategory TEXT,
            title TEXT, description TEXT, country TEXT, source TEXT,
            reach INTEGER, severity INTEGER, feasibility INTEGER,
            retention INTEGER, payment INTEGER)""")

def findings():
    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        records = [dict(row) for row in db.execute("SELECT * FROM problems")]
    for record in records:
        record["score"] = sum(record[key] for key in RATINGS) * 4
    return sorted(records, key=lambda record: record["score"], reverse=True)

class Handler(BaseHTTPRequestHandler):
    def send(self, payload, kind="application/json", status=200):
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self.send(Path(__file__).with_name("index.html").read_text(), "text/html")
        if path == "/api/problems":
            return self.send(findings())
        if path == "/api/sectors":
            return self.send(list(SECTORS))
        self.send({"error": "not found"}, status=404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/problems":
            return self.send({"error": "not found"}, status=404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 65536:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(length))
            if data.get("sector") not in SECTORS or not data.get("title"):
                raise ValueError("Sector and title required")
            if not str(data.get("source", "")).startswith(("https://", "http://")):
                raise ValueError("Evidence URL required")
            values = [int(data.get(key, 3)) for key in RATINGS]
            if any(value < 1 or value > 5 for value in values):
                raise ValueError("Ratings must be 1–5")
            with sqlite3.connect(DB) as db:
                db.execute(
                    "INSERT INTO problems (" + ",".join(FIELDS + RATINGS) +
                    ") VALUES (" + ",".join(["?"] * 12) + ")",
                    [str(data.get(key, "")) for key in FIELDS] + values)
            return self.send({"saved": True}, status=201)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return self.send({"error": str(exc)}, status=400)

if __name__ == "__main__":
    initialize()
    print("Open http://127.0.0.1:8765")
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
