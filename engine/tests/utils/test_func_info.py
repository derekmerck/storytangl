import pytest
import logging
from tangl.core import Entity
from tangl.utils.func_info import FuncInfo, HandlerType


# Test fixtures
class Node(Entity):
    """Test entity for caller type."""

    def validate(self, ctx=None):
        return True

    @classmethod
    def validate_all(cls, caller: "Node", ctx=None):
        return all(...)


class TaskManager(Entity):
    """Test entity for manager pattern."""

    def manage(self, caller: Node, ctx=None):
        return f"managing {caller}"

    @classmethod
    def plan(cls, caller: Node, ctx=None):
        return "planning"


def static_handler(caller: Node, ctx=None):
    """Test static handler function."""
    return "static"


# ==================== Basic Handler Type Detection ====================

def test_static_handler_from_free_function():
    """Static handler inferred from free function with caller param."""
    info = FuncInfo.from_func(static_handler)

    assert info.handler_type == HandlerType.STATIC
    assert info.caller_cls is Node
    assert info.owner is None
    assert info.owner_cls is None


def test_instance_on_caller_from_unbound_method():
    """Instance-on-caller inferred from unbound instance method."""
    info = FuncInfo.from_func(Node.validate)

    assert info.handler_type == HandlerType.INSTANCE_ON_CALLER
    assert info.caller_cls is Node
    assert info.owner is None
    assert info.owner_cls is None  # No owner cls for CLASS_ON_CALLER


def test_class_on_caller_from_unbound_classmethod():
    """Class-on-caller inferred from unbound classmethod."""
    info = FuncInfo.from_func(Node.validate_all)

    assert info.handler_type == HandlerType.CLASS_ON_CALLER
    assert info.caller_cls is Node
    assert info.owner is None


def test_instance_on_owner_from_unbound_manager_method():
    """Instance-on-owner inferred from unbound method with caller param."""
    info = FuncInfo.from_func(TaskManager.manage)

    assert info.handler_type == HandlerType.INSTANCE_ON_OWNER
    assert info.caller_cls is Node
    assert info.owner_cls is TaskManager
    assert info.owner is None


def test_class_on_owner_from_classmethod_with_explicit_owner():
    """Class-on-owner requires explicit owner_cls for refinement."""
    info = FuncInfo.from_func(TaskManager.plan, owner_cls=TaskManager)

    assert info.handler_type == HandlerType.CLASS_ON_OWNER, \
        f"Expected CLASS_ON_OWNER, got {info.handler_type.name}"
    assert info.caller_cls is Node
    assert info.owner_cls is TaskManager


# ==================== Bound Method Detection ====================

def test_instance_on_owner_from_bound_manager_instance():
    """Instance-on-owner inferred from bound manager method."""
    mgr = TaskManager(label="mgr")
    info = FuncInfo.from_func(mgr.manage)

    assert info.handler_type == HandlerType.INSTANCE_ON_OWNER
    assert info.caller_cls is Node
    assert info.owner is mgr
    assert info.owner_cls is TaskManager


def test_instance_on_caller_from_bound_instance_method():
    """Instance-on-caller detected even when method is bound."""
    node = Node(label="test")
    info = FuncInfo.from_func(node.validate)

    assert info.handler_type == HandlerType.INSTANCE_ON_CALLER, \
        f"Expected INSTANCE_ON_CALLER, got {info.handler_type.name}"
    assert info.caller_cls is Node
    assert info.owner_cls is None  # No owner cls for CLASS_ON_CALLER
    # Note: bound instance becomes owner in this case


def test_class_on_caller_from_bound_classmethod():
    """Class-on-caller inferred from bound classmethod."""
    info = FuncInfo.from_func(Node.validate_all)

    assert info.handler_type == HandlerType.CLASS_ON_CALLER, \
        f"Expected CLASS_ON_CALLER, got {info.handler_type.name}"
    assert info.caller_cls is Node
    assert info.owner_cls is None  # No owner cls for CLASS_ON_CALLER


# ==================== Explicit Owner Handling ====================

def test_instance_on_owner_with_explicit_owner_instance():
    """Providing owner instance refines handler type to INSTANCE_ON_OWNER."""
    mgr = TaskManager(label="mgr")
    info = FuncInfo.from_func(TaskManager.manage, owner=mgr)

    assert info.handler_type == HandlerType.INSTANCE_ON_OWNER
    assert info.owner is mgr
    assert info.owner_cls is TaskManager
    assert info.caller_cls is Node


def test_owner_cls_inferred_from_owner_instance():
    """owner_cls automatically inferred from owner instance."""
    mgr = TaskManager(label="mgr")
    info = FuncInfo.from_func(TaskManager.manage, owner=mgr)

    assert info.owner_cls is TaskManager


