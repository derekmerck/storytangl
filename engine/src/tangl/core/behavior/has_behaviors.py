# tangl/core/behavior/has_behaviors.py
from __future__ import annotations
from typing import ClassVar, Self
import logging

from pydantic import Field, model_validator

from tangl.core import Entity
from .behavior import HandlerType, Behavior
from .behavior_registry import BehaviorRegistry, HandlerLayer as L

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class HasBehaviors(Entity):
    """
    Mixin for classes that define and auto‑annotate behaviors.

    During class creation, :meth:`__init_subclass__` annotates any functions that
    were decorated via :meth:`BehaviorRegistry.register` with ``owner_cls=cls``.
    Instance‑level annotation can be added in :meth:`_annotate_inst_behaviors`.
    """
    # Use mixin or call `_annotate` in `__init_subclass__` for a class
    # with registered behaviors

    @classmethod
    def _annotate_behaviors(cls):
        """
        Attach ``owner_cls=cls`` to behaviors declared on this class and
        ``caller_cls=cls`` to inst or cls on caller  handler types.
        """
        logger.debug(f"Behaviors annotated on class {cls.__name__}")
        # annotate handlers defined in this cls with the owner_cls
        for name, obj in cls.__dict__.items():
            h = getattr(obj, "_behavior", None)  # type: Behavior
            if h is not None:
                logger.debug(f"Handler owner set for {h}")
                h.owner_cls = cls
                if h.handler_type in [HandlerType.INSTANCE_ON_CALLER, HandlerType.CLASS_ON_CALLER]:
                    logger.debug(f"Handler caller cls set for {h}")
                    h.caller_cls = cls

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Ensure behavior annotations are applied when the subclass is created.
        """
        super().__init_subclass__(**kwargs)
        cls._annotate_behaviors()


class HasLocalBehaviors(HasBehaviors):

    # instance behaviors get stored here
    local_behaviors: ClassVar[BehaviorRegistry] = BehaviorRegistry(
        label="local.dispatch.haslocalbehaviors",
        handler_layer=L.LOCAL)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        # In this case, we give each class its own local behavior registry,
        # same thinking around Singleton._instances subclass vars applies.
        cls.local_behaviors = BehaviorRegistry(
            label=f"local.dispatch.{cls.__name__.lower()}",
            handler_layer=L.LOCAL)
        cls._register_local_behaviors()

    @classmethod
    def register_local(cls, **attrs):
        def deco(func):
            # stash attrs on _local_behavior for later
            func._local_behavior = attrs
            return func
        return deco

    @classmethod
    def _register_local_behaviors(cls):
        for item in cls.__dict__.values():
            if hasattr(item, "_local_behavior"):
                logger.debug("Registering local behaviors")
                h = Behavior(func=item,
                             owner_cls=cls,
                             **item._local_behavior)
                if h.handler_type in [HandlerType.INSTANCE_ON_CALLER, HandlerType.CLASS_ON_CALLER]:
                    h.caller_cls = cls
                cls.local_behaviors.add_behavior(h)
                item._local_behavior = h

class HasInstanceBehaviors(HasBehaviors):

    instance_behaviors: BehaviorRegistry = None

    @model_validator(mode="after")
    def _create_instance_behaviors(self):
        if self.instance_behaviors is None:
            self.instance_behaviors = BehaviorRegistry(
                label=f"local.dispatch.{self.get_label().lower()}",
                handler_layer=L.LOCAL
            )
        return self

    def register_instance_behavior(self: Self, **attrs):
        """
        >> a.register_instance_behavior()
        >> def foo(caller, *, ctx):
        >>    ...
        """
        def deco(func):
            b = Behavior(func=func,
                         owner=self,
                         handler_type=HandlerType.INSTANCE_ON_OWNER,
                         **attrs)
            self.instance_behaviors.add_behavior(b)
            # Want to stash a pointer to the handler on the func, but
            # instance on owner can have many owners, so use a map
            if not hasattr(func, "_instance_behavior"):
                func._instance_behavior = {}
            func._instance_behavior[self.uid] = b
            return func

        return deco
