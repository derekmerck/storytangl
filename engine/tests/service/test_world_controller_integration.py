from uuid import uuid4

import pytest

from tangl.service.api_endpoints import ServiceManager, AccessLevel
from fake_types import FakeWorld


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

@pytest.fixture
def world_context():
    """
    Provide a dictionary simulating the 'context' for the service manager.
    Typically, we would store users, stories, etc.
    For the world logic, we might not need user/story in the context,
    unless you test the 'create_story' with a user.
    """
    return {
        # e.g. user_id: user_obj, or story_id: story_obj, ...
    }

@pytest.fixture
def world_service_manager(world_context):
    """
    Build a service manager that includes WorldController as a component.
    """
    from tangl.business.world import WorldController  # Adjust import
    mgr = ServiceManager(context=world_context, components=[WorldController])
    return mgr

def test_get_world_info_via_service_manager(world_service_manager):
    """
    Now we call 'WorldController.get_world_info' via the manager endpoints.
    We pass 'world_id' to simulate the client input.
    """
    key = "WorldController.get_world_info"
    assert key in world_service_manager.endpoints

    # No user_id required because it's public
    result = world_service_manager.endpoints[key](world_id="narnia")
    assert result.label == "narnia"
    assert result.name == "FakeWorld-narnia"

def test_unload_world_via_service_manager(world_service_manager):
    """
    Because 'unload_world' is restricted, we must pass a user_id with
    enough access level.
    We'll mock a user in the context to satisfy that requirement.
    """
    # Insert a user into the manager's context
    user_id = uuid4()
    user = type("FakeUser", (), {})()  # a minimal user
    user.uid = user_id
    user.access_level = AccessLevel.RESTRICTED
    world_service_manager.context[user_id] = user

    # create a test world
    from fake_types import FakeWorld
    w = FakeWorld.get_instance("grimdark")

    ep_key = "WorldController.unload_world"
    # call with user_id and world_id
    world_service_manager.endpoints[ep_key](user_id=user_id, world_id="grimdark")

    # ensure it's unloaded
    assert "grimdark" not in FakeWorld._instances

def test_create_story_via_service_manager(world_service_manager):
    """
    'create_story' is user-level. We'll add a user in context
    so that user_id is recognized.
    """
    user_id = uuid4()
    user = type("FakeUser", (), {})()
    user.uid = user_id
    user.access_level = AccessLevel.USER
    # store user
    world_service_manager.context[user_id] = user

    ep_key = "user.create_story"  # note the group is "user"
    # "create_story" is grouped as "user" in your code
    # => so the final name might be "WorldController.create_story" or "user.create_story"?
    # depends on how you set 'group' in the annotation.
    # We'll confirm by checking endpoints keys:

    # Let's see what we actually have:
    print("All endpoints:", world_service_manager.endpoints.keys())
    # Possibly it might be "WorldController.create_story" or "user.create_story".
    # Adjust as needed:
    if "WorldController.create_story" in world_service_manager.endpoints:
        ep_key = "WorldController.create_story"
    elif "user.create_story" in world_service_manager.endpoints:
        ep_key = "user.create_story"

    result = world_service_manager.endpoints[ep_key](user_id=user_id, world_id="ancient", extra="args")
    # Should return a FakeStory with uid = "story-ancient"
    assert result == "story-ancient"
    assert FakeWorld.get_instance(result)
