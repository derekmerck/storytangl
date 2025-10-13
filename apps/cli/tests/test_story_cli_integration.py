from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.story.story_domain.world import World
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

@pytest.mark.xfail(reason="Revised cli requires a 'create story' to instantiate ledge")
def test_load_script_and_show_story(tangl_cli) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    output = _capture_output(app)

    assert "Loaded world: The Crossroads" in output, f"output is {output}"
    assert "The Crossroads" in output
    # assert "You stand at a crossroads" in output

    app.onecmd("story")
    output = _capture_output(app)

    assert "Story: story_" in output
    assert "# start" in output
    assert "You stand at a crossroads" in output
    # todo: Choice numbering is inconsistent?  Should be 1, 2
    assert "Take the left path" in output
    assert "Take the right path" in output

@pytest.mark.xfail(reason="Revised cli requires a 'create story' to instantiate ledge")
def test_choose_advances_story(tangl_cli) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("choose 1")
    output = _capture_output(app)

    assert "garden" in output.lower()
    assert "choices:" in output.lower()

    app.onecmd("do 1")
    output = _capture_output(app)

    assert "your adventure comes to an end" in output.lower()
    assert "no available actions" in output.lower()

@pytest.mark.xfail(reason="Revised cli requires a 'create story' to instantiate ledge")
def test_create_story_with_missing_world(tangl_cli) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd("create_story missing")
    output = _capture_output(app)

    assert "World 'missing' not found" in output

    app.onecmd("story")
    output = _capture_output(app)

    assert "No active story" in output
