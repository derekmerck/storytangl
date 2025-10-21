# tangl/core/dispatch/behaviors.py
"""version 37.2"""
from __future__ import annotations
from enum import IntEnum, Enum, auto
from typing import Type, Callable, TypeVar, Iterator, Iterable, Any, Self, ClassVar, Literal, Protocol, runtime_checkable, Optional
from functools import total_ordering
import itertools
from collections import ChainMap
from uuid import UUID
import inspect
import weakref

from pydantic import Field, field_validator, model_validator

from tangl.type_hints import StringMap
from tangl.utils.base_model_plus import HasSeq
from tangl.utils.func_info import FuncInfo
from tangl.core import Entity, Registry, Record
from tangl.core.entity import Selectable, is_identifier
from tangl.core.registry import _chained_registries


# ----------------------------
# Kind Enums

class HandlerLayer(IntEnum):
    # Reverse sort inline > global
    INLINE = 1       # injected for task (ignore missing @task)
    LOCAL = 2        # defined on a node, ancestors, or graph
    AUTHOR = 3       # world mixins
    APPLICATION = 4  # included by application (i.e., vm jobs)
    GLOBAL = 5       # available everywhere (i.e., core jobs)

class HandlerPriority(IntEnum):
    FIRST = 1
    EARLY = 25
    NORMAL = 50
    LATER = 75
    LAST = 100

# ----------------------------
# Utils

def _mro_dist(this_cls: Type, super_cls: Type) -> int:
    if super_cls is None:
        return 1 << 20  # "very far" when no constraint
    if not isinstance(this_cls, type) or not isinstance(super_cls, type):
        return 1 << 20
    mro = this_cls.mro()
    return mro.index(super_cls) if super_cls in mro else 1 << 20

# Note this is runtime_checkable so Pydantic will allow it as a type-hint.
# It is not actually validated, so this is purely organizational and the function
# call will actually admit any type *args.
@runtime_checkable
class HandlerFunc(Protocol):
    def __call__(self, caller: Entity, *others: Entity, ctx: Optional[Any] = None, **params: Any) -> Any: ...
    # Variadic args are entities, to support things like __lt__(self, other) or transaction
    # type calls
    # `ctx` is a reserved kw arg for Context objects passed by the resolution frame's phase bus
    # `ns` is also a reserved kw arg for scoped namespace string maps, ns will be pulled from ctx
    # if ns is not provided but ctx is

# ----------------------------
# Behaviors

class HandlerType(IntEnum):
    # Most specific
    INSTANCE_ON_CALLER = 5  # unbound def on caller class, we bind to runtime caller
    CLASS_ON_CALLER = 4     # classmethod on caller.__class__
    INSTANCE_ON_OWNER = 3   # bound to some manager instance (weakref)
    CLASS_ON_OWNER = 2      # classmethod on foreign manager class
    STATIC = 1              # unbound free function, signature (caller, *args, **kwargs)
    # Most general

