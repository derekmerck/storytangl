from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import ExtractedArtifact, ExtractedSymbol, TopicDefinition


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    layer TEXT NOT NULL,
    short_description TEXT NOT NULL,
    related_topic_ids_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topic_aliases (
    topic_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    PRIMARY KEY (topic_id, alias),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    qualified_name TEXT NOT NULL UNIQUE,
    symbol_kind TEXT NOT NULL,
    module_name TEXT NOT NULL,
    object_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    line INTEGER,
    signature TEXT,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_key TEXT NOT NULL UNIQUE,
    source_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    facet TEXT NOT NULL,
    relation TEXT NOT NULL,
    line INTEGER,
    anchor TEXT,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    qualified_name TEXT,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_topics (
    artifact_id INTEGER NOT NULL,
    topic_id TEXT NOT NULL,
    facet TEXT NOT NULL,
    relation TEXT NOT NULL,
    evidence_source TEXT NOT NULL,
    weight REAL NOT NULL,
    PRIMARY KEY (artifact_id, topic_id, facet, relation, evidence_source),
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifact_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_artifact_id INTEGER NOT NULL,
    target_artifact_id INTEGER NOT NULL,
    link_kind TEXT NOT NULL,
    FOREIGN KEY (source_artifact_id) REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    FOREIGN KEY (target_artifact_id) REFERENCES artifacts(artifact_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS build_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL
);
"""


class DevRefDatabase:
    """SQLite storage wrapper for the developer reference index."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def table_exists(self, table_name: str) -> bool:
        """Return whether one table exists without mutating an absent database."""

        if not self.path.exists():
            return False
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table_name,),
            ).fetchone()
        return row is not None

    def has_schema(self) -> bool:
        """Return whether the devref schema exists on disk."""

        required_tables = (
            "topics",
            "topic_aliases",
            "artifacts",
            "symbols",
            "artifact_topics",
            "artifact_links",
            "build_meta",
        )
        return all(self.table_exists(table_name) for table_name in required_tables)

    def is_built(self) -> bool:
        """Return whether the database contains a completed devref build."""

        if not self.has_schema():
            return False
        meta = self.get_meta()
        return bool(meta.get("builder_version"))

    def clear_dynamic_tables(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM artifact_links")
            conn.execute("DELETE FROM artifact_topics")
            conn.execute("DELETE FROM artifacts")
            conn.execute("DELETE FROM symbols")
            conn.execute("DELETE FROM build_meta")
            conn.execute("DELETE FROM topic_aliases")
            conn.execute("DELETE FROM topics")

    def delete_source_paths(self, source_paths: Iterable[str]) -> None:
        values = tuple(source_paths)
        if not values:
            return
        placeholders = ", ".join("?" for _ in values)
        with self.connect() as conn:
            conn.execute(
                f"DELETE FROM artifacts WHERE source_path IN ({placeholders})",
                values,
            )
            conn.execute(
                f"DELETE FROM symbols WHERE source_path IN ({placeholders})",
                values,
            )

    def upsert_topics(self, topics: list[TopicDefinition], *, normalize_alias) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM topic_aliases")
            conn.execute("DELETE FROM topics")
            conn.executemany(
                """
                INSERT INTO topics (
                    topic_id,
                    display_name,
                    layer,
                    short_description,
                    related_topic_ids_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        topic.topic_id,
                        topic.display_name,
                        topic.layer,
                        topic.short_description,
                        json.dumps(topic.related_topic_ids),
                    )
                    for topic in topics
                ],
            )
            alias_rows: list[tuple[str, str, str]] = []
            for topic in topics:
                for alias in {topic.topic_id, topic.display_name, *topic.aliases}:
                    alias_rows.append((topic.topic_id, alias, normalize_alias(alias)))
            conn.executemany(
                """
                INSERT INTO topic_aliases (topic_id, alias, alias_norm)
                VALUES (?, ?, ?)
                """,
                alias_rows,
            )

    def insert_symbols(self, symbols: list[ExtractedSymbol]) -> None:
        if not symbols:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO symbols (
                    qualified_name,
                    symbol_kind,
                    module_name,
                    object_name,
                    source_path,
                    source_hash,
                    line,
                    signature,
                    summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(qualified_name) DO UPDATE SET
                    symbol_kind=excluded.symbol_kind,
                    module_name=excluded.module_name,
                    object_name=excluded.object_name,
                    source_path=excluded.source_path,
                    source_hash=excluded.source_hash,
                    line=excluded.line,
                    signature=excluded.signature,
                    summary=excluded.summary
                """,
                [
                    (
                        symbol.qualified_name,
                        symbol.symbol_kind,
                        symbol.module_name,
                        symbol.object_name,
                        symbol.source_path,
                        symbol.source_hash,
                        symbol.line,
                        symbol.signature,
                        symbol.summary,
                    )
                    for symbol in symbols
                ],
            )

    def insert_artifacts(self, artifacts: list[ExtractedArtifact]) -> None:
        if not artifacts:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO artifacts (
                    artifact_key,
                    source_path,
                    source_hash,
                    title,
                    kind,
                    facet,
                    relation,
                    line,
                    anchor,
                    summary,
                    content,
                    qualified_name,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_key) DO UPDATE SET
                    source_path=excluded.source_path,
                    source_hash=excluded.source_hash,
                    title=excluded.title,
                    kind=excluded.kind,
                    facet=excluded.facet,
                    relation=excluded.relation,
                    line=excluded.line,
                    anchor=excluded.anchor,
                    summary=excluded.summary,
                    content=excluded.content,
                    qualified_name=excluded.qualified_name,
                    metadata_json=excluded.metadata_json
                """,
                [
                    (
                        artifact.artifact_key,
                        artifact.source_path,
                        artifact.source_hash,
                        artifact.title,
                        artifact.kind,
                        artifact.facet,
                        artifact.relation,
                        artifact.line,
                        artifact.anchor,
                        artifact.summary,
                        artifact.content,
                        artifact.qualified_name,
                        json.dumps(artifact.metadata, sort_keys=True),
                    )
                    for artifact in artifacts
                ],
            )

    def replace_artifact_topics(self, rows: Iterable[tuple[int, str, str, str, str, float]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM artifact_topics")
            conn.executemany(
                """
                INSERT INTO artifact_topics (
                    artifact_id,
                    topic_id,
                    facet,
                    relation,
                    evidence_source,
                    weight
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                list(rows),
            )

    def replace_artifact_links(self, rows: Iterable[tuple[int, int, str]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM artifact_links")
            conn.executemany(
                """
                INSERT INTO artifact_links (
                    source_artifact_id,
                    target_artifact_id,
                    link_kind
                ) VALUES (?, ?, ?)
                """,
                list(rows),
            )

    def set_meta(self, **values: str) -> None:
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO build_meta (meta_key, meta_value)
                VALUES (?, ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value=excluded.meta_value
                """,
                list(values.items()),
            )

    def get_meta(self) -> dict[str, str]:
        if not self.table_exists("build_meta"):
            return {}
        with self.connect() as conn:
            rows = conn.execute("SELECT meta_key, meta_value FROM build_meta").fetchall()
        return {row["meta_key"]: row["meta_value"] for row in rows}

    def load_rows(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def artifact_count(self) -> int:
        if not self.table_exists("artifacts"):
            return 0
        return self.scalar("SELECT COUNT(*) FROM artifacts")

    def symbol_count(self) -> int:
        if not self.table_exists("symbols"):
            return 0
        return self.scalar("SELECT COUNT(*) FROM symbols")

    def topic_link_count(self) -> int:
        if not self.table_exists("artifact_topics"):
            return 0
        return self.scalar("SELECT COUNT(*) FROM artifact_topics")

    def artifact_link_count(self) -> int:
        if not self.table_exists("artifact_links"):
            return 0
        return self.scalar("SELECT COUNT(*) FROM artifact_links")

    def scalar(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row[0] if row is not None else 0)

    def replace_fts(self) -> bool:
        with self.connect() as conn:
            try:
                conn.execute("DROP TABLE IF EXISTS artifact_fts")
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE artifact_fts USING fts5(
                        artifact_id UNINDEXED,
                        title,
                        summary,
                        content,
                        qualified_name
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO artifact_fts (artifact_id, title, summary, content, qualified_name)
                    SELECT artifact_id, title, summary, content, COALESCE(qualified_name, '')
                    FROM artifacts
                    """
                )
                return True
            except sqlite3.OperationalError:
                conn.execute("DROP TABLE IF EXISTS artifact_fts")
                return False
