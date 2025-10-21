from typing import Generic, Callable, ClassVar
from uuid import UUID

from tangl.core.registry import Registry, VT
from tangl.core.dispatch.dispatch_v37 import BehaviorRegistry, HasBehaviors

class HookedRegistry(Registry, HasBehaviors, Generic[VT]):
    # This can quickly become a recursive issue, but let's allow registries
    # to register and apply behaviors on access.

    behavior_hooks: ClassVar[BehaviorRegistry] = BehaviorRegistry()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.behavior_hooks = BehaviorRegistry()

    @classmethod
    def on_add(cls, **attrs):
        # decorator alias for register(task=on_add)
        # @HookedRegistry.on_add(**attrs)(cls_method)
        attrs['task'] = "on_add"
        attrs['owner_cls'] = cls
        attrs['caller_cls'] = VT
        attrs['handler_type'] = "instance_on_owner"
        return cls.behavior_hooks.register(**attrs)

    @classmethod
    def on_remove(cls, **attrs):
        # decorator alias for register(task=on_remove)
        attrs['task'] = "on_remove"
        attrs['owner_cls'] = cls
        attrs['caller_cls'] = VT
        attrs['handler_type'] = "instance_on_owner"
        cls.behavior_hooks.register_behavior(**attrs)

    @classmethod
    def on_get(cls, **attrs):
        # decorator alias for register(task=on_get)
        attrs['task'] = "on_get"
        attrs['owner_cls'] = cls
        attrs['caller_cls'] = VT
        attrs['handler_type'] = "instance_on_owner"
        cls.behavior_hooks.register_behavior(**attrs)

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
