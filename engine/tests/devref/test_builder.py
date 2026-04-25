from __future__ import annotations

from pathlib import Path

from tangl.devref.builder import build_index
from tangl.devref.query import search_topics


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "mini_repo"
    _write(
        repo / "AGENTS.md",
        "# Contributor Guide\n\nRead the entity and dispatch sections.\n",
    )
    _write(
        repo / "ARCHITECTURE.md",
        "# StoryTangl Architecture\n\n## Entity\n\nEntity overview.\n\n## Dispatch\n\nDispatch overview.\n",
    )
    _write(
        repo / "docs" / "src" / "api" / "core" / "identity.rst",
        """
Identity
========

.. storytangl-topic::
   :topics: entity, selector
   :facets: api
   :relation: documents

.. autoclass:: tangl.core.entity.Entity
""".strip()
        + "\n",
    )
    _write(
        repo / "engine" / "src" / "tangl" / "__init__.py",
        '"""Test namespace."""\n',
    )
    _write(
        repo / "engine" / "src" / "tangl" / "core" / "__init__.py",
        '"""Core overview for Entity and Selector."""\n',
    )
    _write(
        repo / "engine" / "src" / "tangl" / "core" / "entity.py",
        '''
"""Entity module."""

class Entity:
    """Entity for tests."""

    def __init__(self, label: str | None = None):
        self.label = label
'''.strip()
        + "\n",
    )
    _write(
        repo / "engine" / "tests" / "core" / "entity" / "test_entity.py",
        '''
"""Entity tests.

.. storytangl-topic::
   :topics: entity
   :facets: tests
   :relation: tests
"""
'''.strip()
        + "\n",
    )
    _write(
        repo / "worlds" / "logic_demo" / "README.md",
        "# Logic Demo\n\nEntity demo world.\n",
    )
    return repo


def test_build_index_full_and_noop(tmp_path) -> None:
    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"

    first = build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    second = build_index(repo_root=repo_root, db_path=db_path, incremental=True)

    assert first.build_mode == "full"
    assert first.artifacts > 0
    assert first.symbols > 0
    assert second.build_mode == "noop"
    assert second.changed_sources == 0


def test_build_index_incremental_detects_changed_source(tmp_path) -> None:
    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    architecture = repo_root / "ARCHITECTURE.md"
    architecture.write_text(
        "# StoryTangl Architecture\n\n## Entity\n\nUpdated entity overview.\n",
        encoding="utf-8",
    )

    report = build_index(repo_root=repo_root, db_path=db_path, incremental=True)
    response = search_topics("entity", db_path=db_path)

    assert report.build_mode == "incremental"
    assert report.changed_sources == 1
    assert response.artifacts[0].summary.lower().startswith("updated entity overview")


def test_build_index_skips_import_side_effects_and_bad_python(tmp_path) -> None:
    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"
    marker_path = tmp_path / "imported.txt"
    _write(
        repo_root / "engine" / "src" / "tangl" / "core" / "side_effect.py",
        f'''
"""Side effect module."""

from pathlib import Path

Path({str(marker_path)!r}).write_text("imported", encoding="utf-8")

class SideEffect:
    """Indexable without running module import side effects."""
'''.strip()
        + "\n",
    )
    _write(
        repo_root / "engine" / "src" / "tangl" / "core" / "bad.py",
        "def broken(:\n",
    )

    report = build_index(repo_root=repo_root, db_path=db_path, incremental=False)

    assert report.symbols > 0
    assert not marker_path.exists()
