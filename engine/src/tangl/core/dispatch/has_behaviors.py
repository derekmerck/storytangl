from __future__ import annotations
from typing import Type, Callable, Iterator, Iterable, ClassVar
import itertools
import logging

from pydantic import model_validator

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

from typing import ClassVar

class HasLocalBehaviors(HasBehaviors):

    # instance behaviors get stored here
    local_behaviors: ClassVar[BehaviorRegistry] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls.local_behaviors = BehaviorRegistry(
            label=f"local.dispatch.{cls.__name__.lower()}",
            handler_layer=L.LOCAL)
        cls._register_local_behaviors()

    @classmethod
    def register_local(cls, **attrs):
        def deco(func):
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
                if h.handler_layer in [HandlerType.INSTANCE_ON_CALLER, HandlerType.CLASS_ON_CALLER]:
                    h.caller_cls = cls
                cls.local_behaviors.add_behavior(h)


    # @model_validator(mode="after")
    # def _annotate_inst_behaviors(self):
    #     """
    #     (Planned) Annotate a *copy* of class behaviors for this instance, setting
    #     ``owner=self`` where appropriate. Left unimplemented pending a concrete
    #     registration strategy for instance‑bound behaviors.
    #     """
    #     # want to annotate and register a _copy_ of the instance (self, caller)
    #     # but _not_ class (cls, caller) behaviors with owner = self instead
    #     # of owner = cls
    #     return self