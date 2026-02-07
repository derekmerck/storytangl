# tangl/core/behavior.py
from __future__ import annotations
import itertools
from typing import Any, Callable, Protocol, Iterator, Optional, Iterable, Self, ClassVar, runtime_checkable, Mapping
from enum import IntEnum, Enum
from collections import ChainMap

from pydantic import ConfigDict, model_validator

from tangl.type_hints import Tag
from .entity import Entity
from .registry import Registry, RegistryAware
from .record import HasOrder, Record
from .selector import Selector

class Priority(IntEnum):
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


class DispatchLayer(IntEnum):
    # local sorts _later_ in execution priority so it can observe and aggregate globals
    GLOBAL = 0
    SYSTEM = 1
    APPLICATION = 2
    AUTHOR = 3
    USER = 4
    LOCAL = 5

@runtime_checkable
class RuntimeCtx(Protocol):
    def get_args(self) -> tuple[Any]: ...
    def get_kwargs(self) -> dict[str, Any]: ...
    def get_selector(self) -> Selector: ...
    def get_receipts(self) -> list[CallReceipt]: ...
    def get_aggregation_mode(self) -> AggregationMode: ...

class AggregationMode(Enum):
    """How to reduce multiple receipts to a result."""
    FIRST = "first_result"      # Early-exit, first wins
    LAST = "last_result"        # Late-override, last wins
    ALL_TRUE = "all_true"       # Validation gate
    GATHER = "gather_results"   # Collect all
    MERGE = "merge_results"     # Flatten/combine

class CallReceipt(Record):
    """

    **Aggregation Modes:**

    Receipt aggregation or folding summarizes dispatch traces into a concrete result or list of results.  One key detail is that behaviors that return a None result are tracked with a receipt for audit, but do not participate in result reduction. Several generic aggregators are implemented as class functions on Receipt (handling for collections of receipts).  Additional aggregators can be introduced at other layers.

    | Mode             | Function                  | Use Case              |
    |------------------|---------------------------|-----------------------|
    | `first_result`   | First non-None result     | Single result needed  |
    | `last_result`    | Last non-None result      | Override pattern      |
    | `all_true`       | All results truthy        | Validation gates      |
    | `gather_results` | Collect all results       | Accumulation          |
    | `merge_results`  | Flatten lists/merge dicts | Contribution collection |

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

    result: Any = None
    callback: Callable[[Any], Any] = None
    args: tuple[Any, ...] = None
    kwargs: dict[str, Any] = None
    ctx: Optional[RuntimeCtx] = None

    # carries context for reference, so don't serialize
    guard_unstructure: ClassVar[bool] = True

    @model_validator(mode='after')
    def _either_result_or_cb_specified(self):
        value = sum(['callback' in self.model_fields_set, 'result' in self.model_fields_set])
        if value != 1:
            raise ValueError("Exactly one of 'callback' or 'result' should be specified")

    def resolve(self, *args, **kwargs) -> Any:
        if self.result is None and self.callback is not None:
            self.force_set('args', args)  # by-pass frozen
            self.force_set('kwargs', kwargs)
            result = self.callback(*self.args, ctx=self.ctx, **self.kwargs)
            self.force_set('result', result)
        return self.result

    # Aggregation functions

    # todo: force resolve any deferred receipts?

    @classmethod
    def iter_results(cls, *receipts) -> Iterator[Any]:
        return (receipt.result for receipt in receipts if receipt.result is not None)

    @classmethod
    def gather_results(cls, *receipts) -> list[Any]:
        return list(cls.iter_results(*receipts))

    @classmethod
    def first_result(cls, *receipts: Self):
        if len(receipts) < 1:
            raise IndexError
        return next(cls.iter_results(*receipts), None)

    @classmethod
    def last_result(cls, *receipts: Self):
        # this is equivalent to _any_ result is true
        if len(receipts) < 1:
            raise IndexError
        return next(cls.iter_results(*reversed(receipts)), None)

    @classmethod
    def all_true(cls, *receipts: Self):
        return all([bool(r) for r in cls.iter_results(*receipts)])

    @classmethod
    def merge_results(cls, *receipts: Self) -> list[Any] | Mapping[Any, Any]:
        results = cls.gather_results(*receipts)
        if all( isinstance(r, list) for r in results ):
            return list( itertools.chain.from_iterable(results) )
        elif all( isinstance(r, dict) for r in results ):
            return ChainMap(*reversed(results))  # early overrides late in chain map
        return results

    @classmethod
    def aggregate(cls, mode: AggregationMode, *receipts: Self):
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
    """

    func: Callable = lambda *_, **__: True
    task: Tag = None
    priority: int = Priority.NORMAL
    dispatch_layer: int = DispatchLayer.LOCAL

    def __call__(self, *args, ctx: RuntimeCtx = None, **kwargs) -> CallReceipt:
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
        return CallReceipt(
            origin_id=self.uid,
            ctx=ctx,
            callback = self.func
        )

    @property
    def sort_key(self):
        return self.dispatch_layer, self.priority, self.seq


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

    def register(self, func: Callable, **kwargs) -> Callable:
        """Decorator to register a behavior"""
        kwargs.setdefault("task", self.default_task)
        kwargs.setdefault("priority", self.default_priority)
        kwargs.setdefault("dispatch_layer", self.default_dispatch_layer)
        behavior = Behavior(func=func, **kwargs)
        setattr(func, "_behavior", behavior)
        self.add(behavior)
        return func

    @classmethod
    def _get_receipts(cls, behaviors, *, call_args, call_kwargs, ctx) -> Iterator[CallReceipt]:
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
                    inline_behaviors: Iterable[Behavior] = None
                    ) -> Iterator[CallReceipt]:
        """
        Execute all behaviors matching selector in sorted order.

        Args:
            call_args: Positional arguments for behavior functions
            call_kwargs: Keyword arguments for behavior functions
            ctx: Runtime context (optional)
            task: Task tag to filter behaviors (convenience)
            selector: Additional selection criteria
            inline_behaviors: Additional behaviors to execute (not implemented)

        Yields:
            CallReceipt for each executed behavior in sort order
        """
        if task is not None:
            selector = selector or Selector()
            selector = selector.with_criteria(task=task)

        # selector from task, sort_key from prio, seq
        # if inline behaviors or ctx carries dispatch layers
        #   do a chain_find_all
        behaviors = self.find_all(selector=selector,
                                  sort_key=lambda v: v.sort_key)
        if inline_behaviors:
            # todo: allow inline behaviors to be funcs and cast them to behaviors with layer local before adding them.
            behaviors = list(behaviors)
            behaviors.extend(inline_behaviors)
            behaviors.sort(key=lambda v: v.sort_key)
        return self._get_receipts(behaviors, call_args=call_args, call_kwargs=call_kwargs, ctx=ctx)

    @classmethod
    def chain_execute(cls, *registries,
                      call_args = None,
                      call_kwargs = None,
                      ctx = None, task = None,
                      selector: Selector = None,
                      inline_behaviors: Iterable[Behavior] = None
                      ) -> Iterator[CallReceipt]:

        if task is not None:
            selector = selector or Selector()
            selector = selector.with_criteria(task=task)

        behaviors = cls.chain_find_all(
            *registries,
            selector=selector,
            sort_key=lambda v: v.sort_key)
        if inline_behaviors:
            behaviors = list(behaviors)
            behaviors.extend(inline_behaviors)
            behaviors.sort(key=lambda v: v.sort_key)
        return cls._get_receipts(behaviors, call_args=call_args, call_kwargs=call_kwargs, ctx=ctx)
