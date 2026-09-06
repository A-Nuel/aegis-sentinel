"""Lightweight SQLite for watched targets + alerts (not the private audit DB)."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "sentinel.db"


class Store:
    def __init__(self, path: Path = DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS watched (
                    address TEXT NOT NULL,
                    chain TEXT NOT NULL,
                    label TEXT DEFAULT '',
                    PRIMARY KEY (address, chain)
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    ts REAL,
                    payload TEXT
                );
                """
            )

    def add_watch(self, address: str, chain: str, label: str = "") -> dict[str, str]:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO watched(address, chain, label) VALUES (?,?,?)",
                (address, chain, label),
            )
        return {"address": address, "chain": chain, "label": label}

    def list_watched(self) -> list[dict[str, str]]:
        with self._conn() as c:
            rows = c.execute("SELECT address, chain, label FROM watched").fetchall()
        return [dict(r) for r in rows]

    def save_alert(self, alert: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO alerts(id, ts, payload) VALUES (?,?,?)",
                (alert.get("id"), alert.get("timestamp", time.time()), json.dumps(alert)),
            )

    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT payload FROM alerts ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r["payload"]) for r in rows]


store = Store()
