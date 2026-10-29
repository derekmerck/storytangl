"""The stock CLI lists an anthology's books and opens one by id (#610)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.cli.app import StoryTanglCLI
from tangl.persistence import PersistenceManagerFactory
from tangl.service import build_service_manager
from tangl.service import world_registry
from tangl.story import World

SEARCH_ROOT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "anthology_worlds"
)


@pytest.fixture()
def cli(monkeypatch: pytest.MonkeyPatch) -> tuple[StoryTanglCLI, list[str]]:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [SEARCH_ROOT])
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    World.clear_instances()
    errors: list[str] = []
    app = StoryTanglCLI(
        service_manager=build_service_manager(PersistenceManagerFactory.native_in_mem()),
        terminal_style="plain",
    )
    app.stdout = io.StringIO()
    app.perror = lambda message="", **_kw: errors.append(str(message))  # type: ignore[method-assign]
    app.onecmd_plus_hooks("create_user anthology-reader")
    yield app, errors
    World.clear_instances()


def _run(app: StoryTanglCLI, command: str) -> str:
    app.stdout.seek(0)
    app.stdout.truncate(0)
    app.onecmd_plus_hooks(command)
    return app.stdout.getvalue()


def test_the_cli_lists_books_and_opens_one_by_id(cli: tuple[StoryTanglCLI, list[str]]) -> None:
    app, errors = cli

    listing = _run(app, "worlds")
    transcript = _run(app, "create_story shelf_second")

    assert errors == []
    assert "shelf_first" in listing and "shelf_second" in listing
    assert "The second book opens." in transcript


def test_the_cli_names_the_books_when_asked_for_the_anthology(
    cli: tuple[StoryTanglCLI, list[str]],
) -> None:
    app, errors = cli

    _run(app, "create_story shelf")

    assert any("open one of its books: shelf_first, shelf_second" in error for error in errors)
