"""Append-only SQLite memory. Model outputs are snapshots, never editable fields."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import local
from uuid import uuid4


class MemoryStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._local = local()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, request_id TEXT UNIQUE, customer_id TEXT NOT NULL,
                product TEXT NOT NULL, kind TEXT NOT NULL, timestamp TEXT NOT NULL,
                request TEXT NOT NULL, payload TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS events_customer ON events(customer_id, timestamp)")

    @contextmanager
    def connect(self):
        active = getattr(self._local, "connection", None)
        if active is not None:
            yield active
            return
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._local.connection = db
            try:
                yield
            finally:
                self._local.connection = None

    def replay(self, customer_id, product, kind, request):
        if not request.get("request_id"):
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM events WHERE request_id=?", (request["request_id"],)).fetchone()
            if row is None:
                return None
            expected = json.dumps(request, sort_keys=True, separators=(",", ":"))
            if (row["request"], row["customer_id"], row["product"], row["kind"]) != (expected, customer_id, product, kind):
                raise ValueError("Request ID already used for a different action")
            return json.loads(row["payload"])

    def append(self, customer_id, product, kind, request, payload):
        request_json = json.dumps(request, sort_keys=True, separators=(",", ":"))
        request_id = request.get("request_id")
        with self.connect() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            if request_id:
                row = db.execute("SELECT * FROM events WHERE request_id=?", (request_id,)).fetchone()
                if row:
                    if (row["request"], row["customer_id"], row["product"], row["kind"]) != (
                        request_json, customer_id, product, kind,
                    ):
                        raise ValueError("Request ID already used for a different action")
                    return json.loads(row["payload"])
            event = {
                "id": str(uuid4()), "customer_id": customer_id, "product": product,
                "kind": kind, "timestamp": datetime.now(timezone.utc).isoformat(), **payload,
            }
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", (
                event["id"], request_id, customer_id, product, kind, event["timestamp"],
                request_json, json.dumps(event, sort_keys=True),
            ))
            return event

    def history(self, customer_id, product=None):
        with self.connect() as db:
            sql = "SELECT payload FROM events WHERE customer_id=?"
            args = [customer_id]
            if product is not None:
                sql += " AND product=?"
                args.append(product)
            return [json.loads(row[0]) for row in db.execute(sql + " ORDER BY rowid", args)]

    def get_event(self, event_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM events WHERE id=?", (event_id,)).fetchone()
            return json.loads(row[0]) if row else None
