from pprint import pprint
from uuid import uuid4, UUID

import attr
import yaml

from tangl.world.script import ScriptHandler
from tangl.core.utils.cattrs_converter import NodeConverter
from tangl.story import Story
from tangl.story.scene import Scene, Block, Action
from tangl.story.actor import Role, Actor

import pytest




def test_story_script_handler(sample_world_sf_text):
    sh = ScriptHandler.from_text(sample_world_sf_text)
    pprint(sh.script)
    r = sh.create_story()
    pprint(r)
    assert set( r.nodes_by_path() ) == {'player', 'scene1', 'scene1/ro-alice', 'scene1/ro-bob', 'scene1/start', 'scene1/start/ac-0', 'scene1/child1', 'scene1/child1/ac-0', 'scene1/child2', 'scene1/child2/ac-0', 'alice', 'bob'}

    alice = r['alice']
    assert isinstance(alice, Actor)
    assert alice.name == "Alice"

def test_story_script_handler_text_by_path(sample_world_sf_text):
    sh = ScriptHandler.from_text(sample_world_sf_text)
    strings_map = sh.strings_map()

    assert strings_map == {'scene1/child1': "You're in next block",
                           'scene1/child2': "You're in the last block",
                           'scene1/start': "You're in the start block",
                           'scene1/start/ac-0': 'Go to node1'}

@pytest.mark.skip('Dumb circular imports...')
def test_scripted_story_is_serializable(sample_world_sf_text):

    sh = ScriptHandler.from_text(sample_world_sf_text)
    r = sh.create_story()
    nc = NodeConverter.get_preconf('yaml')
    y = nc.unstructure(r)

    # print(yaml.safe_dump(y, sort_keys=False))

    rr = nc.structure(y, Story)

    # print( r.nodes_by_path().keys() )

    # print( r['scene1/root/ac-0']._target_node )
    # print( rr['scene1/root/ac-0']._target_node )

    # check items with weakrefs
    for k, v in r.items():
        if isinstance(v, Action | Role):
            assert v == rr[k]
    for k, v in r.items():
        if isinstance(v, Block | Scene):
            assert v == rr[k]

    assert rr.data == r.data
    print( attr.asdict( r, filter=lambda f, v: f.name != 'data') )
    print( attr.asdict( rr, filter=lambda f, v: f.name != 'data') )

    assert rr == r


def test_scene_block_action_from_script():
    from tangl.world.script.models import SceneScript

    # Define a YAML data for Scene
    sc_data = {
        'blocks': {

            'dog': {
                'text': 'a dog',
                'actions': [{'target_node': uuid4()}]
            },
            'cat': {
                'text': 'a cat',
                'actions': [{'target_node': uuid4()}]
            }
        }
    }

    sc_script = SceneScript( **sc_data )

    # Convert data to Scene
    scene = ScriptHandler.mk_scene("Test Scene", sc_script)

    # Check if the converted Scene has the same guid
    assert scene.label == "Test Scene"
    assert scene.blocks[0].label == "dog"

    # Check if the children are correctly added as blocks
    assert len(scene.blocks) == 2

    # Check if the actions of each block were correctly added
    for block in scene.blocks:
        assert len(block.actions) == 1
        for action in block.actions:
            assert isinstance(action.target_node, UUID)


def test_load_story():
    # Define a story
    story_yaml = """
    label: test_story
    metadata:
      title: Test Story
      author: Test Author
    scenes: 
      scene_1:
        is_entry: True
        blocks: 
          block_1:
            text: "You are in a block."
            is_entry: True
            actions:
            - text: Do something
              target_node: dummy
            - label: something_else
              text: Do something else
              target_node: dummy
    """

    # Load the story into a dictionary
    story_dict = yaml.safe_load(story_yaml)
    s = ScriptHandler.from_dict(story_dict)
    story = s.create_story()
    assert 'scene_1/block_1/ac-0' in story
    assert 'scene_1/block_1/something_else' in story

    # # Instantiate a story world with the story dictionary
    # world = World(label="test_world")
    # story = world.create_story()

    # Ensure that the story was loaded correctly
    assert len( story.scenes ) == 1
    assert story.scenes[0].label == "scene_1"
    assert len(story.scenes[0].blocks) == 1
    assert story.scenes[0].blocks[0].label == "block_1"
    assert story.scenes[0].blocks[0].text == "You are in a block."


def test_entry_conditions():
    # Define a story with three blocks and two actions in the first block
    story_yaml = """
    label: test_story
    metadata:
      title: Test Story
      author: Test Author
    scenes: 
      scene_1:
        is_entry: True
        locals: { foo: -1 }
        blocks: 
          block_1:
            text: "You are at the start."
            is_entry: True
            actions: 
              - label: "action_1"
                text: "Go to block 2"
                target_node: "block_2"
              - label: "action_2"
                text: "Go to block 3"
                target_node: "block_3"
          block_2:
            conditions: [ "foo > 0" ]
            text: "You are in block 2."
          block_3:
            conditions: [ "foo > 0" ]
            text: "You are in block 3."
    """

    # Load the story into a dictionary
    story_dict = yaml.safe_load(story_yaml)
    s = ScriptHandler.from_dict(story_dict)
    story = s.create_story()

    # Ensure that the story was loaded correctly
    assert len(story.scenes) == 1
    assert story.scenes[0].label == "scene_1"
    assert len(story.scenes[0].blocks) == 3

    assert not story.scenes[0].blocks[1].available()
    assert not story.scenes[0].blocks[2].available()
    story.scenes[0].blocks[1].locals["foo"] = 10

    print( story.scenes[0].blocks[1].ns() )

    # this should override the scene local
    assert story.scenes[0].blocks[1].available()
    # but block 3 is still not enterable
    assert not story.scenes[0].blocks[2].available()

    assert story.scenes[0].story is story
    assert story.scenes[0].blocks[0].story is story

    # Here is a mermaid diagram of the conditional branching
    """
    graph LR
      id1((Block 1)) -->|action_1| id2{{Block 2}}
      id1 -->|action_1| id4{{Block 2 foo=10}}
      id1((Block 1)) -->|action_2| id3{{Block 3}}

      classDef enterable fill:green,stroke:black;
      classDef unenterable fill:red,stroke:black;

      class id1 enterable;
      class id2,id3 unenterable;

      class id4 enterable;
    """