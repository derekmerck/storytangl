# tangl/persistence/storage/sqlite_storage.py
"""
SQLite-backed key-value storage for the persistence layer.

Provides a single-file persistent storage backend that implements
StorageProtocol. Works with any serializer (pickle, json, yaml, etc.)
via the binary_rw flag.

Usage:
    storage = SQLiteStorage(path="data/store.db", binary_rw=True)
    storage[uuid] = pickled_bytes
    data = storage[uuid]
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator
from uuid import UUID

from tangl.type_hints import FlatData

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kv_store (
    key   TEXT PRIMARY KEY,
    value BLOB NOT NULL
);
"""


class SQLiteStorage:
    """
    SQLite-backed key-value storage implementing StorageProtocol.
    
    Keys are UUIDs (stored as TEXT), values are FlatData (str or bytes).
    Uses WAL mode for better concurrent read performance.
    
    Args:
        path: Path to the SQLite database file. Parent directories are
              created automatically. Defaults to in-memory if ":memory:".
        binary_rw: If True, values are stored/retrieved as bytes (BLOB).
                   If False, values are stored/retrieved as text (decoded UTF-8).
    """
    
    def __init__(self, path: str | Path = ":memory:", binary_rw: bool = False):
        self.path = str(path)
        self.binary_rw = binary_rw
        self._persistent_conn: sqlite3.Connection | None = None

        # Create parent directories if needed (skip for :memory:)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        else:
            # For :memory:, we need to keep one connection alive
            # otherwise each _conn() gets a fresh empty database
            self._persistent_conn = self._make_conn()

        # Initialize schema
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    #---------

    def _make_conn(self) -> sqlite3.Connection:
        """Create a new connection with WAL mode enabled."""
        conn = sqlite3.connect(self.path, isolation_level=None)  # autocommit
        if self.path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _conn(self) -> sqlite3.Connection:
        """
        Get a connection to use.

        For :memory: databases, returns the persistent connection.
        For file databases, creates a new connection (WAL makes this safe).
        """
        if self._persistent_conn is not None:
            return self._persistent_conn
        return self._make_conn()

    def _key_str(self, key: UUID) -> str:
        """Convert UUID to string for storage."""
        return str(key)
    
    def _encode_value(self, value: FlatData) -> bytes:
        """Encode value for storage as BLOB."""
        if isinstance(value, bytes):
            return value
        return value.encode("utf-8")
    
    def _decode_value(self, blob: bytes) -> FlatData:
        """Decode BLOB to appropriate FlatData type."""
        if self.binary_rw:
            return blob
        return blob.decode("utf-8")
    
    def __setitem__(self, key: UUID, value: FlatData) -> None:
        key_str = self._key_str(key)
        blob = self._encode_value(value)
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO kv_store (key, value) VALUES (?, ?)",
                (key_str, blob),
            )
    
    def __getitem__(self, key: UUID) -> FlatData:
        key_str = self._key_str(key)
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT value FROM kv_store WHERE key = ?",
                (key_str,),
            )
            row = cur.fetchone()
            if row is None:
                raise KeyError(f"No such key {key}")
            return self._decode_value(row[0])
    
    def __delitem__(self, key: UUID) -> None:
        key_str = self._key_str(key)
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM kv_store WHERE key = ?",
                (key_str,),
            )
            if cur.rowcount == 0:
                raise KeyError(f"No such key {key}")
    
    def __contains__(self, key: object) -> bool:
        if not isinstance(key, UUID):
            return False
        key_str = self._key_str(key)
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT 1 FROM kv_store WHERE key = ?",
                (key_str,),
            )
            return cur.fetchone() is not None
    
    def __len__(self) -> int:
        with self._conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM kv_store")
            return cur.fetchone()[0]
    
    def __iter__(self) -> Iterator[UUID]:
        """Iterate over all keys in the store."""
        with self._conn() as conn:
            cur = conn.execute("SELECT key FROM kv_store")
            for (key_str,) in cur:
                yield UUID(key_str)
    
    def __bool__(self) -> bool:
        return len(self) != 0
    
    def clear(self) -> None:
        """Remove all entries from the store."""
        with self._conn() as conn:
            conn.execute("DELETE FROM kv_store")
    
    def keys(self) -> Iterator[UUID]:
        """Return an iterator over all keys."""
        return iter(self)
    
    def values(self) -> Iterator[FlatData]:
        """Return an iterator over all values."""
        with self._conn() as conn:
            cur = conn.execute("SELECT value FROM kv_store")
            for (blob,) in cur:
                yield self._decode_value(blob)
    
    def items(self) -> Iterator[tuple[UUID, FlatData]]:
        """Return an iterator over all (key, value) pairs."""
        with self._conn() as conn:
            cur = conn.execute("SELECT key, value FROM kv_store")
            for key_str, blob in cur:
                yield UUID(key_str), self._decode_value(blob)
