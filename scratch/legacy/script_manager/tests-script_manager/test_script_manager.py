from pprint import pprint

import pytest
import pydantic

from tangl.script import ScriptManager
from tangl.script.script_models import *
from tangl.story.scene import Block

SpecialBlock = pydantic.create_model("SpecialBlock", __base__ = Block)

@pytest.fixture()
def sample_world_sm(sample_world_sf_dict):
    return ScriptManager.from_dict(sample_world_sf_dict)

def test_script_models(sample_world_sf_dict):
    metadata_ = sample_world_sf_dict['metadata']
    metadata = StoryMetadata( **metadata_ )
    print( metadata )

    for scene_ in sample_world_sf_dict['scenes'].values():

        for block_ in scene_['blocks'].values():
            block = BlockScript( **block_ )
            print( block )

        for role_ in scene_['roles'].values():
            role = RoleScript( **role_ )
            print( role )

        scene = SceneScript( **scene_ )
        print( scene )

    story = StoryScript( **sample_world_sf_dict )
    print( story )

def test_script_manager(sample_world_sf_text):

    script_manager = ScriptManager.from_text( sample_world_sf_text )
    print( script_manager.script )

# @pytest.mark.xfail(reason="needs to be reimplmented")
def test_strings_map(sample_world_sm):

    strings_map = sample_world_sm.strings_map()
    pprint( strings_map )

# def test_story_creation(sample_world_sm):
#
#     assert Block.get_subclass_by_name('SpecialBlock') is SpecialBlock
#
#     story = sample_world_sm.create_story()
#     print( story )

def test_story_script_handler_schema(sample_world_sm):
    s = sample_world_sm.get_script_schema()
    pprint( s )
