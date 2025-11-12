from __future__ import annotations

import io
from pathlib import Path

import pytest

from tangl.story.fabula.world import World
from tangl.cli.app import create_cli_app, StoryTanglCLI as TanglShell


TEST_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "demo_script.yaml"
)

LINEAR_SCRIPT = (
    Path(__file__).resolve().parents[3] / "engine" / "tests" / "resources" / "linear_script.yaml"
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


def test_linear_story_initializes_and_lists_choices(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {LINEAR_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_path")
    output = _capture_output(app)

    assert "Created story:" in output
    assert "You begin your journey at dawn." in output
    assert "Continue" in output
    assert "Use 'do <number>' to make a choice." in output


def test_linear_story_walkthrough(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {LINEAR_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_path")
    _capture_output(app)

    app.onecmd("story")
    story_output = _capture_output(app)
    assert "You begin your journey at dawn." in story_output
    assert "1. Continue" in story_output

    app.onecmd("do 1")
    second_step = _capture_output(app)
    assert "The path winds through ancient woods." in second_step
    assert "Choices:" in second_step

    app.onecmd("do 1")
    final_output = _capture_output(app)
    assert "You arrive at the village." in final_output
    assert "No available choices." in final_output


def test_branching_story_left_path_cli(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_crossroads")
    first_update = _capture_output(app)

    assert "Choices:" in first_update
    assert "1. exit crossroads" in first_update
    assert "2. Take the left path" in first_update
    assert "3. Take the right path" in first_update

    app.onecmd("do 2")
    second_update = _capture_output(app)

    assert "The left path opens into a peaceful garden." in second_update
    assert "Flowers bloom everywhere." in second_update
    assert "No available choices." in second_update


def test_branching_story_cave_path_cli(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_crossroads")
    first_update = _capture_output(app)
    assert "3. Take the right path" in first_update

    app.onecmd("do 3")
    cave_update = _capture_output(app)

    assert "The right path leads to a dark cave." in cave_update
    assert "You hear strange sounds within." in cave_update
    assert "1. Enter the cave" in cave_update
    assert "2. Go back" in cave_update

    app.onecmd("do 1")
    interior_update = _capture_output(app)

    assert "The cave is deeper than you thought" in interior_update
    assert "No available choices." in interior_update


def test_branching_story_cave_backtrack_cli(tangl_cli: TanglShell) -> None:
    app = tangl_cli
    app.stdout = io.StringIO()

    app.onecmd(f"load_script {TEST_SCRIPT}")
    _capture_output(app)

    app.onecmd("create_story the_crossroads")
    _capture_output(app)

    app.onecmd("do 3")
    _capture_output(app)

    app.onecmd("do 2")
    backtrack_update = _capture_output(app)

    assert "You stand at a crossroads in the forest." in backtrack_update
    assert "Take the left path" in backtrack_update
    assert "No available choices." in backtrack_update
