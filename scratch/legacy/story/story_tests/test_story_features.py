import pytest

from tangl.story.actor import Actor

@pytest.fixture
def my_story(world):
    from tangl.story.world import WorldHandler
    story = WorldHandler.create_story(world)
    return story

def test_story_features(my_story):

    assert my_story.label == 'test_world'

    actor = my_story.find_node(with_cls=Actor)
    assert isinstance(actor, Actor)

    from tangl.story.player import Player
    assert isinstance(my_story.player, Player)
