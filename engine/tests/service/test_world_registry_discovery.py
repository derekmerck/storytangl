"""World search-path discovery and its logging.

``world_dirs`` is a search path, so a root that is absent in this deployment is
ordinary. Reporting each one at warning level meant every local run of the CLI
and the server logged a container-only path it was never going to find.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tangl.service.world_registry import WorldRegistry


def _records(caplog, level: int) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno == level]


def test_absent_search_root_is_not_a_warning(tmp_path, caplog) -> None:
    present = tmp_path / "worlds"
    present.mkdir()

    with caplog.at_level(logging.DEBUG, logger="tangl.service.world_registry"):
        WorldRegistry(world_dirs=[Path("/nonexistent/worlds"), present])

    assert _records(caplog, logging.WARNING) == []
    assert any("/nonexistent/worlds" in message for message in _records(caplog, logging.DEBUG))


def test_search_path_with_no_existing_root_warns_once(tmp_path, caplog) -> None:
    with caplog.at_level(logging.DEBUG, logger="tangl.service.world_registry"):
        WorldRegistry(world_dirs=[Path("/nonexistent/a"), Path("/nonexistent/b")])

    warnings = _records(caplog, logging.WARNING)

    assert len(warnings) == 1
    assert "/nonexistent/a" in warnings[0]
    assert "/nonexistent/b" in warnings[0]


def test_empty_search_path_warns(caplog) -> None:
    with caplog.at_level(logging.DEBUG, logger="tangl.service.world_registry"):
        WorldRegistry(world_dirs=[])

    warnings = _records(caplog, logging.WARNING)

    assert len(warnings) == 1
    assert "nothing configured" in warnings[0]


def test_bundles_still_load_from_a_present_root(tmp_path, caplog) -> None:
    """An absent root must not stop the scan of the roots that do exist."""

    repo_worlds = Path(__file__).resolve().parents[3] / "worlds"

    with caplog.at_level(logging.DEBUG, logger="tangl.service.world_registry"):
        registry = WorldRegistry(world_dirs=[Path("/nonexistent/worlds"), repo_worlds])

    assert registry.bundles
    assert _records(caplog, logging.WARNING) == []
