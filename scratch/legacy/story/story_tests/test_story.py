from uuid import uuid4

from tangl.story.scene import Block, Scene, Action
from tangl.story import Story
from tangl.story.story_node import StoryNode as Node
from tangl.story.api import StoryApi

import pytest


def test_storynode_and_story():
    # this duplicates a test on Graph
    g = Story()
    print(g.nodes_by_path())

    root = Node(label='root', graph=g)

    assert root.graph is g
    assert root in g
    print(g.nodes_by_path())

    child1 = Node(label='child1')
    root.add_child(child1)

    assert child1.graph is g

    print(g.data.keys())

    assert child1 in g
    assert child1.path in g
    assert child1.guid in g

    child2 = Node(label='child2')
    root.add_child(child2)
    g.add_node(child2)

    assert len(root.children) == 2
    assert g.get(root.guid) == root
    assert g.get(root.guid) == root
    assert g.get(child1.guid) == child1
    assert g.get(child2.guid) == child2
    assert g.get(root.path) == root
    assert g.get(root.path) == root
    assert g.get(child1.path) == child1
    assert g.get(child2.path) == child2

    assert g.find(root.guid) == root
    assert g.find(root.guid) == root
    assert g.find(child1.guid) == child1
    assert g.find(child2.guid) == child2
    assert g.find(root.path) == root
    assert g.find(root.path) == root
    assert g.find(child1.path) == child1
    assert g.find(child2.path) == child2

    assert root.graph == g
    assert child1.graph == g
    assert child2.graph == g

    assert child1 in root.children
    root.remove_child(child1)
    assert child1 not in root.children

    g.remove_node(child2)
    assert child2 not in g

    with pytest.raises(KeyError):
        g.find("dog")

    with pytest.raises(KeyError):
        g.find(uuid4())

    with pytest.raises(TypeError):
        g.find(100)

    with pytest.raises(TypeError):
        assert 100 in g

    with pytest.raises(TypeError):
        node = Node(namespace=100)



def test_story():
    story = Story()

    # Create test Scenes and add them to the story
    scene1 = Scene(locals={"foo": 0, "scene_label": "scene1"}, label="scene1", is_entry=True, graph=story)
    scene2 = Scene(locals={"foo": 5, "scene_label": "scene2"}, label="scene2", graph=story)

    assert scene1 in story
    assert scene2 in story

    # Create a few test Blocks
    block1 = Block(locals={"foo": 0, "block_label": "block1"}, text="abc", label="block1", is_entry=True)
    scene1.add_child(block1)

    block2 = Block(locals={"foo": 5, "block_label": "block2", "action_label": "go to 2"}, label="block2")
    scene2.add_child(block2)

    # Create an Action from block1 pointing to block2
    action1 = Action.from_node(block1, block2)
    # add it to block1
    block1.add_child(action1)

    # Check that the entry scene can be evaluated
    assert story.entry_scene is scene1
    # Check that the entry block can be evaluated
    assert story.entry_scene.entry_block is block1
    # No bookmark yet
    assert story.bookmark is None

    # Start the story
    story.enter()

    # Entering the story sets the first bookmark
    print( story.bookmark )
    assert story.bookmark is block1  # Story starts at the entry scene's entry block (block1)

    entry, node = story.bookmark.enter()
    print( entry )
    assert entry == block1.render()
    print( node )
    assert node is None

    api = StoryApi(story)
    update = api.get_update()
    print( update )

    # assert update == [{
    #     'guid': str(block1.guid),
    #     'text': block1.text,
    #     'actions': [{
    #         'guid': str(block1.actions[0].guid),
    #         'label': block1.actions[0].label}]}]

    # Navigate to an action
    StoryApi(story).do_action(action1)
    assert story.bookmark == block2  # We are at block2 after the action

    # Check story status summary
    assert StoryApi(story).get_status() == [{'key': 'current_block', 'value': 'scene2/block2'}]
