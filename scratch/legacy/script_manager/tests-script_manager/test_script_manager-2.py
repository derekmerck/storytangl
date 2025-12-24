from pathlib import Path
import yaml

import pytest

from tangl.scripting.master_script_model import MasterScript

from tangl.scripting import ScriptManager


@pytest.fixture
def my_script(my_script_data):
    mscript = MasterScript(**my_script_data)
    return mscript

@pytest.fixture
def my_script_manager(my_script):
    sm = ScriptManager(master_script=my_script)
    return sm


def test_script_from_data(my_script_data):

    mscript = MasterScript(**my_script_data)

    print( mscript )

    assert mscript.label == "test_script"
    assert len( mscript.scenes ) == 2

    assert mscript.locals['foo'] == "bar"


def test_script_manager_from_data(my_script_data, my_script):

    sm = ScriptManager.from_data(my_script_data)
    print( sm )
    assert sm.master_script == my_script


def test_get_globals(my_script_manager):

    g = my_script_manager.get_story_globals()
    print( g )
    assert g['foo'] == "bar"


# def test_get_text(my_script_manager):
#
#     g = my_script_manager.get_story_text()
#     print( g )
#     assert isinstance(g, list)
#     assert g[0]['text'].startswith("This is the first")


def test_get_unstructured(my_script_manager):

    for node_data in my_script_manager.get_unstructured('scenes'):
        print( node_data )

    assert len( list(my_script_manager.get_unstructured('scenes'))) == 2

def test_convert_unstructured(my_script_manager):

    from tangl.story.scene import Scene
    from tangl.story.actor import Actor
    from tangl.core.entity.handlers import SelfFactoringHandler

    for node_data in my_script_manager.get_unstructured('scenes'):
        node_data.setdefault('obj_cls', Scene)
        sc = SelfFactoringHandler.create_node( **node_data )
        print( sc )

    for node_data in my_script_manager.get_unstructured('actors'):
        node_data.setdefault('obj_cls', Actor)
        ac = SelfFactoringHandler.create_node( **node_data )
        print( ac )


def test_custom_types(my_script_manager):

    from tangl.story.scene import Scene
    from tangl.core.entity.handlers import SelfFactoringHandler

    class MyScene(Scene):
        # All StoryNode types are subclassed from InheritanceAware
        ...

    # test direct cast
    for node_data in my_script_manager.get_unstructured('scenes'):
        node_data['obj_cls'] = MyScene
        sc = SelfFactoringHandler.create_node( **node_data )
        assert isinstance( sc, MyScene )

    # test string cast (requires InheritanceAware)
    for node_data in my_script_manager.get_unstructured('scenes'):
        node_data['obj_cls'] = "MyScene"
        sc = SelfFactoringHandler.create_node( **node_data )
        assert isinstance( sc, MyScene )
