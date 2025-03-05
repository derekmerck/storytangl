import pytest
from uuid import uuid4, UUID
from typing import Dict, Any

from tangl.service.api_endpoints import ServiceManager, AccessLevel, MethodType, ApiEndpoint, HasApiEndpoints


# -------------------------------------------------------------------
# 1) Fake Classes for Testing
# -------------------------------------------------------------------

class FakeUser:
    def __init__(self, uid, access_level=AccessLevel.USER, current_story_id=None):
        self.uid = uid
        self.access_level = access_level
        self.current_story_id = current_story_id
        self.story_ids = []

    def add_story(self, story_id):
        self.story_ids.append(story_id)
        self.current_story_id = story_id

class FakeStory:
    def __init__(self, uid, user=None):
        self.uid = uid
        self.user = user  # might be a FakeUser or just user_id


# -------------------------------------------------------------------
# 2) Sample Controller to Register with ServiceManager
# -------------------------------------------------------------------

class MyController(HasApiEndpoints):
    """
    This controller simulates typical create/read/update/delete methods
    that require either a 'user' or a 'story' or are 'public'.
    """

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC)
    def get_public_info(self) -> str:
        """Public method that doesn't require a user."""
        return "public_data"

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def get_user_info(self, user: "FakeUser") -> dict:
        """READ method that requires user_id to open user."""
        return {"user_uid": user.uid, "level": user.access_level}

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def create_story_for_user(self, user: "FakeUser", data: dict) -> "FakeStory":
        """CREATE method that requires user_id. Returns a new story object."""
        # We'll mock a new story
        new_story_id = uuid4()
        story = FakeStory(uid=new_story_id, user=user)
        user.add_story(new_story_id)
        return story

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def drop_user_data(self, user: "FakeUser") -> list:
        """DELETE method that returns item_ids to remove from context."""
        # Suppose we remove the user and all their stories
        return [user.uid] + user.story_ids

    @ApiEndpoint.annotate(access_level=AccessLevel.USER)
    def update_story_content(self, story: "FakeStory", content: str) -> dict:
        """UPDATE method that modifies story data, then returns some result."""
        # For simplicity, store content in a dict
        return {"story_uid": story.uid, "updated_content": content}


# -------------------------------------------------------------------
# 3) Pytest Tests for ServiceManager
# -------------------------------------------------------------------

@pytest.fixture
def basic_context():
    """Set up a dictionary with a user and story references."""
    user_id = uuid4()
    user = FakeUser(uid=user_id, access_level=AccessLevel.USER, current_story_id=None)

    # Another user with lower access
    public_user_id = uuid4()
    public_user = FakeUser(uid=public_user_id, access_level=AccessLevel.PUBLIC)

    # Add them to the context
    return {
        user_id: user,
        public_user_id: public_user,
        # we add stories dynamically if created
    }


@pytest.fixture
def service_manager(basic_context):
    """Create a ServiceManager with MyController as a component."""
    mgr = ServiceManager(context=basic_context, components=[MyController])
    return mgr


def test_public_method_no_user_required(service_manager):
    """
    Test calling a public endpoint with no user_id required.
    """
    # The endpoint name is MyController.get_public_info
    endpoint_key = "MyController.get_public_info"
    assert endpoint_key in service_manager.endpoints

    # This is a public method, so we don't pass user_id
    result = service_manager.endpoints[endpoint_key]()
    assert result == "public_data"


def test_read_user_info_ok(service_manager):
    """
    Test a read method (get_user_info) with an existing user.
    """
    # We'll pick a user_id from context
    some_user_id = next(iter(service_manager.context.keys()))  # just pick one

    endpoint_key = "MyController.get_user_info"
    result = service_manager.endpoints[endpoint_key](user_id=some_user_id)
    assert "user_uid" in result
    assert result["user_uid"] == some_user_id


def test_read_user_info_missing_user_id(service_manager):
    """
    If we call get_user_info without user_id, we should get a ValueError.
    """
    endpoint_key = "MyController.get_user_info"
    with pytest.raises(ValueError, match="user_id is required"):
        service_manager.endpoints[endpoint_key]()


