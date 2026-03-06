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


class HasClassBehaviors(HasBehaviors):

    # instance behaviors get stored here
    cls_behaviors: ClassVar[BehaviorRegistry] = BehaviorRegistry(
        label="local.dispatch.cls.has_cls_behaviors",
        handler_layer=L.LOCAL)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        # In this case, we give each class its own local behavior registry,
        # same thinking around Singleton._instances subclass vars applies.
        cls.cls_behaviors = BehaviorRegistry(
            label=f"local.dispatch.cls.{cls.__name__.lower()}",
            handler_layer=L.LOCAL)
        cls._register_cls_behaviors()

    @classmethod
    def register_cls_behavior(cls, **attrs):
        def deco(func):
            # stash attrs on _local_behavior for later
            func._cls_behavior = attrs
            return func
        return deco

    @classmethod
    def _register_cls_behaviors(cls):
        for item in cls.__dict__.values():
            if hasattr(item, "_cls_behavior"):
                logger.debug("Registering class local behaviors")
                h = Behavior(func=item,
                             owner_cls=cls,
                             **item._cls_behavior)
                if h.handler_type in [HandlerType.INSTANCE_ON_CALLER, HandlerType.CLASS_ON_CALLER]:
                    h.caller_cls = cls
                cls.cls_behaviors.add_behavior(h)
                item._cls_behavior = h

class HasLocalBehaviors(HasBehaviors):
    """
    Warning:  If you use this as a mixin, the object will _not_ be serializable!
    """

    local_behaviors: BehaviorRegistry = Field(default_factory=BehaviorRegistry)

    @model_validator(mode="after")
    def _update_local_behavior_label(self):
        if self.local_behaviors:
            label = f"local.dispatch.inst.{self.get_label().lower()}"
            self.local_behaviors.label = label
        return self

    def register_local_behavior(self: Self, **attrs):
        """
        >> a.register_local_behavior()
        >> def foo(caller, *, ctx):
        >>    ...
        """
        def deco(func):
            b = Behavior(func=func,
                         owner=self,
                         handler_type=HandlerType.INSTANCE_ON_OWNER,
                         **attrs)
            self.local_behaviors.add_behavior(b)
            # Let's not bother for now ...
            # Want to stash a pointer to the handler on the func, but
            # instance on owner can have many owners, so use a map
            # if not hasattr(func, "_local_behaviors"):
            #     func._local_behaviors = {}
            # func._local_behaviors[self.uid] = b
            return func

        return deco

    def unstructure(self):
        # Alternatively, we could declare any locals to be ephemeral and
        # discard them if we try to serialize the object. But easier to just fail.
        raise RuntimeError("Entities using the HasLocalBehaviors mixin cannot be unstructured")
