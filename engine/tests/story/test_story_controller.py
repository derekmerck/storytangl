import pytest
from tangl.business.story.story_controller import StoryController

from fake_types import FakeStory, FakeAnonymousEdge

@pytest.fixture(autouse=True)
def patch_world(monkeypatch):
    """
    Replace the 'AnonymousEdge' class in 'story_controller' with 'FakeAnonymousEdge'.
    This fixture can be used for tests that force logic jumps
    """
    from tangl.business.story import story_controller
    monkeypatch.setattr(story_controller, "AnonymousEdge", FakeAnonymousEdge)
    return True

def test_direct_get_journal_entry():
    c = StoryController()
    endpoints = c.get_api_endpoints()
    ep = endpoints["get_journal_entry"]  # inferred from the method name

    # Provide a FakeStory with a known journal
    fake_story = FakeStory()
    result = ep(c, story=fake_story, item=1)  # direct call
    assert result == "entry1"  # from the fake journal

def test_direct_get_story_info():
    c = StoryController()
    ep = c.get_api_endpoints()["get_story_info"]

    fake_story = FakeStory()
    info = ep(c, story=fake_story, extra="stuff")
    # Should return a dictionary with "info" and "kwargs"
    assert "info" in info
    assert info["info"] == "FakeStory Info"
    assert info["kwargs"]["extra"] == "stuff"

def test_direct_get_story_media():
    c = StoryController()
    ep = c.get_api_endpoints()["get_story_media"]

    fake_story = FakeStory()
    # There's a "mediaX" object in the story's nodes
    result = ep(c, story=fake_story, media="mediaX")
    assert "Media content for mediaX" in result

def test_direct_do_step():
    c = StoryController()
    ep = c.get_api_endpoints()["do_step"]

    fake_story = FakeStory()
    fake_story.nodes['edgeX'].successor = fake_story.nodes['node1']
    assert not fake_story.dirty
    ep(c, story=fake_story, edge="edgeX", reason="testing")
    # The story should now be dirty, and the cursor changed
    assert fake_story.dirty
    assert fake_story.cursor.alias is "node1"

def test_direct_goto_node():
    c = StoryController()
    ep = c.get_api_endpoints()["goto_node"]

    fake_story = FakeStory()
    # The node "node1" is in the story's .nodes
    ep(c, story=fake_story, node="node1")
    # node1 should be dirty
    node1 = fake_story.nodes["node1"]
    assert node1.dirty
    # The story do_step was invoked
    assert fake_story.dirty

@pytest.mark.skip(reason="Not working yet")
def test_direct_check_condition():
    c = StoryController()
    ep = c.get_api_endpoints()["check_condition"]

    fake_story = FakeStory()
    # We'll override HasConditions.eval_str using a monkeypatch if needed,
    # or just store a dummy method
    # For now let's pretend gather_context -> {"story_state": "demo"}

    res = ep(c, story=fake_story, expr="some_expr")
    assert fake_story.dirty
    # We didn't define 'HasConditions.eval_str' in the fakes, so maybe your real code or a patch is needed
    # For demonstration, let's say it returns True or something
    # If you haven't monkeypatched HasConditions, might need to do that or skip

def test_direct_undo_step():
    c = StoryController()
    ep = c.get_api_endpoints()["undo_step"]
    fake_story = FakeStory()

    with pytest.raises(NotImplementedError):
        ep(c, story=fake_story)
