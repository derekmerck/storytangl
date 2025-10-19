from __future__ import annotations
from enum import IntEnum, Enum
from typing import Type, Callable, TypeVar, Iterator, Iterable, Any, Self, ClassVar, Literal
from functools import total_ordering
import itertools
from collections import ChainMap
from uuid import UUID

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.utils.base_model_plus import HasSeq
from tangl.core import Entity, Registry, Record
from tangl.core.entity import Selectable


# ----------------------------
# Kind Enums

class HandlerLayer(IntEnum):
    GLOBAL = 1       # available everywhere (i.e., core jobs)
    APPLICATION = 2  # included by application (i.e., vm jobs)
    AUTHOR = 3       # world mixins
    LOCAL = 4        # defined on a node, ancestors, or graph
    INLINE = 5       # injected for task (ignore missing @task)

class HandlerType(IntEnum):
    STATIC = 1
    CLASS = 2
    INSTANCE = 3

class HandlerPriority(IntEnum):
    FIRST = 1
    EARLY = 25
    NORMAL = 50
    LATER = 75
    LAST = 100

# ----------------------------
# Utils

def _mro_dist(super_cls: Type, sub_cls: Type) -> int:
    # todo: impl
    return 0


# ----------------------------
# Behaviors

@total_ordering
class Behavior(Entity, Selectable, HasSeq):
    func: Callable
    handler_type: HandlerType

    owner_cls: Type = None    # Only req if this is an INSTANCE or CLASS type
    caller_cls: Type = None   # Owner class if INSTANCE, else explicit

    def get_caller_cls(self) -> Type[CallerT] | None:
        if self.handler_type == HandlerType.INSTANCE:
            return self.owner_cls
        return self.caller_cls

    def mro_dist(self, caller: CallerT) -> int:
        wants_caller_cls = self.get_caller_cls()
        return _mro_dist( caller.__class__, wants_caller_cls )

    priority: HandlerPriority = HandlerPriority.NORMAL

    origin: BehaviorRegistry = None
    # The origin is not the registry, but the node that contributed the registry to discovery

    def origin_dist(self, caller: CallerT) -> int:
        # how far away is this behavior's origin from the caller by discovery
        # inline = 0, on self = 1, on ancestors = dist
        # this is what order the registry has in the initial domain-sorted input for select_by
        return 0

    def get_layer(self) -> HandlerLayer:
        # this isn't really the discovery 'origin', it's the registry's layer in this case
        if self.origin is not None and self.origin.handler_layer is not None:
            return self.origin.handler_layer
        return HandlerLayer.INLINE

    task: str = None   # "@validate", "@render", etc.

    def get_task(self) -> str | None:
        if self.task is not None:
            return self.task
        if self.origin is not None and self.origin.task is not None:
            return self.origin.task

    def has_task(self, task: str) -> bool:
        # No task given
        if task is None or \
           self.get_task() is None or \
           self.get_layer() is HandlerLayer.INLINE:
            # we can ignore
            return True
        return task == self.get_task()

    def get_selection_criteria(self) -> StringMap:
        criteria = dict(self.selection_criteria)
        # We will get the registries task and caller_cls if any from the registry criteria merge
        if self.caller_cls is not None:
            criteria.setdefault("is_instance", self.caller_cls)
        if self.origin is not None:
            # small chance that the registry might have a more specific criterion,
            # like a lower bound on caller_cls, but that seems like improper usage.
            criteria = self.origin.get_selection_criteria() | criteria  # clobber
        return criteria

    @property
    def specificity(self) -> int:
        # 3-tuple in css: #identifiers, .pseudo-classes, association tags
        criteria = self.get_selection_criteria()
        if 'has_identifier' in criteria:
            # #id=x is more specific than any number of other criteria
            return 100
        return len(criteria)

    def sort_key(self, caller=None, by_origin = False):
        """
        - global < inline         # inline can clobber
        - priority early < late   # late can clobber
        - fewer selectors < more  # more selectors can clobber
        - -origin dist            # closer registry can clobber (needs caller)
        - -mro dist               # closer func def can clobber (needs caller)
        - static < class < inst   # inst can clobber
        - late def < early        # first created wins

        `by_origin` flag -> origin dist !important
        """
        # Without a caller, we can only resolve a caller-independent key
        if caller is None:
            return (self.get_layer(),
                    self.priority,
                    self.specificity,
                    self.handler_type,
                    -self.seq)

        # With a caller, we can resolve a more precise caller-dependent key
        if by_origin:
            return (-self.origin_dist(caller),  # closer ancestors > farther ancestors
                    self.get_layer(),
                    self.priority,
                    self.specificity,
                    -self.mro_dist(caller),     # subclass meth > superclass meth
                    self.handler_type,
                    -self.seq)

        return (self.get_layer(),
                self.priority,
                self.specificity,
                -self.origin_dist(caller),  # closer ancestors > farther ancestors
                -self.mro_dist(caller),     # subclass meth > superclass meth
                self.handler_type,
                -self.seq)

    def __lt__(self, other: Behavior):
        return self.sort_key() < other.sort_key()

    def __call__(self, caller: CallerT, *args, ctx = None, **kwargs) -> CallReceipt:
        # call func, wrap in receipt
        result = self.func(caller, *args, ctx = ctx, **kwargs)
        return CallReceipt(
            behavior_id=self.uid,
            result=result,  # can put a lambda here if we want deferred/lazy eval or iter dispatch
            ctx=ctx,
            args=args,
            kwargs=kwargs
        )

# ----------------------------
# Registry/Dispatch

