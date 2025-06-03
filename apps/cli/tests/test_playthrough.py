
import yaml
import pytest
from cmd2_ext_test import ExternalTestMixin

from tangl.story.world import World
from tangl.scripting import ScriptManager

from tangl.cli.app import TanglShell
from tests.conftest import test_resources


@pytest.fixture(scope='session')
def demo_script_data():
    fp = test_resources / 'demo_script.yaml'
    with open(fp) as f:
        data = yaml.safe_load(f)
    return data

@pytest.fixture(autouse=True)
def demo_world(demo_script_data):
    World.clear_instances()
    sm = ScriptManager.from_data(demo_script_data)
    world = World(label='demo_world', script_manager=sm)
    yield world
    World.clear_instances()


def test_cli_story_playthrough(capsys):

    app = TanglShell()  # capsys does not like the 'app' fixture

    # Create/load story
    app.onecmd("create_story demo_world")
    captured = capsys.readouterr()
    assert "crossroads" in captured.out

    # Try choices
    app.onecmd("story")  # Show current state
    captured = capsys.readouterr()
    assert "1. Take the left path" in captured.out
    assert "2. Take the right path" in captured.out

    # Make choice
    app.onecmd("do 1")  # Choose left path
    captured = capsys.readouterr()
    assert "peaceful garden" in captured.out

    # Check status
    app.onecmd("status")
    captured = capsys.readouterr()
    assert "Story Status" in captured.out


def test_story_scripted_playthrough(tmpdir, capsys):

    script = """
    create_story demo_world
    story
    do 1
    status
    """
    with open(tmpdir / 'script.txt', 'w') as f:
        f.write(script)

    app = TanglShell()
    app.do_run_script(str(tmpdir / 'script.txt'))

    captured = capsys.readouterr()
    assert "crossroads" in captured.out
    assert "peaceful garden" in captured.out
    assert "Story Status" in captured.out


# -----------------------
# EXTERNAL TESTING PLUGIN
# -----------------------

# Captures output directly with each cmd invocation

class TesterAfcShell(ExternalTestMixin, TanglShell):
    def __init__(self, *args, **kwargs):
        # Need this or neither the plugin nor cmd2 will initialize
        super().__init__(*args, **kwargs)

@pytest.fixture
def tester_app():
    app = TesterAfcShell()
    app.fixture_setup()
    yield app
    app.fixture_teardown()

def test_basic_story(tester_app):

    app = tester_app

    # Create and start story
    out = app.app_cmd("create_story demo_world")
    assert "crossroads" in out.stdout

    # Check available choices
    out = app.app_cmd("story")
    assert "1. Take the left path" in out.stdout
    assert "2. Take the right path" in out.stdout

    # Make choice
    out = app.app_cmd("do 1")
    assert "peaceful garden" in out.stdout

    # Verify status
    out = app.app_cmd("status")
    assert "Story Status" in out.stdout

