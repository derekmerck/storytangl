import pytest

pytest.skip(reason="v34 broken", allow_module_level=True)

from uuid import uuid4
from tangl.service.api_endpoint import AccessLevel
from tangl.service.service_manager import ServiceManager
from tangl.story.story_controller import StoryController
from fake_types import FakeStory, FakeUser, FakeAnonymousEdge

@pytest.fixture(autouse=True)
def patch_story(monkeypatch):
    """
    Replace the 'AnonymousEdge' class in 'story_controller' with 'FakeAnonymousEdge'.
    This fixture can be used for tests that force logic jumps
    """
    from tangl.story import story_controller
    monkeypatch.setattr(story_controller, "AnonymousEdge", FakeAnonymousEdge)
    return True

@pytest.fixture
def story_context():
    """
    Provide a dictionary that has a user plus a story object.
    The user points to the story's ID.
    The story might have a small journal, etc.
    """
    user_id = uuid4()
    story_id = uuid4()

    user = FakeUser(uid=user_id, access_level=AccessLevel.USER, current_story_id=story_id)
    story = FakeStory()
    # We'll store them by their IDs
    ctx = {
        user_id: user,
        story_id: story
    }
    return ctx

@pytest.fixture
def story_service_manager(story_context):
    """Create a ServiceManager with a single controller: StoryController."""
    mgr = ServiceManager(context=story_context, components=[StoryController])
    return mgr

def test_get_journal_entry_integration(story_service_manager):
    """
    Test calling get_journal_entry via the manager.
    Must supply user_id => manager opens user => manager finds story =>
    calls the method with story= that object.
    """
    ep_key = "StoryController.get_journal_entry"
    user_id = next(iter(story_service_manager.context.keys()))
    # Actually check it's a user
    ep = story_service_manager.endpoints[ep_key]

    # item=-1 => last entry in the fake journal
    result = ep(user_id=user_id, item=-1)
    assert result == "entry2"  # from FakeStory's default journal ["entry0","entry1","entry2"]

def test_get_story_info_integration(story_service_manager):
    ep_key = "StoryController.get_story_info"
    user_id = next(iter(story_service_manager.context.keys()))

    info = story_service_manager.endpoints[ep_key](user_id=user_id, extra="someargs")
    # Should be the dictionary from story.get_info(...)
    assert info["info"] == "FakeStory Info"
    assert info["kwargs"]["extra"] == "someargs"

def test_do_step_integration(story_service_manager):
    """Check that do_step sets story.dirty and calls resolve_step."""
    ep_key = "StoryController.do_step"
    user_id = next(iter(story_service_manager.context.keys()))

    # Initially not dirty
    story_obj = story_service_manager.context[story_service_manager.context[user_id].current_story_id]
    assert not story_obj.dirty

    story_service_manager.endpoints[ep_key](user_id=user_id, edge="edgeX")
    assert story_obj.dirty

def test_restricted_method_requires_restricted_acl(story_service_manager):
    """
    goto_node is restricted => user must have access_level >= RESTRICTED
    or else the manager should raise an error.
    """
    ep_key = "StoryController.goto_node"
    user_id = next(iter(story_service_manager.context.keys()))

    user_obj = story_service_manager.context[user_id]
    assert user_obj.access_level == AccessLevel.USER  # defaults

    # So this should fail
    with pytest.raises(RuntimeError, match="exceeds method acl"):
        story_service_manager.endpoints[ep_key](user_id=user_id, node="node1")

    # Now upgrade user to restricted
    user_obj.access_level = AccessLevel.RESTRICTED
    # Try again
    story_service_manager.endpoints[ep_key](user_id=user_id, node="node1")

    # Should succeed, node1 becomes dirty, etc.

def test_undo_step_not_implemented(story_service_manager):
    """undo_step is a MethodType.UPDATE, but it raises NotImplementedError."""
    ep_key = "StoryController.undo_step"
    user_id = next(iter(story_service_manager.context.keys()))

    with pytest.raises(NotImplementedError):
        story_service_manager.endpoints[ep_key](user_id=user_id)
