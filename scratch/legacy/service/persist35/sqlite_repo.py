# tangl/persist/sqlite_repo.py
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from .ser import Serializer, PickleSerializer
from .repo import Repository

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS events (
  graph_id TEXT NOT NULL,
  version  INTEGER NOT NULL,
  patch    BLOB NOT NULL,
  idem_key TEXT,
  PRIMARY KEY (graph_id, version)
);
CREATE TABLE IF NOT EXISTS snapshots (
  graph_id TEXT NOT NULL,
  version  INTEGER NOT NULL,
  blob     BLOB NOT NULL,
  PRIMARY KEY (graph_id, version)
);
"""

@dataclass
class SQLiteRepo(Repository):
    path: str
    serializer: Serializer = PickleSerializer()

    def __post_init__(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as cx:
            cx.executescript(_SCHEMA)

    def _conn(self):
        # new connection per call; WAL makes this safe
        cx = sqlite3.connect(self.path, isolation_level=None)  # autocommit
        cx.execute("PRAGMA journal_mode=WAL;")
        return cx

    def load_latest_snapshot(self, graph_id: UUID) -> Tuple[int, bytes] | None:
        with self._conn() as cx:
            cur = cx.execute(
                "SELECT version, blob FROM snapshots WHERE graph_id=? ORDER BY version DESC LIMIT 1",
                (str(graph_id),),
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None

    def append_patch(self, graph_id: UUID, expected_version: int, patch_blob: bytes, idem_key: str | None) -> int:
        gid = str(graph_id)
        with self._conn() as cx:
            cur = cx.execute("SELECT COALESCE(MAX(version), 0) FROM events WHERE graph_id=?", (gid,))
            current = cur.fetchone()[0]
            if current != expected_version:
                raise RuntimeError(f"version conflict: expected {expected_version}, got {current}")
            new_version = expected_version + 1
            cx.execute(
                "INSERT INTO events (graph_id, version, patch, idem_key) VALUES (?,?,?,?)",
                (gid, new_version, patch_blob, idem_key),
            )
            return new_version

    def save_snapshot(self, graph_id: UUID, version: int, snap_blob: bytes) -> None:
        with self._conn() as cx:
            cx.execute(
                "INSERT OR REPLACE INTO snapshots (graph_id, version, blob) VALUES (?,?,?)",
                (str(graph_id), version, snap_blob),
            )