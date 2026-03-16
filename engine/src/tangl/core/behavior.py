# tangl/core/behavior.py
"""Behavior dispatch primitives and receipt aggregation for core.

This module provides:

- behavior metadata and invocation wrappers (:class:`Behavior`);
- registry composition and execution plumbing (:class:`BehaviorRegistry`);
- execution receipts and aggregation helpers (:class:`CallReceipt`);
- shared ordering enums (:class:`Priority`, :class:`DispatchLayer`).

Higher layers supply policy by deciding which registries are active in context.
Core only defines deterministic selection, ordering, and result folding.
"""

from __future__ import annotations
import itertools
from typing import (
    Any,
    Callable,
    Protocol,
    Iterator,
    Iterable,
    Self,
    ClassVar,
    runtime_checkable,
    Mapping,
    Type,
    Optional,
)
from enum import IntEnum, Enum
from collections import ChainMap
from inspect import isclass
import logging

from pydantic import ConfigDict, model_validator, SkipValidation

from tangl.type_hints import Tag
from .entity import Entity
from .registry import Registry, RegistryAware
from .record import HasOrder, Record
from .selector import Selector
from .ctx import DispatchCtx

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class Priority(IntEnum):
    """Execution priority within one dispatch layer (lower values run earlier)."""
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


class DispatchLayer(IntEnum):
    """Registry layer ordering used before per-layer priority ordering."""
    # local sorts _later_ in execution priority so it can observe and aggregate globals
    GLOBAL = 0
    SYSTEM = 1
    APPLICATION = 2
    AUTHOR = 3
    USER = 4
    LOCAL = 5


@runtime_checkable
class RuntimeCtx(DispatchCtx, Protocol):
    """Runtime context protocol used by behavior execution chains.

    Core dispatch only requires registry and inline behavior access. Higher
    layers may expose additional fields and helper methods.
    """

    def get_authorities(self) -> Iterable[BehaviorRegistry]: ...
    def get_inline_behaviors(self) -> Iterable[Behavior | Callable[..., Any]]: ...


class AggregationMode(Enum):
    """How to reduce multiple receipts to a result."""
    FIRST = "first_result"       # Early-exit, first wins
    LAST = PIPE = "last_result"  # Composite result
    ALL_TRUE = "all_true"        # Validation gate
    GATHER = "gather_results"    # Collect all
    MERGE = "merge_results"      # Flatten/combine, later wins


