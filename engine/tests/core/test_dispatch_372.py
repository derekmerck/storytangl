from __future__ import annotations
from typing import Any, Self

from tangl.core import Entity, CallReceipt
from tangl.core.dispatch.behavior import Behavior, HandlerLayer, HandlerType
from tangl.core.dispatch.behavior_registry import BehaviorRegistry

# --------------------------
# Binding patterns

# There are 5 cases and 3 unique signature patterns and require different bindings.

global_behaviors = BehaviorRegistry(handler_layer=HandlerLayer.GLOBAL)
# no default task or selectors

def static_do_global(caller, *args, **kwargs) -> Any:
    ...

global_behaviors.add_behavior(
    static_do_global,
    handler_type=HandlerType.STATIC,
    task="my_task")
# can we infer that it's a non-class bound defined func?

on_task = BehaviorRegistry(handler_layer=HandlerLayer.APPLICATION, task="my_task")

def static_do_something(caller: Tasker, *args, **kwargs):
    ...

on_task.add_behavior(static_do_something, handler_type=HandlerType.STATIC)

class Tasker(Entity):

    def inst_do_something(self, *args, **kwargs) -> Any:
        ...

    @classmethod
    def cls_do_something(cls, caller: Self, *args, **kwargs) -> Any:
        ...

on_task.add_behavior(Tasker.inst_do_something, handler_type=HandlerType.INSTANCE_ON_CALLER)
on_task.add_behavior(Tasker.cls_do_something, handler_type=HandlerType.CLASS_ON_CALLER)

class TaskManager(Entity):

    def mgr_do_something(self, caller: Tasker, *args, **kwargs) -> Any:
        ...

    @classmethod
    def mgr_cls_do_something(cls, caller: Tasker, *args, **kwargs) -> Any:
        ...

mgr = TaskManager()

# Owner class != caller class
# in this case, we need to track the owner/self for binding
on_task.add_behavior(
    TaskManager.mgr_do_something,
    owner=mgr,
    handler_type=HandlerType.INSTANCE_ON_OWNER,
    owner_cls=Tasker)

# in this case, we can infer the owner class and bind automatically, need caller class separately
on_task.add_behavior(
    TaskManager.mgr_cls_do_something,
    handler_type=HandlerType.CLASS_ON_OWNER,
    owner_cls=Tasker)

# inherits task from registry, infers instance defined and caller class from func name?


def test_binding_patterns() -> None:
    inst = Tasker()

    receipts = BehaviorRegistry.chain_dispatch(global_behaviors, on_task, caller=inst, task="my_task")

    # should select and call all tasks
    first_result = CallReceipt.gather_results(*receipts)
    print(first_result)