def test_create_story_for_user(service_manager):
    """
    Test a create method that returns a new story object and adds it to context.
    """
    endpoint_key = "MyController.create_story_for_user"
    user_id = next(iter(service_manager.context.keys()))  # pick one
    assert endpoint_key in service_manager.endpoints

    # Let's call the create method with some data
    new_story = service_manager.endpoints[endpoint_key](user_id=user_id, data={"title": "A Great Tale"})

    # The create method returns a FakeStory object (with a fresh uid)
    assert isinstance(new_story, UUID)
    # The new story should be in the context now
    story_uid = new_story
    assert story_uid in service_manager.context
    # The story's user is unlinked before storing, so new_story.user is user.uid?
    # Actually your code modifies new_story.user = new_story.user.uid if it finds .user
    # So let's check:
    new_story = service_manager.context[story_uid]
    assert new_story.user == user_id

    # The user in context should have that story in story_ids
    user_obj = service_manager.context[user_id]
    assert story_uid in user_obj.story_ids


def test_delete_user_data(service_manager):
    """
    Test a DELETE method that returns item_ids to remove from context.
    """
    endpoint_key = "MyController.drop_user_data"
    user_id = next(iter(service_manager.context.keys()))

    # Let's add a story to that user so we can see it removed
    user_obj = service_manager.context[user_id]
    story_id = uuid4()
    fake_story = FakeStory(story_id, user=user_id)
    service_manager.context[story_id] = fake_story
    user_obj.add_story(story_id)

    # Now call drop_user_data
    result = service_manager.endpoints[endpoint_key](user_id=user_id)
    # The result should be the IDs to remove
    assert story_id in result
    assert user_id in result

    # The manager code removes them from context after the function returns
    assert user_id not in service_manager.context
    assert story_id not in service_manager.context


def test_update_story_content(service_manager):
    """
    Test an update method that modifies a story for a user and returns some result.
    """
    # We create a user and a story in context
    user_id = next(iter(service_manager.context.keys()))
    user_obj = service_manager.context[user_id]
    st_id = uuid4()
    fake_story = FakeStory(st_id, user=user_id)
    service_manager.context[st_id] = fake_story
    user_obj.add_story(st_id)

    endpoint_key = "MyController.update_story_content"
    updated = service_manager.endpoints[endpoint_key](user_id=user_id, content="Hello World")
    assert updated["story_uid"] == st_id
    assert updated["updated_content"] == "Hello World"


def test_user_acl_check_fail(service_manager):
    """
    If the user in context has too low an access level for a restricted method,
    we should get RuntimeError.
    """

    # Let's define another method in MyController that requires RESTRICTED or something
    class ACLController(HasApiEndpoints):
        @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED)
        def get_secret_info(self, user: "FakeUser"):
            return {"secret": "for restricted eyes only"}

    # We'll add ACLController to the existing manager
    service_manager.add_component(ACLController)

    # pick a user with USER or PUBLIC
    user_id = next(iter(service_manager.context.keys()))
    user_obj = service_manager.context[user_id]
    user_obj.access_level = AccessLevel.USER  # not restricted

    ep_key = "ACLController.get_secret_info"
    # Try calling it
    with pytest.raises(RuntimeError, match="User acl .* exceeds method acl"):
        service_manager.endpoints[ep_key](user_id=user_id)


def test_acl_only_method(service_manager):
    """
    If the method has access_level > PUBLIC but doesn't take a user or story param,
    we must still pass user_id for ACL check.
    """

    class ACLOnlyController(HasApiEndpoints):
        @ApiEndpoint.annotate(access_level=AccessLevel.USER)
        def do_system_task(self) -> str:
            return "sys_task_done"

    service_manager.add_component(ACLOnlyController)
    ep_key = "ACLOnlyController.do_system_task"

    # If we call without user_id -> ValueError
    with pytest.raises(ValueError, match="user_id is required for do_system_task"):
        service_manager.endpoints[ep_key]()

    # Pass a user with enough level
    user_id = next(iter(service_manager.context.keys()))
    user_obj = service_manager.context[user_id]
    user_obj.access_level = AccessLevel.USER

    result = service_manager.endpoints[ep_key](user_id=user_id)
    assert result == "sys_task_done"