class CallReceipt(Record):
    """
    **Aggregation Modes:**

    Receipt aggregation or folding summarizes dispatch traces into a concrete result or list of results.  One key detail is that behaviors that return a None result are tracked with a receipt for audit, but do not participate in result reduction. Several generic aggregators are implemented as class functions on Receipt (handling for collections of receipts).  Additional aggregators can be introduced at other layers.

    Supported aggregation helpers:
    - ``first_result``: first non-``None`` result (single winner).
    - ``last_result``: last non-``None`` result (override pattern).
    - ``all_true``: all non-``None`` results are truthy (validation gates).
    - ``gather_results``: collect all non-``None`` results.
    - ``merge_results``: flatten lists or merge dicts (later entries override).

    Examples:
        >>> receipts = [ CallReceipt(result=None),
        ...              CallReceipt(result=1),
        ...              CallReceipt(result=0),
        ...              CallReceipt(result=None) ]
        >>> CallReceipt.gather_results(*receipts)
        [1, 0]
        >>> CallReceipt.first_result(*receipts)
        1
        >>> CallReceipt.last_result(*receipts)
        0
        >>> CallReceipt.all_true(*receipts)
        False
        >>> CallReceipt.merge_results(CallReceipt(result=[1,2,3]),
        ...                           CallReceipt(result=[4,5,6]))  # flattens
        [1, 2, 3, 4, 5, 6]
        >>> dict( CallReceipt.merge_results(CallReceipt(result={'a': 'foo'}),
        ...                                 CallReceipt(result={'b': 'bar'}),
        ...                                 CallReceipt(result={'a': 'baz'})) )  # late overrides
        {'a': 'baz', 'b': 'bar'}
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    # carries arbitrary types in callbacks and context, so don't serialize
    guard_unstructure: ClassVar[bool] = True

    result: Any = None
    callback: Callable[[Any], Any] = None
    args: tuple[Any, ...] = None
    kwargs: dict[str, Any] = None
    ctx: SkipValidation[RuntimeCtx] = None

    @model_validator(mode='after')
    def _either_result_or_cb_specified(self) -> Self:
        """Require exactly one of ``result`` or ``callback``."""
        value = sum(['callback' in self.model_fields_set, 'result' in self.model_fields_set])
        if value != 1:
            raise ValueError("Exactly one of 'callback' or 'result' should be specified")
        return self

    def resolve(self, *args, **kwargs) -> Any:
        """Resolve deferred callback receipts once and cache the result."""
        if self.result is None and self.callback is not None:
            self.force_set('args', args)  # by-pass frozen
            self.force_set('kwargs', kwargs)
            result = self.callback(*self.args, ctx=self.ctx, **self.kwargs)
            self.force_set('result', result)
        return self.result

    # Aggregation functions

    # todo: force resolve any deferred receipts?  otherwise they don't count as None's

    @classmethod
    def iter_results(cls, *receipts) -> Iterator[Any]:
        """Yield non-``None`` receipt results in order."""
        return (receipt.result for receipt in receipts if receipt.result is not None)

    @classmethod
    def gather_results(cls, *receipts) -> list[Any]:
        """Collect non-``None`` receipt results in order."""
        return list(cls.iter_results(*receipts))

    @classmethod
    def first_result(cls, *receipts: Self):
        """Return first non-``None`` receipt result, or ``None``."""
        return next(cls.iter_results(*receipts), None)

    @classmethod
    def last_result(cls, *receipts: Self):
        """Return last non-``None`` receipt result, or ``None``."""
        return next(cls.iter_results(*reversed(receipts)), None)

    @classmethod
    def all_true(cls, *receipts: Self):
        """Return ``True`` when all non-``None`` results are truthy."""
        return all([bool(r) for r in cls.iter_results(*receipts)])

    @classmethod
    def all_truthy(cls, *receipts: Self):
        """Legacy alias for :meth:`all_true`."""
        return cls.all_true(*receipts)

    @classmethod
    def merge_results(cls, *receipts: Self) -> list[Any] | Mapping[Any, Any]:
        """Merge homogeneous results (lists/dicts) or return gathered mixed results."""
        results = cls.gather_results(*receipts)
        if all( isinstance(r, list) for r in results ):
            return list( itertools.chain.from_iterable(results) )
        elif all( isinstance(r, dict) for r in results ):
            return ChainMap(*reversed(results))  # later dict values override earlier ones
        return results

    @classmethod
    def aggregate(cls, mode: AggregationMode, *receipts: Self):
        """Dispatch aggregation by :class:`AggregationMode`."""
        match mode:
            case AggregationMode.FIRST:
                return cls.first_result(*receipts)
            case AggregationMode.LAST:
                return cls.last_result(*receipts)
            case AggregationMode.ALL_TRUE:
                return cls.all_true(*receipts)
            case AggregationMode.GATHER:
                return cls.gather_results(*receipts)
            case AggregationMode.MERGE:
                return cls.merge_results(*receipts)
            case _:
                raise ValueError(f"Unknown aggregation mode: {mode}")


class Behavior(RegistryAware, HasOrder, Entity):
    """
    Example:
        >>> b = Behavior(func=lambda *nums, **kwargs: sum(nums))
        >>> receipt = b(1, 2, 3)
        >>> f"sum{receipt.args}={receipt.result}"
        'sum(1, 2, 3)=6'
        >>> deferred = b.defer()
        >>> assert deferred.result is None
        >>> deferred.resolve(4, 5, 6)
        15
        >>> f"sum{deferred.args}={deferred.result}"
        'sum(4, 5, 6)=15'
        >>> c = Behavior(func=lambda *_, **__: True, wants_caller_kind=Entity)
        >>> assert Selector(caller_kind=Entity).matches(c) and not Selector(caller_kind=dict).matches(c)
    """
    # todo: method type introspection was in v37, but complicated and underutilized?
    #       - detect class methods as caller hint
    #       - detect inst methods as caller hint and bind func to caller dynamically
    #       - detect instance funcs and bind source

    func: Callable = lambda *_, **__: True
    task: Tag = None
    priority: int = Priority.NORMAL
    dispatch_layer: int = DispatchLayer.LOCAL

    wants_caller_kind: Type[Any] | None = None
    wants_exact_kind: bool = True  # disallow caller-kind subclasses

    def caller_kind(self, kind: Type[Any]) -> bool:
        """Return whether this behavior accepts a caller of ``kind``."""
        logger.debug("checking caller kind against wants_caller_kind")
        if self.wants_caller_kind is None:
            return True
        if isclass(kind):
            if kind is self.wants_caller_kind:
                return True
            elif not self.wants_exact_kind and issubclass(kind, self.wants_caller_kind):
                return True
        return False

    def __call__(self, *args, ctx: RuntimeCtx = None, **kwargs) -> CallReceipt:
        """Invoke behavior function and return a resolved :class:`CallReceipt`."""
        # todo: could do some introspection here, if the func wants caller, etc., check
        #       for default call args/kwargs in ctx
        return CallReceipt(
            origin_id=self.uid,
            result=self.func(*args, ctx=ctx, **kwargs),
            args=args,
            kwargs=kwargs,
            ctx=ctx
        )

    def defer(self, ctx: RuntimeCtx = None) -> CallReceipt:
        """Return a deferred receipt that resolves the callback later."""
        return CallReceipt(
            origin_id=self.uid,
            ctx=ctx,
            callback = self.func
        )

    @property
    def sort_key(self):
        """
        Sorts by:
          - layer: global -> local
          - priority: low -> high
          - wants_exact_kind: ``False`` then ``True``
          - registration seq: earlier -> later
        """
        return self.dispatch_layer, self.priority, self.wants_exact_kind, self.seq


class BehaviorRegistry(Registry[Behavior]):
    """
    Example:
        >>> br = BehaviorRegistry()
        >>> f = br.register(lambda *nums, **kwargs: sum(nums), task="sum")
        >>> g = br.register(lambda *args, **kwargs: ''.join([str(a) for a in args]),
        ...                 task="join", priority=Priority.EARLY)
        >>> next( br.execute_all(task="sum", call_args=(1, 2, 3)) ).result
        6
        >>> next( br.execute_all(task="join", call_args=('a', 'b', 'c')) ).result
        'abc'
        >>> CallReceipt.gather_results( *br.execute_all(call_args=(1, 2, 3)) )
        ...     # join triggers first even tho registered last, b/c lower priority
        ['123', 6]
    """

    default_task: Tag = None
    default_priority: Priority = Priority.NORMAL
    default_dispatch_layer: DispatchLayer = DispatchLayer.APPLICATION

    def register(self, func: Callable | None = None, **kwargs):
        """Register behavior function(s), supporting both direct and decorator use."""

        def _register(target: Callable) -> Callable:
            payload = dict(kwargs)
            payload.setdefault("task", self.default_task)
            payload.setdefault("priority", self.default_priority)
            payload.setdefault("dispatch_layer", self.default_dispatch_layer)
            behavior = Behavior(func=target, **payload)
            setattr(target, "_behavior", behavior)
            self.add(behavior)
            return target

        if func is None:
            return _register
        return _register(func)

    @classmethod
    def _get_receipts(cls, behaviors, *, call_args, call_kwargs, ctx) -> Iterator[CallReceipt]:
        """Yield receipts for each behavior call with normalized args/kwargs."""
        call_args = call_args or ()
        call_kwargs = call_kwargs or {}
        yield from (b(*call_args, ctx=ctx, **call_kwargs) for b in behaviors)

    # It would be nice to include aggregator here, but it makes type checking a pain
    def execute_all(self, *,
                    call_args: tuple[Any, ...] = None,
                    call_kwargs: dict[str, Any] = None,
                    ctx: RuntimeCtx = None,
                    task: Tag = None,
                    selector: Selector = None,
                    inline_behaviors: Iterable[Behavior | Callable[..., Any]] = None
                    ) -> Iterator[CallReceipt]:
        """
        Execute all behaviors matching selector in sorted order.

        Args:
            call_args: Positional arguments for behavior functions
            call_kwargs: Keyword arguments for behavior functions
            ctx: Runtime context (optional)
            task: Task tag to filter behaviors (convenience)
            selector: Additional selection criteria
            inline_behaviors: Additional behaviors/callables to execute

        Yields:
            CallReceipt for each executed behavior in sort order
        """
        return self.chain_execute_all(
            self,
            call_args=call_args,
            call_kwargs=call_kwargs,
            ctx=ctx,
            task=task,
            selector=selector,
            inline_behaviors=inline_behaviors,
        )

    def dispatch(
        self,
        *call_args: Any,
        ctx: RuntimeCtx = None,
        task: Tag = None,
        selector: Selector = None,
        extra_handlers: Iterable[Behavior | Callable[..., Any]] = None,
        **call_kwargs: Any,
    ) -> list[CallReceipt]:
        """Legacy alias returning a materialized receipt list."""
        kwargs = call_kwargs or None
        args = call_args or None
        return list(
            self.execute_all(
                call_args=args,
                call_kwargs=kwargs,
                ctx=ctx,
                task=task,
                selector=selector,
                inline_behaviors=extra_handlers,
            )
        )

    @classmethod
    def _wrap_inline(
        cls,
        behaviors: Iterable[Behavior | Callable[..., Any]],
        *,
        task: Tag = "inline",
    ) -> BehaviorRegistry:
        """Wrap ad-hoc inline callables/behaviors into a temporary local registry."""
        registry = cls(default_dispatch_layer=DispatchLayer.LOCAL)
        for behavior in behaviors:
            if isinstance(behavior, Behavior):
                # Keep original task/layer metadata without rebinding ownership.
                registry.members[behavior.uid] = behavior
                continue
            if callable(behavior):
                registry.register(func=behavior, task=task)
                continue
            raise TypeError(f"Expected Behavior or callable, got {type(behavior)!r}")
        return registry

    @classmethod
    def _ctx_authorities(cls, ctx: Any) -> Iterable[BehaviorRegistry]:
        """Yield registry authorities provided by ``ctx``."""
        get_authorities = getattr(ctx, "get_authorities", None)
        if callable(get_authorities):
            return get_authorities() or ()

        return ()

    @classmethod
    def chain_execute_all(
        cls,
        *registries: BehaviorRegistry,
        call_args: Optional[tuple[Any, ...]] = None,
        call_kwargs: Optional[dict[str, Any]] = None,
        ctx: Optional[RuntimeCtx] = None,
        task: Optional[Tag] = None,
        selector: Optional[Selector] = None,
        inline_behaviors: Optional[Iterable[Behavior | Callable[..., Any]]] = None,
    ) -> Iterator[CallReceipt]:
        """Execute behaviors across multiple registries plus context-provided sources.

        Registry sources are assembled in this order:

        1. Explicit ``registries`` arguments.
        2. ``ctx.get_authorities()`` when available.
        3. Inline callables from ``ctx.get_inline_behaviors()`` and ``inline_behaviors``.

        Registries are deduplicated by object identity, then behaviors are filtered and
        sorted by :attr:`Behavior.sort_key`.
        """

        assembled_registries = list(registries)

        if ctx is not None:
            assembled_registries.extend(cls._ctx_authorities(ctx))

            get_inline_behaviors = getattr(ctx, "get_inline_behaviors", None)
            if callable(get_inline_behaviors):
                inline_from_ctx = get_inline_behaviors() or ()
                if inline_from_ctx:
                    assembled_registries.append(cls._wrap_inline(inline_from_ctx, task=task or "inline"))

        if inline_behaviors:
            assembled_registries.append(cls._wrap_inline(inline_behaviors, task=task or "inline"))

        deduplicated_registries: list[BehaviorRegistry] = []
        seen_registry_ids: set[int] = set()
        for registry in assembled_registries:
            registry_id = id(registry)
            if registry_id in seen_registry_ids:
                continue
            seen_registry_ids.add(registry_id)
            deduplicated_registries.append(registry)

        if task is not None:
            selector = (selector or Selector()).with_criteria(task=task)

        behaviors = cls.chain_find_all(
            *deduplicated_registries,
            selector=selector,
            sort_key=lambda v: v.sort_key,
        )
        return cls._get_receipts(behaviors, call_args=call_args, call_kwargs=call_kwargs, ctx=ctx)

    @classmethod
    def chain_execute(
        cls,
        *registries: BehaviorRegistry,
        call_args: Optional[tuple[Any, ...]] = None,
        call_kwargs: Optional[dict[str, Any]] = None,
        ctx: Optional[RuntimeCtx] = None,
        task: Optional[Tag] = None,
        selector: Optional[Selector] = None,
        inline_behaviors: Optional[Iterable[Behavior | Callable[..., Any]]] = None,
    ) -> Iterator[CallReceipt]:
        """Backwards-compatible alias for :meth:`chain_execute_all`."""
        return cls.chain_execute_all(
            *registries,
            call_args=call_args,
            call_kwargs=call_kwargs,
            ctx=ctx,
            task=task,
            selector=selector,
            inline_behaviors=inline_behaviors,
        )


# Legacy vocabulary aliases retained during namespace cutover.
HandlerPriority = Priority
HandlerLayer = DispatchLayer
LayeredDispatch = BehaviorRegistry
