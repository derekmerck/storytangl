import pytest

from tangl.core.graph.handlers import TraversableNode
from tangl.story import Story, StoryNode, StoryHandler
from tangl.story.player import Player

@pytest.mark.skip()
def test_player():
    # todo
    pass

TestTraversableStoryNode = type("TestTraversableStoryNode", (StoryNode, TraversableNode), {})

def test_story_find_entry():
    node = TestTraversableStoryNode(tags={'is_entry'})
    story = node.story
    assert isinstance(story, Story)
    assert story.find_entry_node() is node

    child = TestTraversableStoryNode(label="start")
    node.add_child(child)
    assert node.find_entry_node() is child

def test_story_enter():
    node = TestTraversableStoryNode(tags={'is_entry'})
    child = TestTraversableStoryNode(label="start")
    node.add_child(child)

    story = node.story
    assert story.cursor is None
    story.enter()
    assert story.cursor is child, f"Story cursor is {story.cursor!r}"


def test_story_pickles():
    import pickle

    r = Story()
    p = Player(name="Bob Smith")
    r.add_node(p)
    k = StoryNode(label="Test Node k")
    print( k )
    r.add_node(k)

    r_pkl = pickle.dumps(r)
    rr = pickle.loads(r_pkl)

    assert r == rr
    assert r.nodes == rr.nodes