@total_ordering
class Behavior(Entity, Selectable, HasSeq, arbitrary_types_allowed=True):
    # arbitrary types allowed for possible WeakRef owner
    func: HandlerFunc

    def has_func_name(self, value: str) -> bool:
        # for matching
        return self.func.__name__ == value

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.func.__name__

    # classification is inferred in _populate_from_funcinfo unless explicitly provided
    handler_type: HandlerType = HandlerType.STATIC
    owner: Entity | weakref.ReferenceType | None = None
    owner_cls: Type[Entity] = None
    caller_cls: Type = None   # for selection and dist; can infer on bind/call

    @model_validator(mode="before")
    @classmethod
    def _populate_from_funcinfo(cls, values: dict):
        """
        Hydrate Behavior from FuncInfo in one deterministic pass.
        Explicit kwargs win; inferred values fill gaps.
        Also normalizes a bound caller method (self, no 'caller') to unbound
        to avoid double-binding at call time.
        """
        func = values.get("func")
        if func is None:
            return values

        # Track explicit hints (before inference)
        explicit_handler_type = values.get("handler_type") not in (None, HandlerType.STATIC)
        explicit_owner = values.get("owner") is not None
        explicit_caller_cls = values.get("caller_cls") is not None

        owner_val = values.get("owner")
        owner_cls_hint = owner_val if isinstance(owner_val, type) else None
        owner_inst_hint = owner_val if (owner_val is not None and not isinstance(owner_val, type)) else None

        info = FuncInfo.from_func(
            func=func,
            handler_type=values.get("handler_type"),
            caller_cls=values.get("caller_cls"),
            owner_cls=owner_cls_hint,
            owner=owner_inst_hint,
        )
        if info is None:
            return values

        # Always use normalized func from FuncInfo (may unbind bound methods)
        values["func"] = info.func

        # handler_type: explicit wins, otherwise inferred
        if not explicit_handler_type:
            values["handler_type"] = info.handler_type

        # caller_cls: fill if missing
        if not explicit_caller_cls and getattr(info, "caller_cls", None) is not None:
            values["caller_cls"] = info.caller_cls

        # owner: fill if missing, in the shape Behavior expects
        # - INSTANCE_ON_OWNER: store the instance (field validator will weakref it)
        # - CLASS_ON_OWNER: store the owner class
        if not explicit_owner:
            if info.handler_type == HandlerType.INSTANCE_ON_OWNER and getattr(info, "owner", None) is not None:
                values["owner"] = info.owner
                values["owner_cls"] = info.owner_cls
            elif info.handler_type == HandlerType.CLASS_ON_OWNER and getattr(info, "owner_cls", None) is not None:
                values["owner_cls"] = info.owner_cls

        return values

    # req if INST_ON_OWNER or CLASS_ON_OWNER
    @field_validator("owner", mode="before")
    @classmethod
    def _owner_to_weakref(cls, data):
        if isinstance(data, Entity):
            data = weakref.ref(data)
            # can guarantee that this is INST_ON_OWNER now
        # Classes and None pass through
        return data

    def mro_dist(self, caller: CallerT = None) -> int:
        if caller is None:
            return -1
        return _mro_dist(caller.__class__, self.caller_cls)

    priority: HandlerPriority = HandlerPriority.NORMAL

    origin: BehaviorRegistry = None
    # The origin is not the registry, but the node that contributed the registry to discovery

    def origin_dist(self) -> int:
        # how far away is this behavior's origin from the caller by discovery
        # -1 = inline
        #  0 = self layer
        #  1-n = ancestor layers
        #  >n = APP, GLOBAL handler layers
        #  large = missing from registry
        # todo: still not sure this is right, what about a global handler
        #       referenced by a parent?
        if self.origin is None or self.handler_layer() is HandlerLayer.INLINE:
            return -1
        from tangl.core.registry import _CHAINED_REGISTRIES
        registries = _CHAINED_REGISTRIES.get()
        if registries is None or self.origin not in registries:
            # Called for a sort key without having a relevant chained registry ctx var
            return 1 << 20
        return registries.index(self.origin)

    def handler_layer(self) -> HandlerLayer:
        # this isn't really the discovery 'origin', it's the registry's layer in this case
        if self.origin is not None and self.origin.handler_layer is not None:
            return self.origin.handler_layer
        return HandlerLayer.INLINE

    task: str = None   # "@validate", "@render", etc.

    def has_task(self, task: str) -> bool:
        # when filtered by behavior.matches(has_task=x)
        if task is None:
            # No task given, always match
            return True
        if self.handler_layer() is HandlerLayer.INLINE:
            # I may not have a task, but I am inline
            return True
        if self.task is not None:
            # I might match some non-None task
            return self.task == task
        if self.origin is not None and self.origin.task is not None:
            # I might inherit my origin's non-None task
            return self.origin.task == task
        return False

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

    @classmethod
    def _criteria_specificity(cls, **criteria) -> tuple[int, int, int]:
        # 3-tuple in css: #identifiers, .class/pseudo classes, association tags
        id_specifier = 1 if 'has_identifier' in criteria else 0
        class_specifier = 1 if 'is_instance' in criteria else 0
        other_specifiers = len(criteria) - id_specifier - class_specifier
        return id_specifier, class_specifier, other_specifiers

    @property
    def specificity(self) -> tuple[int, int, int]:
        # does not include task, since that's not in specifier, but maybe useful to know if
        # this handler has a task, or if it's using its registry's default task
        return self._criteria_specificity(**self.get_selection_criteria())

    def sort_key(self, caller=None, by_origin = False):
        """
        -  priority early < late   # late can clobber
        - -origin dist             # closer registry can clobber (needs caller)
        -  global < inline         # inline can clobber
        - -mro dist                # closer func def can clobber (needs caller)
        - *fewer selectors < more  # more selectors can clobber
        -  static < class < inst   # most specific (inst) can clobber
        -  late def < early        # first created wins

        `by_origin` flag -> flips priority and origin dist/layer ~ origin dist !important
        This is critical for ensuring that ancestor order is preserved and values shadowed
        by layer, not by priority when accumulating a namespace.
        """
        if by_origin:
            # by priority within registry/layer
            return (-self.origin_dist(),        # closer ancestors > farther ancestors
                    -self.handler_layer(),      # inline > globals
                     self.priority,             # explicit
                    -self.mro_dist(caller),     # subclass meth > superclass meth
                    *self.specificity,          # match specificity
                     self.handler_type,         # instance > class > static
                    -self.seq)                  # registration order

        # by priority first
        return ( self.priority,                 # explicit
                -self.origin_dist(),            # closer ancestors > farther ancestors
                -self.handler_layer(),          # inline > globals
                -self.mro_dist(caller),         # subclass meth > superclass meth
                *self.specificity,              # match specificity
                 self.handler_type,             # instance > class > static
                -self.seq)                      # registration order

    def __lt__(self, other: Behavior):
        return self.sort_key() < other.sort_key()

    def bind_func(self, caller: CallerT) -> Callable:
        """
        There are several possible signatures for a handler:
        - `f(self/caller, *, ctx, other = None, result = None )`, mro instance methods, static methods
        - `f(self/owner, caller, *, ctx, result = None )`, instance methods on other nodes
        - `f(cls, caller, *, ctx, other = None, result = None )`, cls methods (on any cls)
        """
        match self.handler_type:
            # The instance case is not actually necessary as we always include _caller_
            # as the first argument in the standard invocation
            # case HandlerType.INSTANCE_ON_CALLER:
            #     return self.func.__get__(caller, caller.__class__)  # bind to caller
            case HandlerType.STATIC | HandlerType.INSTANCE_ON_CALLER:
                return self.func

            # For class methods, we only need to know the owner class if it's _not_
            # the caller's class.  In general, perhaps we don't need to distinguish
            # them and we can just assume owner/owner_cls -> caller.__class__ during
            # init.  In that case, we don't need to pass in 'caller' and this can be
            # cached.
            case HandlerType.CLASS_ON_CALLER:
                return self.func.__get__(caller.__class__, type)   # bind to caller's class
            case HandlerType.CLASS_ON_OWNER:  # bind to foreign class, no owner inst
                if not isinstance(self.owner_cls, type):
                    raise RuntimeError(f"Expected 'owner' to be a class type for CLASS_ON_OWNER, got {type(self.owner_cls)}")
                return self.func.__get__(self.owner_cls, type)

            # This is the exception, when we need to grab a reference to a specific
            # manager instance where this behavior is registered, a function that
            # takes self, but is not the caller.
            case HandlerType.INSTANCE_ON_OWNER:
                owner_inst = self.owner() if self.owner else None
                if owner_inst is None:  # owner GC'd or otherwise missing
                    raise RuntimeError("Handler owner is not defined")
                return self.func.__get__(owner_inst, owner_inst.__class__)

            case _:
                raise RuntimeError("Unknown call mode")

    def __call__(self, caller: CallerT, *args, ctx = None, **kwargs) -> CallReceipt:
        # bind func, call func, wrap in receipt
        bound = self.bind_func(caller)
        result = bound(caller, *args, ctx=ctx, **kwargs)
        return CallReceipt(
            behavior_id=self.uid,
            result=result,  # can put a lambda here if we want deferred/lazy eval or iter dispatch
            ctx=ctx,
            args=args,
            kwargs=kwargs
        )

    def unstructure(self) -> StringMap:
        raise RuntimeError(f"Do _not_ try to serialize {self!r}; contains Callable, WeakRef.")

    def get_func_sig(self):
        return self._get_func_sig(self.func)

    @staticmethod
    def _get_func_sig(func):
        if func is None:
            raise ValueError("func cannot be None")
        while hasattr(func, '__func__'):
            # May be a wrapped object
            func = func.__func__
        return inspect.signature(func)

    def __hash__(self) -> int:
        # delegate hash, assuming each func can only correspond to a single handler
        return hash(self.func)

