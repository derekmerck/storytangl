from typing import Any

import pytest

from tangl.service.api_endpoints import HasApiEndpoints, ApiEndpoint, MethodType, ResponseType, AccessLevel

# def test_api_endpoints_decorator():
#
#     c = MyController()
#     print(c.get_api_endpoints())
#     assert 'get_world_info' in c.get_api_endpoints()
#     print(c.get_world_info())
#     assert c.get_world_info() == {'hello': 'world', 'foo': 'bar'}
#     assert c.get_world_info._api_endpoint.group == "my"
#
#     assert len(c.get_world_info._api_endpoint.type_hints()) == 0
#     assert "data" in c.custom_create_something._api_endpoint.type_hints()


# -------------------------------------------------------------------
# 1. Fixtures & Sample Controller / Classes to Decorate
# -------------------------------------------------------------------

def dummy_preprocessor(*args, **kwargs):
    # do something trivial
    pass

def dummy_postprocessor(result):
    if isinstance(result, dict):
        result["postprocessed"] = True
    return result

class MyTestController(HasApiEndpoints):
    """
    A simple class with decorated endpoints to test the inference logic.
    """

    @ApiEndpoint.annotate()
    def get_something_info(self, item_id: str) -> dict[str, Any]:
        """Should be inferred as MethodType=READ, ResponseType=INFO."""
        return {"item_id": item_id, "data": "some info"}

    @ApiEndpoint.annotate()
    def create_something(self, data: dict) -> dict:
        """Should be inferred as MethodType=CREATE, ResponseType=RUNTIME."""
        return {"status": "created", **data}

    @ApiEndpoint.annotate()
    def drop_data(self, key: str) -> list:
        """Should be inferred as MethodType=DELETE, ResponseType=RUNTIME."""
        return [key]

    @ApiEndpoint.annotate(postprocessors=[dummy_postprocessor])
    def update_thing_content(self, content: str) -> dict:
        """
        Should be inferred as MethodType=UPDATE, ResponseType=RUNTIME.
        Also includes a postprocessor.
        """
        return {"content": content}

class ExplicitController(HasApiEndpoints):
    """
    Demonstrates overriding the method_type and response_type manually.
    """

    @ApiEndpoint.annotate(method_type=MethodType.CREATE, response_type=ResponseType.MEDIA)
    def load_foo_media(self, foo_id: str):
        """
        Normally 'load_foo_media' might get method_type=CREATE, response_type=RUNTIME,
        but we're explicitly overriding the response_type to MEDIA.
        """
        return f"MEDIA for {foo_id}"


# -------------------------------------------------------------------
# 2. Tests for Basic Inference & Execution
# -------------------------------------------------------------------

def test_basic_inference():
    """
    Verify that function name inference sets method_type & response_type
    as expected for MyTestController endpoints.
    """
    endpoints = MyTestController.get_api_endpoints()
    assert "get_something_info" in endpoints
    assert "create_something" in endpoints
    assert "drop_data" in endpoints
    assert "update_thing_content" in endpoints

    get_info_ep = endpoints["get_something_info"]
    assert get_info_ep.method_type == MethodType.READ
    assert get_info_ep.response_type == ResponseType.INFO
    assert get_info_ep.access_level == AccessLevel.RESTRICTED  # default

    create_ep = endpoints["create_something"]
    assert create_ep.method_type == MethodType.CREATE
    assert create_ep.response_type == ResponseType.RUNTIME

    drop_ep = endpoints["drop_data"]
    assert drop_ep.method_type == MethodType.DELETE
    assert drop_ep.response_type == ResponseType.RUNTIME

    update_ep = endpoints["update_thing_content"]
    assert update_ep.method_type == MethodType.UPDATE
    assert update_ep.response_type == ResponseType.RUNTIME


