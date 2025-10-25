from typing import Generic, Callable, ClassVar
from uuid import UUID

from tangl.core.registry import Registry, VT
from .behavior_registry import BehaviorRegistry, HasBehaviors

# --- Hook decorator markers -----------------------------------------------
# We can't reliably call a classmethod decorator from the class body being defined.
# Instead, these factories just *tag* functions, and __init_subclass__ will
# discover the tags and register the behaviors on the concrete subclass.
def _make_hook_decorator(task: str, **default_attrs):
    def factory(**attrs):
        merged = {**default_attrs, **attrs}
        def decorator(func):
            marks = getattr(func, "_st_hook_marks_", [])
            marks.append({"task": task, **merged})
            setattr(func, "_st_hook_marks_", marks)
            return func
        return decorator
    return factory

class HookedRegistry(Registry, HasBehaviors, Generic[VT]):
    # This can quickly become a recursive issue, but let's allow registries
    # to register and apply behaviors on access.

    behavior_hooks: ClassVar[BehaviorRegistry] = BehaviorRegistry()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # fresh registry per subclass
        cls.behavior_hooks = BehaviorRegistry()
        # discover hook-marked callables declared on this subclass
        for name, obj in list(vars(cls).items()):
            # unwrap descriptors to raw function for tag lookup
            func = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
            marks = getattr(func, "_st_hook_marks_", None)
            if not marks:
                continue
            for mark in marks:
                task = mark.get("task")
                attrs = {k: v for k, v in mark.items() if k != "task"}
                # fill placeholders now that we have the concrete subclass
                if attrs.get("owner_cls") == "__CLASS__":
                    attrs["owner_cls"] = cls
                # delegate to behavior registry; it will infer handler_type/owner/caller_cls as needed
                cls.behavior_hooks.add_behavior(func, task=task, **attrs)

    # Class-level aliases usable inside subclass bodies:
    #   class MyReg(HookedRegistry[Foo]):
    #       @HookedRegistry.on_add()     # or just @on_add() if imported at module scope
    #       def handle_add(self, caller: Foo, ctx=None): ...
    on_add   = _make_hook_decorator("on_add",   handler_type="instance_on_owner", owner_cls="__CLASS__")
    on_remove= _make_hook_decorator("on_remove",handler_type="instance_on_owner", owner_cls="__CLASS__")
    on_get   = _make_hook_decorator("on_get",   handler_type="instance_on_owner", owner_cls="__CLASS__")

    def add(self, item: VT, extra_handlers: list[Callable] = None):
        self.behavior_hooks.dispatch_for(item, task="on_add", extra_handlers=extra_handlers)
        super().add(item)

    def remove(self, item: VT | UUID, extra_handlers: list[Callable] = None):
        if isinstance(item, UUID):
            item = super().get(item)  # skip the get handlers
        self.behavior_hooks.dispatch_for(item, task="on_remove", extra_handlers=extra_handlers)
        super().remove(item)

    def get(self, key: UUID, extra_handlers: list[Callable] = None):
        item = super().get(key)
        self.behavior_hooks.dispatch_for(item, task="on_get", extra_handlers=extra_handlers)
        return item