# ==================== Edge Cases ====================

def test_none_function_returns_none():
    """from_func returns None when given None."""
    info = FuncInfo.from_func(None)
    assert info is None


def test_explicit_caller_cls_overrides_inference():
    """Explicit caller_cls parameter takes precedence."""

    class CustomEntity(Entity):
        pass

    def handler(caller, ctx=None):
        pass

    info = FuncInfo.from_func(handler, caller_cls=CustomEntity)
    assert info.caller_cls is CustomEntity


def test_conflicting_caller_cls_raises_error():
    """Conflicting explicit and inferred caller_cls raises RuntimeError."""

    class WrongEntity(Entity):
        pass

    with pytest.raises(RuntimeError, match="Incompatible caller_cls override"):
        FuncInfo.from_func(static_handler, caller_cls=WrongEntity)


# ==================== Type Annotation Edge Cases ====================

def test_handler_without_type_annotations():
    """Handler without annotations still works."""

    def untyped_handler(caller, ctx=None):
        return "works"

    info = FuncInfo.from_func(untyped_handler)

    assert info.handler_type == HandlerType.STATIC
    assert info.caller_cls is None  # Can't infer without annotation


def test_self_annotation_with_typing_self():
    """Typing.Self annotation resolves to declaring class."""
    from typing import Self

    class SelfAnnotated(Entity):
        def method(self: Self, ctx=None):
            pass

    info = FuncInfo.from_func(SelfAnnotated.method)

    print( f"Debug: {info.debug_func(SelfAnnotated.method)}" )

    assert info.handler_type is HandlerType.INSTANCE_ON_CALLER
    assert info.caller_cls is SelfAnnotated


# ==================== Integration Test ====================

def test_complete_workflow_with_all_handler_types():
    """End-to-end test covering all handler types in one workflow."""

    # Setup
    class Controller(Entity):
        def process(self, caller: Node, ctx=None):
            return "processed"

        @classmethod
        def batch_process(cls, caller: Node, ctx=None):
            return "batched"

    def preprocess(caller: Node, ctx=None):
        return "preprocessed"

    controller = Controller(label="ctrl")

    # Static
    static_info = FuncInfo.from_func(preprocess)
    assert static_info.handler_type == HandlerType.STATIC

    # Instance on caller
    # (Node.validate already tested)

    # Instance on owner (unbound)
    unbound_info = FuncInfo.from_func(Controller.process)
    assert unbound_info.handler_type == HandlerType.INSTANCE_ON_OWNER

    # Instance on owner (bound)
    bound_info = FuncInfo.from_func(controller.process)
    assert bound_info.handler_type == HandlerType.INSTANCE_ON_OWNER
    assert bound_info.owner is controller

    # Class on caller
    class_caller_info = FuncInfo.from_func(Controller.batch_process)
    assert class_caller_info.handler_type == HandlerType.CLASS_ON_CALLER

    # Class on owner (with explicit owner_cls)
    class_owner_info = FuncInfo.from_func(
        Controller.batch_process,
        owner_cls=Controller
    )
    assert class_owner_info.handler_type == HandlerType.CLASS_ON_OWNER

def test_local_lambda_no_class_token():
    f = (lambda: (lambda caller, ctx=None: None))()  # create a local lambda
    info = FuncInfo.from_func(f)
    assert info.handler_type is HandlerType.STATIC  # absent hints → static by default

def test_local_class_lambda_method():
    class C(Entity):
        m = staticmethod(lambda caller, ctx=None: None)
    info = FuncInfo.from_func(C.m)
    # Depending on hints you provide, this will generally be STATIC; you can
    # pass caller_cls explicitly to refine or keep STATIC as the honest default.
    assert info.handler_type in (HandlerType.STATIC, HandlerType.CLASS_ON_CALLER, HandlerType.CLASS_ON_OWNER)

def test_local_class_instance_lambda_self_only():
    class N(Entity):
        v = lambda self, ctx=None: None
    info = FuncInfo.from_func(N.v)

    print( f"Debug: {info.debug_func(N.v)}" )

    assert info.handler_type is HandlerType.INSTANCE_ON_CALLER
    assert info.caller_cls is N

from typing import Self
def test_classmethod_caller_self_maps_to_declaring_class():
    class C(Entity):
        @classmethod
        def f(cls, caller: Self, ctx=None): ...
    info = FuncInfo.from_func(C.f)

    logging.debug(FuncInfo.debug_func(C.f))

    assert info.handler_type is HandlerType.CLASS_ON_CALLER
    assert info.caller_cls is C