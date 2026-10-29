"""Actual cmd2 status commands retain full labels/values and ignore icon advice."""
from __future__ import annotations

import io
from pathlib import Path

from tangl.cli.app import StoryTanglCLI
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service.world_registry import pop_manual_world, register_manual_world

from pytest_helpers.status_icons import icon_world


def test_status_and_inventory_shortcut_keep_full_item_text(tmp_path: Path) -> None:
    world = icon_world(tmp_path / "icons", label="cli_status_icons")
    register_manual_world(world)
    manager = ServiceManager(PersistenceManagerFactory.native_in_mem())
    app = StoryTanglCLI(service_manager=manager, terminal_style="plain")
    app.stdout = io.StringIO()
    errors: list[str] = []

    def record_error(message: object = "", **_kwargs: object) -> None:
        errors.append(str(message))

    app.perror = record_error
    try:
        app.onecmd_plus_hooks("create_user status-reader")
        app.onecmd_plus_hooks(f"create_story {world.label}")
        with manager.open_session(user_id=app.user_id) as session:
            before = session.ledger.unstructure()
        for command in ("status ui-status", "status inv"):
            app.stdout.seek(0)
            app.stdout.truncate(0)
            app.onecmd_plus_hooks(command)
            output = app.stdout.getvalue()
            assert "Hall pass" in output and "Carried" in output
            assert "Brass token" in output and "Canvas pouch" in output
            assert "HP" not in output and "pass.svg" not in output
        with manager.open_session(user_id=app.user_id) as session:
            assert session.ledger.unstructure() == before
        app.onecmd_plus_hooks("do 1")
        app.stdout.seek(0)
        app.stdout.truncate(0)
        app.onecmd_plus_hooks("status inv")
        assert "Hall pass" not in app.stdout.getvalue()
        assert "Brass token" in app.stdout.getvalue()
        app.onecmd_plus_hooks("do 1")
        app.stdout.seek(0)
        app.stdout.truncate(0)
        app.onecmd_plus_hooks("status ui-status")
        assert "Hall pass" in app.stdout.getvalue()
        assert errors == []
    finally:
        pop_manual_world(world.label)
