from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.story.story_domain.world import World
from tangl.cli.app import TanglShell


TEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "demo_script.yaml"
)


@pytest.fixture(autouse=True)
def reset_worlds() -> None:
    World.clear_instances()
    yield
    World.clear_instances()


def _capture_output(app: TanglShell) -> str:
    output = app.stdout.getvalue()
    app.stdout.truncate(0)
    app.stdout.seek(0)
    return output


def test_load_script_and_show_story() -> None:
    app = TanglShell()
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    output = _capture_output(app)

    assert "Loaded world: crossroads_demo" in output
    assert "The Crossroads" in output
    assert "You stand at a crossroads" in output

    app.onecmd("story")
    output = _capture_output(app)

    assert "Story: story_" in output
    assert "# start" in output
    assert "You stand at a crossroads" in output
    # todo: Choice numbering is inconsistent?  Should be 1, 2
    assert "Take the left path" in output
    assert "Take the right path" in output

def test_choose_advances_story() -> None:
    app = TanglShell()
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


def test_create_story_without_world() -> None:
    app = TanglShell()
    app.stdout = io.StringIO()

    app.onecmd("create_story missing")
    output = _capture_output(app)

    assert "World 'missing' not found" in output

    app.onecmd("story")
    output = _capture_output(app)

    assert "No active story" in output
