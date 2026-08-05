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


def test_annotated_plain_module_and_symbol_are_indexed(tmp_path) -> None:
    """Non-package, non-test modules opt into indexing via topic annotations."""

    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"
    _write(
        repo_root / "engine" / "src" / "tangl" / "core" / "annotated.py",
        '''
"""Annotated module.

.. storytangl-topic::
   :topics: selector
   :facets: code
   :relation: defines
"""

class Annotated:
    """Annotated symbol.

    .. storytangl-topic::
       :topics: registry
       :facets: code
       :relation: defines
    """
'''.strip()
        + "\n",
    )

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)

    module_hits = [
        artifact
        for artifact in search_topics("selector", db_path=db_path).artifacts
        if artifact.source_path.endswith("core/annotated.py") and artifact.kind != "symbol"
    ]
    symbol_hits = [
        artifact
        for artifact in search_topics("registry", db_path=db_path).artifacts
        if artifact.qualified_name is not None
        and artifact.qualified_name.endswith("annotated.Annotated")
    ]

    assert module_hits, "annotated module docstring should produce a module artifact"
    assert symbol_hits, "annotated class docstring should link its symbol artifact"

    # The declared classification must survive onto the artifact, not just the
    # topic link, since find/map report the artifact's own facet and relation.
    assert module_hits[0].facet == "code"
    assert module_hits[0].relation == "defines"
    assert module_hits[0].summary.startswith("Annotated module")


def test_myst_topic_fence_is_not_summarized_as_a_section(tmp_path) -> None:
    """A MyST directive must not leave its closing fence as the summary."""

    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"
    _write(
        repo_root / "docs" / "src" / "design" / "fenced.md",
        """
# Fenced

## Annotated Section

```{storytangl-topic}
:topics: entity
:facets: design
:relation: documents
```

The real opening paragraph.
""".strip()
        + "\n",
    )

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)

    hits = [
        artifact
        for artifact in search_topics("entity", db_path=db_path).artifacts
        if artifact.source_path.endswith("design/fenced.md")
    ]

    assert hits
    assert all("```" not in artifact.summary for artifact in hits)
    assert any(artifact.summary.startswith("The real opening paragraph") for artifact in hits)


def test_unannotated_plain_module_produces_no_module_artifact(tmp_path) -> None:
    """Annotation is the opt-in; ordinary modules stay symbol-only."""

    repo_root = _mini_repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)

    entity_module_hits = [
        artifact
        for artifact in search_topics("entity", db_path=db_path).artifacts
        if artifact.source_path.endswith("core/entity.py") and artifact.kind != "symbol"
    ]

    assert not entity_module_hits


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
