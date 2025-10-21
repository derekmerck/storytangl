# tangl/core/dispatch/behavior_registry.py
"""Behavior Registry - dispatch version 37.2"""
from __future__ import annotations
from typing import Type, Callable, Iterator, Iterable
import itertools
import logging

from pydantic import model_validator

from tangl.core import Entity, Registry
from tangl.core.entity import Selectable
from tangl.core.registry import _chained_registries
from .behavior import HandlerType, Behavior, HandlerLayer, HandlerPriority
from .call_receipt import CallReceipt

logger = logging.getLogger(__name__)

# ----------------------------
# Registry/Dispatch

class BehaviorRegistry(Selectable, Registry[Behavior]):
    """
    Behavior registry
    -----------------
    Ordered, queryable collection of :class:`~tangl.core.dispatch.behavior.Behavior`.
    Provides convenience helpers to register callables and execute matching
    handlers as a pipeline, yielding :class:`~tangl.core.dispatch.call_receipt.CallReceipt`.

    "It's like CSS specificity, but for narrative mechanics."

    A registry can represent a single task/phase, or a single layer (global, app, author),
    or provide a mix.

    Calling dispatch will filter handlers for criteria (i.e., phase/task) and then filter
    for a selector, the calling entity.  Selection criteria is handled similarly to
    css specificity, where more specific/closer/earlier behavior definitions have priority,
    and are run _last_ so they can inspect or clobber prior results.
    """
    # defaults
    handler_layer: HandlerLayer | int = HandlerLayer.GLOBAL
    task: str = None

    def add_behavior(self, item, *,
                     priority: HandlerPriority = HandlerPriority.NORMAL,
                     # These params are optional hints for FuncInfo, don't set defaults
                     handler_type: HandlerType = None,
                     owner: Entity | None = None,
                     owner_cls: Type[Entity] | None = None,
                     caller_cls: Type[Entity] | None = None,
                     **attrs):
        """
        Register a callable or Behavior into this registry.

        Hints (handler_type, owner, caller_cls) are optional; missing pieces
        are inferred by Behavior/FuncInfo at model-validate time. We always set
        origin=self so layer/task metadata and origin distance are available.
        """
        if isinstance(item, Behavior):
            if item.origin is None:
                item.origin = self
            self.add(item)
            return

        if isinstance(item, Callable):
            payload = dict(attrs)
            if handler_type is not None:
                payload["handler_type"] = handler_type
            if caller_cls is not None:
                payload["caller_cls"] = caller_cls
            if owner is not None:
                payload["owner"] = owner  # instance; Behavior will normalize/weakref
            if owner_cls is not None:
                payload["owner_cls"] = owner_cls

            h = Behavior(func=item,
                         priority=priority,
                         origin=self,
                         **payload)
            self.add(h)
            return

        raise ValueError(f"Unknown behavior type {type(item)}")

    def register(self, **attrs):
        # returns a decorator that creates and registers the handler and
        # leaves a _behavior attrib bread crumb for `HasHandlers._annotate_behaviors`
        def deco(func):
            h = Behavior(func=func, origin=self, **attrs)
            self.add(h)
            func._behavior = h
            return func
        return deco

    @staticmethod
    def _iter_normalize_handlers(handlers: Iterable[Behavior | Callable]) -> Iterator[Behavior]:
        for h in handlers or []:
            if isinstance(h, Behavior):
                yield h
            elif isinstance(h, Callable):
                yield Behavior(func=h, task=None)

    def dispatch(self, caller: Entity, *, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task
        behaviors = self.select_all_for(selector=caller, **inline_criteria)

        # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
        if extra_handlers:
            behaviors = itertools.chain(behaviors, self._iter_normalize_handlers(extra_handlers))

        behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        logger.debug(f"Behaviors: {[b.sort_key() for b in behaviors]}")
        return (b(caller, ctx=ctx) for b in behaviors)

    @classmethod
    def chain_dispatch(cls, *registries: BehaviorRegistry, caller, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found both 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task

        behaviors = cls.chain_select_all_for(*registries, selector=caller, **inline_criteria)
        # could also treat this as an ephemeral registry and add it onto the registry
        # stack and sort while filtering, but it seems clearer to copy the
        # single-registry-dispatch code.
        if extra_handlers:
            behaviors = itertools.chain(behaviors, cls._iter_normalize_handlers(extra_handlers))
        with _chained_registries(registries):  # provide registries for origin_dist sort key
            behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        return (b(caller, ctx=ctx) for b in behaviors)

    def iter_dispatch(self, *args, **kwargs) -> Iterator[CallReceipt]:
        raise NotImplementedError()
        # We could return an iterator of handler calls that each produce a receipt:
        return (lambda: b(caller, ctx) for b in behaviors)
        # Or we could return an iterator of job receipts with lambda functions as result
        return (b.partial_receipt(caller, ctx) for b in behaviors)
        # Probably want a iter_chain_dispatch() as well for symmetry

    def all_tasks(self) -> list[str]:
        return [x.task for x in self.data.values() if x.task is not None]


# ----------------------------
# Registration Helper

class HasBehaviors(Entity):
    # Use mixin or call `_annotate` in `__init_subclass__` for a class
    # with registered behaviors

    @classmethod
    def _annotate_behaviors(cls):
        # annotate handlers defined in this cls with the owner_cls
        for item in cls.__dict__:
            h = getattr(item, "_behavior", None)
            if h is not None:
                h.owner_cls = cls
                # cls is either class_on_caller or class_on_owner

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._annotate_behaviors()

    @model_validator(mode="after")
    def _annotate_inst_behaviors(self):
        # want to annotate and register a _copy_ of the instance (self, caller)
        # but _not_ class (cls, caller) behaviors with owner = self instead
        # of owner = cls
        ...