# ----------------------------
# Registry/Dispatch

CallerT = TypeVar("CallerT")
ResultT = TypeVar("ResultT")

class BehaviorRegistry(Selectable, Registry[Behavior]):
    """
    A registry can represent a single task/phase, or a single layer (global, app, author),
    or provide a mix.

    Calling dispatch will filter handlers for criteria (i.e., phase/task) and then filter
    for a selector, the calling entity.  Selection criteria is handled similarly to
    css specificity, where more specific/closer/earlier behavior definitions have priority,
    and are run _last_ so they can inspect or clobber prior results.
    """

    # defaults
    handler_layer: HandlerLayer = HandlerLayer.GLOBAL
    task: str = None

    def add_behavior(self, item, *,
                     priority: HandlerPriority = HandlerPriority.NORMAL,
                     handler_type: HandlerType = HandlerType.STATIC,
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

    def dispatch(self, caller: CallerT, *, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task
        behaviors = self.select_all_for(selector=caller, **inline_criteria)
        if extra_handlers:  # inlines
            # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
            extra_behaviors = (Behavior(func=f, task=None) for f in extra_handlers or [])
            behaviors = itertools.chain(behaviors, extra_behaviors)
        behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        return (b(caller, ctx) for b in behaviors)

    @classmethod
    def chain_dispatch(cls, *registries: BehaviorRegistry, caller, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task

        behaviors = cls.chain_select_all_for(*registries, selector=caller, **inline_criteria)
        # could also treat this as an ephemeral registry and add it onto the registry
        # stack and sort while filtering, but it seems clearer to copy the
        # single-registry-dispatch code.
        if extra_handlers:  # inlines
            # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
            extra_behaviors = (Behavior(func=f, task=None) for f in extra_handlers or [])
            behaviors = itertools.chain(behaviors, extra_behaviors)
        with _chained_registries(registries):  # provide registries for origin_dist sort key
            behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        return (b(caller, ctx) for b in behaviors)

    def iter_dispatch(self, *args, **kwargs) -> Iterator[CallReceipt]:
        raise NotImplementedError()
        # We could return an iterator of handler calls that each produce a receipt:
        return (lambda: b(caller, ctx) for b in behaviors)
        # Or we could return an iterator of job receipts with lambda functions as result
        return (b.partial_receipt(caller, ctx) for b in behaviors)
        # Probably want a iter_chain_dispatch() as well for symmetry


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
        # want to annotate a _copy_ of the instance (self, caller) but not
        # class (cls, caller) behaviors with owner = self instead of owner = cls
        ...


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
    """
    Support behavior audit for each phase in the vm, which behaviors were triggered, what were the resulting shape and data changes.
    """
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

# There are 5 cases and 3 unique signature patterns and require different bindings.
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

inst = Tasker()

receipts = BehaviorRegistry.chain_dispatch(global_behaviors, on_task, caller=inst, task="my_task")
# should select and call all tasks
first_result = CallReceipt.first_result(*receipts)
print( first_result )