def test_call_api_endpoint():
    """
    Test actually calling the endpoints and verifying the return values,
    including postprocessor usage.
    """
    controller = MyTestController()

    # read info
    ep_get_info = controller.get_api_endpoints()["get_something_info"]
    result = ep_get_info(controller, item_id="abc123")
    assert result == {"item_id": "abc123", "data": "some info"}

    # create something
    ep_create = controller.get_api_endpoints()["create_something"]
    out = ep_create(controller, data={"foo": "bar"})
    assert out["status"] == "created"
    assert out["foo"] == "bar"

    # drop data
    ep_drop = controller.get_api_endpoints()["drop_data"]
    to_delete = ep_drop(controller, "mykey")
    assert to_delete == ["mykey"]

    # update with postprocessor
    ep_update = controller.get_api_endpoints()["update_thing_content"]
    updated = ep_update(controller, content="XYZ")
    assert updated["content"] == "XYZ"
    # postprocessor adds "postprocessed": True
    assert updated["postprocessed"] is True

def test_explicit_overrides():
    """
    Check that method_type and response_type can be overridden manually.
    """
    endpoints = ExplicitController.get_api_endpoints()
    assert "load_foo_media" in endpoints

    ep = endpoints["load_foo_media"]
    assert ep.method_type == MethodType.CREATE   # explicit
    assert ep.response_type == ResponseType.MEDIA  # explicit

    # Actually call it
    ret = ep(ExplicitController(), "my_foo_id")
    assert ret == "MEDIA for my_foo_id"

def test_bad_inference():
    """
    This should raise ValueError because `unknown_operation` does not
    match any recognized prefix to infer the method_type.
    """
    # The error occurs during the validation for the decorated function,
    # so let's define a bad class in a try block:
    with pytest.raises(ValueError, match="Unable to infer method type from: unknown_operation"):

        class BadController(HasApiEndpoints):
            """
            Controller with a function name that doesn't match any known pattern,
            which should raise ValueError in metadata inference.
            """

            @ApiEndpoint.annotate()
            def unknown_operation(self):
                """No prefix like get_, create_, drop_, update_, so should fail."""

        BadController.get_api_endpoints()


# -------------------------------------------------------------------
# 3. Test Type Hints & Param Reflection
# -------------------------------------------------------------------

def test_type_hints():
    endpoints = MyTestController.get_api_endpoints()
    ep = endpoints["get_something_info"]
    hints = ep.type_hints()
    # Example: {'item_id': <class 'str'>, 'return': typing.Dict[str, typing.Any]}
    assert "item_id" in hints
    assert hints["item_id"] == str
    assert "return" in hints

    # Another example
    ep_create = endpoints["create_something"]
    hints2 = ep_create.type_hints()
    # e.g., {'data': <class 'dict'>, 'return': <class 'dict'>}
    assert "data" in hints2
    assert hints2["data"] == dict


# -------------------------------------------------------------------
# 4. Test Pre/Post-Processors More Explicitly
# -------------------------------------------------------------------

def test_pre_postprocessors():
    """
    Example of a new decorated function that uses both pre and post processors.
    """
    logs = []

    def my_preprocessor(*args, **kwargs):
        logs.append(("pre", args, kwargs))

    def my_postprocessor(result):
        logs.append(("post", result))
        return {"wrapped": result}

    class ProcessorController(HasApiEndpoints):
        @ApiEndpoint.annotate(preprocessors=[my_preprocessor],
                              postprocessors=[my_postprocessor])
        def get_info_stuff(self, x: int) -> dict:
            return {"value": x}

    ep = ProcessorController.get_api_endpoints()["get_info_stuff"]
    out = ep(ProcessorController(), 99)

    # Check the logs
    assert logs[0][0] == "pre"
    assert logs[0][1][1] == 99
    # no "x" in kwargs because user didn't pass as named kwarg
    assert logs[1][0] == "post"
    assert logs[1][1] == {"value": 99}

    # Return should be {"wrapped": {"value": 99}}
    assert out == {"wrapped": {"value": 99}}

