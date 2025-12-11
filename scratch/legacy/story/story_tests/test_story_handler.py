import logging

import pytest

from tangl.story import StoryHandler, Story

@pytest.fixture
def my_story(world):
    from tangl.story.world import WorldHandler
    story = WorldHandler.create_story(world)
    return story


def test_initialize_story(my_story):

    logging.debug(my_story.cursor)
    assert my_story.cursor is None
    assert isinstance(my_story, Story)

    # Verify initial state
    assert my_story.find_entry_node().path == "first_scene/start"

    my_story.enter()

    logging.debug(my_story.cursor)
    assert my_story.cursor is not None
    assert my_story.cursor.label == "second_block"

    print( my_story.journal )

    assert len( my_story.journal.items ) == 2
    assert len( my_story.journal.items[-1].actions ) == 1

    # todo: these get generated, but no entry index is set...


def test_get_story_info(my_story):

    status = StoryHandler.get_story_info(my_story)
    print( status )


def test_get_journal_entry(my_story):

    from tangl.journal import JournalingGraph
    assert isinstance(my_story, JournalingGraph)
    my_story.enter()
    update = StoryHandler.get_journal_entry(my_story)
    assert len(update) == 2
    print( update )
    assert len( update[1].actions ) == 1

def test_do_action(my_story):

    my_story.enter()
    assert my_story.cursor.label == "second_block"

    action = my_story.journal.items[-1].actions[-1].uid

    # Has 2 blocks of content and an action
    assert len( my_story.journal.items ) == 2
    assert len( my_story.journal.items[-1].actions ) == 1

    StoryHandler.do_action(my_story, action)
    logging.debug( my_story.cursor )
    assert my_story.cursor.label == "third_block"

    # Has 3 blocks of content
    assert len( my_story.journal.items ) == 3
