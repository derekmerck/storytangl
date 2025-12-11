import pytest
from uuid import uuid4, UUID

from tangl.story import Story
from tangl.story.scene import Block, Scene, Action
from tangl.story.actor.role import Role

def _sample_scene():
    story = Story()
    scene = Scene(label="scene1",
                  text="Test Scene",
                  tags={'is_entry'},
                  graph=story)

    # Create some Blocks
    block1 = Block(label="block1", text="Block 1", tags={"is_entry"})
    block2 = Block(label="block2", text="Block 2")

    # Add Blocks as children of the Scene
    scene.add_child(block1)
    scene.add_child(block2)

    role = Role(label="role1", actor_template={'label': 'john', 'name': 'John Doe'}, graph=story)
    scene.add_child(role)

    return scene

@pytest.fixture
def sample_scene():
    return _sample_scene()

def test_scene(sample_scene):
    assert sample_scene.text == "Test Scene"
    assert len(sample_scene.blocks) == 2
    assert len(sample_scene.roles) == 1

    block = sample_scene.blocks[0]
    assert block.parent == sample_scene

    role = sample_scene.roles[0]
    assert role.parent == sample_scene


def test_scene_pickles(sample_scene):
    import pickle

    s = pickle.dumps(sample_scene)
    res = pickle.loads(s)
    print(res)
    assert sample_scene == res

# @pytest.skip(reason="not sure why its not working...")
def test_scene_properties_and_methods(sample_scene):

    # Check enterability
    assert sample_scene.available()  # entry conditions are satisfied

    # Enter scene
    sample_scene.enter()

    block1 = sample_scene.blocks[0]
    assert block1.render()

@pytest.fixture
def sample_scene_with_continue():
    sc = _sample_scene()
    cont = Action(successor_ref="block2", activation="exit")
    sc.block1.add_child(cont)
    return sc

def test_traversed_scene_properties_and_methods(sample_scene_with_continue):
    sample_scene = sample_scene_with_continue

    # Check enterability
    assert sample_scene.available()  # entry conditions are satisfied

    # Enter scene
    sample_scene.enter()

    assert sample_scene.visited
    assert sample_scene.block1.visited
    assert sample_scene.block2.visited

    print( sample_scene.story.journal.items )

# def test_scene_create():
#     scene_data = {
#         "uid": "scene1",
#         "title": "Title",
#         "description": "Description",
#         "blocks": [{"uid": "block1", "text": "Block Text"}],
#         "roles": [{"uid": "role1", "actor": {"uid": "actor1", "name": "Actor Name"}}]
#     }
#
#     scene = Scene.create(scene_data)
#
#     assert scene.uid == "scene1"
#     assert scene.title == "Title"
#     assert scene.description == "Description"
#     assert len(scene.blocks) == 1
#     assert scene.blocks[0].uid == "block1"
#     assert scene.blocks[0].text == "Block Text"
#     assert len(scene.roles) == 1
#     assert scene.roles[0].uid == "role1"
#     assert scene.roles[0].actor.uid == "actor1"
#     assert scene.roles[0].actor.name == "Actor Name"
#
# def test_scene_add_invalid_block():
#     scene = Scene(uid="scene1", title="Title", description="Description")
#     with pytest.raises(TypeError):
#         scene.add_block("Invalid Block")
#
# def test_scene_add_existing_block():
#     scene = Scene(uid="scene1", title="Title", description="Description")
#     block = Block(uid="block1", text="Block Text")
#     scene.add_block(block)
#     with pytest.raises(ValueError):
#         scene.add_block(block)
#
#     role = Role(uid="role1")
#     scene.add_role(role)
#     with pytest.raises(ValueError):
#         scene.add_role(role)