CallerT = TypeVar("CallerT")
ResultT = TypeVar("ResultT")

class BehaviorRegistry(Registry[Behavior]):
    behaviors: list[Behavior] = Field(default_factory=list)

    # defaults
    handler_layer: HandlerLayer = HandlerLayer.GLOBAL
    task: str = None

    def add_behavior(self, item, **kwargs):
        if isinstance(item, Behavior):
            self.add(item)
        elif isinstance(item, Callable):
            h = Behavior(func=item, **kwargs)
            self.add(h)
        else:
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

    def dispatch(self, caller: CallerT, *, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, **inline_criteria) -> Iterator[CallReceipt]:
        # task param is just a type-hint for `inline_criteria['task'] = '@foo'`
        behaviors = self.select_all_for(selector=caller, task=task, **inline_criteria)
        if extra_handlers:  # inlines
            # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
            extra_behaviors = (Behavior(func=f, task=None) for f in extra_handlers or [])
            behaviors = itertools.chain(behaviors, extra_behaviors)
        behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller))
        return (b(caller, ctx) for b in behaviors)

    @classmethod
    def chain_dispatch(cls, *registries: BehaviorRegistry, caller, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, **inline_criteria) -> Iterator[CallReceipt]:
        # task param is just a type-hint for `inline_criteria['task'] = '@foo'`
        behaviors = cls.chain_select_all_for(*registries, selector=caller, task=task, **inline_criteria)
        if extra_handlers:  # inlines
            # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
            extra_behaviors = (Behavior(func=f, task=None) for f in extra_handlers or [])
            behaviors = itertools.chain(behaviors, extra_behaviors)
        behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller))
        return (b(caller, ctx) for b in behaviors)


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

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._annotate_behaviors()


# ----------------------------
# Receipts and Aggregation

class AggregatorType(Enum):
    GATHER = "gather"
    MERGE = "merge"
    FIRST = "first"
    LAST = "last"
    ANY = "any"
    ALL = "all"

class CallReceipt(Record):
    record_type: Literal['receipt'] = "receipt"
    behavior_id: UUID
    result: Any
    ctx: Any = Field(None, exclude=True)    # don't try to serialize this stuff
    args: tuple | None = Field(None, exclude=True)
    kwargs: dict | None = Field(None, exclude=True)

    # Aggregators

    @classmethod
    def gather_results(cls, *receipts: Self) -> Iterator[Any]:
        return (r.result for r in receipts if r is not None)

    @classmethod
    def merge_results(cls, *receipts: Self) -> ChainMap:
        results = cls.gather_results(*receipts)
        return ChainMap(*results)

    @classmethod
    def first_result(cls, *receipts: Self) -> Any:
        return next(cls.gather_results(*receipts), None)

    @classmethod
    def any_true(cls, *receipts: Self) -> bool:
        # all false -> not any true
        return any(cls.gather_results(*receipts))

    @classmethod
    def last_result(cls, *receipts: Self) -> Any:
        # Useful for pipelining
        return next(cls.gather_results(*reversed(receipts)), None)

    @classmethod
    def all_true(cls, *receipts: Self) -> bool:
        # any false -> not all true
        return all(cls.gather_results(*receipts))

    aggregation_func: ClassVar[dict[AggregatorType, Callable]] = {
        AggregatorType.GATHER: gather_results,
        AggregatorType.MERGE: merge_results,
        AggregatorType.FIRST: first_result,
        AggregatorType.ANY: any_true,
        AggregatorType.LAST: last_result,
        AggregatorType.ALL: all_true,
    }

    @classmethod
    def aggregate(cls, aggregator: AggregatorType = AggregatorType.GATHER,
                       *receipts: Self) -> Iterator[Any] | Any | bool | ChainMap:
        # Helper to avoid lambdas
        aggregation_func = cls.aggregation_func.get(aggregator)
        if aggregation_func is None:
            raise ValueError(f"Unknown aggregation type {aggregator}")
        return aggregation_func(*receipts)


# --------------------------
# Binding patterns

# There are 5? unique signature patterns

# These _all_ require different bindings
# - how do we annotate them and bind them properly
# - how do we infer annotations as necessary so we don't have to exhaustively label them?
#   - using init_subclass for registration and post_init for manager pattern?

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

# Owner class == caller class
# We can infer caller class from owner_cls
on_task.add_behavior(Tasker.inst_do_something, handler_type=HandlerType.INSTANCE)
on_task.add_behavior(Tasker.cls_do_something, handler_type=HandlerType.CLASS)

class TaskManager(Entity):

    def mgr_do_something(self, caller: Tasker, *args, **kwargs) -> Any:
        ...

    @classmethod
    def mgr_cls_do_something(cls, caller: Tasker, *args, **kwargs) -> Any:
        ...

mgr = TaskManager()

# Owner class != caller class
# in this case, we need to track the owner/self for binding
on_task.add_behavior(TaskManager.mgr_do_something, owner=mgr, handler_type=HandlerType.INSTANCE, caller_cls=Tasker)
# in this case, we can infer the owner class and bind automatically, need caller class separately
on_task.add_behavior(TaskManager.mgr_cls_do_something, handler_type=HandlerType.CLASS, caller_cls=Tasker)

# inherits task from registry, infers instance defined and caller class from func name?

inst = Tasker()

receipts = BehaviorRegistry.chain_dispatch(global_behaviors, on_task, caller=inst, task="my_task")
# should select and call all tasks
first_result = CallReceipt.first_result(*receipts)
print( first_result )

