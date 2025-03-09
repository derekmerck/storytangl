import pytest

from tangl.business.world import world_controller, WorldController
from tangl.service.api_endpoints import MethodType, AccessLevel

from tests.fake_types import FakeWorld, FakeStory


@pytest.fixture(autouse=True)
def patch_world(monkeypatch):
    """
    Replace the 'World' class in 'world_controller' with 'FakeWorld'.
    This fixture can be used for tests that need to intercept calls
    to 'World.get_instance' etc.
    """
    from tangl.business.world import world_controller
    monkeypatch.setattr(world_controller, "World", FakeWorld)
    # Optionally ensure no leftover state
    FakeWorld._instances.clear()
    return True

def test_get_world_info_with_patch():
    """
    Example test that calls 'get_world_info' with a monkey-patched FakeWorld.
    """
    c = WorldController()
    print( world_controller.World )
    print( world_controller._dereference_world_id((), kwargs={"world_id": "mars"}) )

    # We get the endpoint from reflection or directly from the class method
    ep = c.get_api_endpoints()["get_world_info"]

    # Now, calls to 'World.get_instance("mars")' inside the controller code
    # are actually 'FakeWorld.get_instance("mars")'
    result = ep(c, world_id="mars")
    assert result.label == "mars"
    assert result.name == "FakeWorld-mars"

def test_world_controller_inference():
    """
    Ensure the method_type and access_level were set
    according to your annotate usage.
    """
    endpoints = WorldController.get_api_endpoints()

    assert "load_world" in endpoints
    load_ep = endpoints["load_world"]
    assert load_ep.access_level == AccessLevel.RESTRICTED
    assert load_ep.method_type == MethodType.CREATE  # or default from 'load_' prefix

    unload_ep = endpoints["unload_world"]
    assert unload_ep.access_level == AccessLevel.RESTRICTED
    # from prefix 'unload_', we might expect method_type=CREATE or DELETE
    # depending on your naming rules. Check the actual code or usage.

    info_ep = endpoints["get_world_info"]
    assert info_ep.access_level == AccessLevel.PUBLIC
    assert info_ep.method_type == MethodType.READ

    # etc. for the rest of them
    # "create_story" should have access_level=USER, "group"=user, etc.


def test_world_controller_direct_calls(monkeypatch):
    """
    Call the WorldController endpoints *directly*, providing the
    'world' object ourselves via the preprocessor or manually.
    """
    # We'll get the endpoints from reflection
    endpoints = WorldController.get_api_endpoints()

    # We'll create a test world object:
    w = FakeWorld.get_instance("earth")
    # Now let's call 'get_world_info' with the 'world' param explicitly
    ep_info = endpoints["get_world_info"]
    result = ep_info(WorldController(), world=w)
    assert result.label == "earth"
    assert result.name == "FakeWorld-earth"

    # 'unload_world'
    ep_unload = endpoints["unload_world"]
    # Because it tries `World.clear_instance(world.label)`, let's see if it works
    ep_unload(WorldController(), world=w)
    # Now 'earth' should no longer exist
    assert "earth" not in FakeWorld._instances


def test_preprocessor_dereference(monkeypatch):
    """
    The 'get_world_info' etc. has a preprocessor that calls
    `_dereference_world_id(world_id=...) -> world`.
    We'll simulate that by providing 'world_id'.
    """
    # We'll re-init the dictionary so we start fresh
    FakeWorld._instances.clear()
    # Just to confirm it's empty
    assert len(FakeWorld._instances) == 0

    c = WorldController()
    ep_info = c.get_api_endpoints()["get_world_info"]

    # The preprocessor expects 'world_id' and sets 'world' in kwargs
    result = ep_info(c, world_id="mars")
    assert result.label == "mars"  # from 'mars' instance
    assert result.name == "FakeWorld-mars"


def test_create_story_direct():
    """
    Test the 'create_story' method by calling it directly with a fake user
    and a fake world.
    """

    class FakeUser:
        def __init__(self, uid):
            self.uid = uid

    user = FakeUser(uid="user-1")
    w = FakeWorld.get_instance("someworld")

    c = WorldController()
    ep_create_story = c.get_api_endpoints()["create_story"]
    new_story = ep_create_story(c, world=w, user=user, some_arg="test")
    assert isinstance(new_story, FakeStory)
    assert new_story.uid == "story-someworld"
    assert new_story.user == user
