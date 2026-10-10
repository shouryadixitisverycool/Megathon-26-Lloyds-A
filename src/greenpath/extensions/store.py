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
        self._recommendations = {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY, request_id TEXT UNIQUE, customer_id TEXT NOT NULL,
                product TEXT NOT NULL, kind TEXT NOT NULL, timestamp TEXT NOT NULL,
                request TEXT NOT NULL, payload TEXT NOT NULL)""")
            db.execute("CREATE INDEX IF NOT EXISTS events_customer ON events(customer_id, timestamp)")
            db.execute("""CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, product TEXT NOT NULL,
                timestamp TEXT NOT NULL, payload TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS explanations (
                decision_id TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY (decision_id, digest))""")

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
        if getattr(self._local, "connection", None) is not None:
            yield
            return
        pending = {}
        try:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                self._local.connection = db
                self._local.recommendations = pending
                yield
            # Entries are known durable only after the outer transaction commits.
            self._recommendations.update(pending)
            while len(self._recommendations) > 256:
                self._recommendations.pop(next(iter(self._recommendations)))
        finally:
            self._local.connection = None
            self._local.recommendations = None

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

    def save_recommendation(self, recommendation):
        from greenpath.recommendation.service import decision_evidence, decision_identity
        if recommendation.decision_id is None:
            recommendation = recommendation.model_copy(update={"decision_id": decision_identity(recommendation)})
        payload = recommendation.model_dump(mode="json")
        evidence = decision_evidence(payload)
        pending = getattr(self._local, "recommendations", None)
        cached = (pending or {}).get(payload["decision_id"]) or self._recommendations.get(payload["decision_id"])
        if cached is not None:
            if cached[0] != evidence:
                raise ValueError("Decision ID already belongs to different immutable evidence")
            return recommendation.__class__.model_validate(cached[1].model_dump(mode="python"))
        with self.connect() as db:
            inserted = db.execute("INSERT OR IGNORE INTO decisions VALUES (?,?,?,?,?)", (
                payload["decision_id"], payload["customer_id"], payload["product"],
                payload["timestamp"], json.dumps(payload, sort_keys=True),
            )).rowcount
            if inserted:
                # The exact serialized payload was just inserted; detach cache ownership.
                result = recommendation.__class__.model_validate(payload)
            else:
                stored = db.execute("SELECT payload FROM decisions WHERE id=?", (payload["decision_id"],)).fetchone()
                if decision_evidence(json.loads(stored[0])) != evidence:
                    raise ValueError("Decision ID already belongs to different immutable evidence")
                result = recommendation.__class__.model_validate_json(stored[0])
        target = pending if pending is not None else self._recommendations
        target[payload["decision_id"]] = (evidence, result)
        # Provenance can include large source snapshots; do not retain the full cohort.
        if len(target) > 256:
            target.pop(next(iter(target)))
        return recommendation.__class__.model_validate(result.model_dump(mode="python"))

    def get_recommendation(self, decision_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM decisions WHERE id=?", (decision_id,)).fetchone()
            if row is None:
                return None
            result = json.loads(row[0])
            result["explanations"] = [json.loads(r[0]) for r in db.execute(
                "SELECT payload FROM explanations WHERE decision_id=? ORDER BY rowid", (decision_id,))]
            result["unified_provenance"] = {"decision": result.get("provenance", {}),
                "explanation_runs": [{"prompt_version": e["prompt_version"], "llm_version": e["llm_version"],
                                      "timestamp": e["timestamp"], "source": e["explanation"]["source"],
                                      "validation_passed": e["explanation"]["validation_passed"],
                                      "fallback_reason": e["explanation"].get("fallback_reason")}
                                     for e in result["explanations"]]}
            return result

    def recommendation_history(self, customer_id, product=None):
        with self.connect() as db:
            rows = db.execute("SELECT payload FROM decisions WHERE customer_id=? ORDER BY rowid", (customer_id,))
            return [p for row in rows if (p := json.loads(row[0])) and (product is None or p["product"] == product)]

    def save_explanation(self, decision_id, explanation, prompt_version=None):
        import hashlib
        payload = {"explanation": explanation.model_dump(mode="json"), "prompt_version": prompt_version,
                   "llm_version": explanation.provider_version, "timestamp": datetime.now(timezone.utc).isoformat()}
        digest = hashlib.sha256(json.dumps(payload["explanation"], sort_keys=True).encode() + str(prompt_version).encode()).hexdigest()
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO explanations VALUES (?,?,?)", (decision_id, digest, json.dumps(payload, sort_keys=True)))

    def source_updates(self, customer_id=None):
        with self.connect() as db:
            sql = "SELECT payload FROM events WHERE kind='source_update'"
            args = ()
            if customer_id is not None:
                sql += " AND customer_id=?"
                args = (customer_id,)
            return [json.loads(row[0]) for row in db.execute(sql + " ORDER BY rowid", args)]

    def active_campaigns(self):
        with self.connect() as db:
            events = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events WHERE kind IN ('campaign', 'campaign_closed') ORDER BY rowid")]
        closed = {e.get("campaign_id") for e in events if e["kind"] == "campaign_closed"}
        return [e for e in events if e["kind"] == "campaign" and e["id"] not in closed and e.get("result", {}).get("executed")]

    def remaining_campaign_capacity(self, channel, capacity, max_active_campaigns=None):
        active = self.active_campaigns()
        if max_active_campaigns is not None and len(active) >= max_active_campaigns:
            return 0
        used = sum(e.get("result", {}).get("selected_count", 0) for e in active
                   if json.loads(self._event_request(e["id"])).get("channel") == channel)
        return max(0, capacity - used)

    def _event_request(self, event_id):
        with self.connect() as db:
            return db.execute("SELECT request FROM events WHERE id=?", (event_id,)).fetchone()[0]
