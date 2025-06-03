import pytest
from unittest.mock import MagicMock

from cmd2 import Cmd

from tangl.cli.controllers import StoryController, WorldController, UserController, SystemController, DevController
from tangl.cli.app_service_manager import get_service_manager, get_user_id

from tests.conftest import my_script_data
from tests.story.conftest import world

@pytest.fixture(autouse=True)
def recreate_story(world):
    sm = get_service_manager()
    user_id = get_user_id()
    sm.create_story(user_id, world_id="test_world")

@pytest.fixture
def story_controller():
    controller = Cmd(StoryController)
    controller.poutput = print
    return controller


def test_story_controller_do_story( story_controller, capsys ):

    story_controller.do_story('')

    # Capture the output
    captured = capsys.readouterr()
    printed_data: str = captured.out

    print(printed_data)

    # todo: should not include the <p>'s, request response without md2html
    assert printed_data.startswith("Story Update:\n-------------------------\n<p>This is the first block of the first scene</p>"), f'Output starts with {printed_data[0:20]}'


def test_story_controller_do_do(story_controller, capsys):

    # fill the update buffer
    story_controller.do_story('')
    # invoke the continue action
    story_controller.do_do('0')

    # Capture the output
    captured = capsys.readouterr()
    printed_data: str = captured.out

    print( printed_data )
    # todo: verify printed_data contents...


@pytest.fixture
def user_controller():
    controller = Cmd(UserController)
    controller.poutput = print
    return controller

@pytest.fixture
def world_controller():
    controller = Cmd(WorldController)
    controller.poutput = print
    return controller


@pytest.mark.xfail(raises=NotImplementedError)
def test_world_controller_do_world_info( world_controller, capsys ):
    world_controller.do_world_info('test_world')

    # Capture the output
    captured = capsys.readouterr()
    printed_data: str = captured.out

    print( printed_data )
    # todo: verify printed_data contents...


@pytest.fixture
def system_controller():
    controller = Cmd(SystemController)
    controller.poutput = print
    return controller

def test_system_controller_do_system_info( system_controller, capsys ):
    system_controller.do_system_info('')

# Similar tests for other controller methods...
