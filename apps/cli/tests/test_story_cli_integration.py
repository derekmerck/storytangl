from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.story.fabula.world import World
from tangl.cli.app import create_cli_app, StoryTanglCLI as TanglShell


TEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "demo_script.yaml"
)


@pytest.fixture(autouse=True)
def reset_worlds() -> None:
    World.clear_instances()
    yield
    World.clear_instances()


@pytest.fixture()
def tangl_cli() -> TanglShell:
    app = create_cli_app()
    app.onecmd("create_user my_password")
    return app


def _capture_output(app: TanglShell) -> str:
    output = app.stdout.getvalue()
    app.stdout.truncate(0)
    app.stdout.seek(0)
    return output


def test_load_script_and_show_story(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    output = _capture_output(app)
    assert "Loaded world: The Crossroads" in output

    app.onecmd("create_story the_crossroads")
    output = _capture_output(app)

    assert "Created story:" in output
    assert "Story Begins" in output
    assert "You stand at a crossroads" in output
    assert "Choices:" in output
    assert "Take the left path" in output
    assert "Take the right path" in output

    app.onecmd("story")
    output = _capture_output(app)
    assert "Story Update:" in output
    assert "Choices:" in output


def test_create_story_bundles_journal_and_choices(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_crossroads")
    output = _capture_output(app)

    assert "Created story:" in output
    assert "Story Begins" in output
    assert "Choices:" in output
    assert "Use 'do <number>' to make a choice." in output


def test_choose_advances_story(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_crossroads")
    _capture_output(app)

    app.onecmd("do 2")
    output = _capture_output(app)
    assert "Story Update:" in output
    assert "garden" in output.lower()
    assert "No available choices" in output


def test_create_story_with_missing_world(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    with pytest.raises(ValueError):
        app.onecmd("create_story missing")
