"""Durable checkpoints backed by an append-only, hash-linked SQLite event journal."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any

from agency_garden.contracts import JSONObject
from agency_garden.errors import IntegrityError
from agency_garden.serialization import canonical, digest


class RunStore:
    """One writer per run; the runtime holds an OS-backed lock for its full lifetime."""

    def __init__(self, path: str | Path, *, read_only: bool = False) -> None:
        self.path = Path(path)
        if read_only:
            self.connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.executescript("""
                CREATE TABLE IF NOT EXISTS objects (
                    kind TEXT NOT NULL, key TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY (kind, key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY, payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL, hash TEXT NOT NULL
                );
            """)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self) -> "RunStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.connection.close()

    def get(self, kind: str, key: str) -> JSONObject | None:
        row = self.connection.execute(
            "SELECT body FROM objects WHERE kind=? AND key=?", (kind, key)
        ).fetchone()
        return json.loads(row["body"]) if row else None

    def items(self, kind: str) -> dict[str, JSONObject]:
        return {
            row["key"]: json.loads(row["body"])
            for row in self.connection.execute(
                "SELECT key,body FROM objects WHERE kind=? ORDER BY key", (kind,)
            )
        }

    def put(self, kind: str, key: str, value: JSONObject) -> None:
        body = canonical(value)
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            last = self.connection.execute(
                "SELECT seq,hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq, previous = (last["seq"] + 1, last["hash"]) if last else (1, "0" * 64)
            payload = {
                "kind": kind,
                "key": key,
                "value": value,
                "recorded_at": datetime.now(UTC).isoformat(),
            }
            fingerprint = digest({"seq": seq, "payload": payload, "previous_hash": previous})
            self.connection.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (seq, canonical(payload), previous, fingerprint),
            )
            self.connection.execute(
                "INSERT INTO objects VALUES (?,?,?) ON CONFLICT(kind,key) "
                "DO UPDATE SET body=excluded.body",
                (kind, key, body),
            )
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def events(self) -> list[JSONObject]:
        return [
            {
                "seq": row["seq"],
                "payload": json.loads(row["payload"]),
                "previous_hash": row["previous_hash"],
                "hash": row["hash"],
            }
            for row in self.connection.execute("SELECT * FROM events ORDER BY seq")
        ]

    def attempts(self) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM events WHERE json_extract(payload,'$.kind')='decision' "
                "AND json_extract(payload,'$.value.status')='started'"
            ).fetchone()[0]
        )

    def verify(self) -> JSONObject:
        """Check event continuity and every materialized object against the journal.

        This detects accidental modification; it is not a signature or protection
        against someone who can replace the entire database and all its hashes.
        """
        previous = "0" * 64
        replay: dict[tuple[str, str], Any] = {}
        records = self.events()
        for expected, record in enumerate(records, 1):
            payload = record["payload"]
            if record["seq"] != expected or record["previous_hash"] != previous:
                raise IntegrityError(f"Event continuity failed at {expected}")
            calculated = digest({"seq": expected, "payload": payload, "previous_hash": previous})
            if calculated != record["hash"]:
                raise IntegrityError(f"Event hash failed at {expected}")
            replay[(payload["kind"], payload["key"])] = payload["value"]
            previous = calculated
        actual = {
            (row["kind"], row["key"]): json.loads(row["body"])
            for row in self.connection.execute("SELECT * FROM objects")
        }
        if canonical(sorted((k, v) for k, v in replay.items())) != canonical(
            sorted((k, v) for k, v in actual.items())
        ):
            raise IntegrityError("Materialized records differ from their event history")
        manifest = self.get("manifest", "run")
        if manifest and digest(manifest["specification"]) != manifest["fingerprint"]:
            raise IntegrityError("Run manifest fingerprint is inconsistent")
        return {"valid": True, "events": len(records), "objects": len(actual), "head": previous}
