from __future__ import annotations
from typing import Any, Callable, Protocol, Iterator, Optional, Iterable, Self
from enum import IntEnum
from functools import partial

from tangl.type_hints import Tag
from .bases import NonUnstructurable
# from .builder import BuildOffer
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


class RTCtx(Protocol):
    def get_caller(self) -> tuple[Any]: ...
    def get_others(self) -> dict[str, Any]: ...
    def get_kwargs(self) -> dict[str, Any]: ...
    def get_dispatch_layers(self) -> Iterator[BehaviorRegistry]: ...
    def get_selector(self) -> Selector: ...
    def get_receipts(self) -> list[CallReceipt]: ...


class CallReceipt(NonUnstructurable, Record, arbitrary_types_allowed=True):
    # carries context for reference, so don't serialize
    result: Any
    args: tuple[Any] = None
    kwargs: dict[str, Any] = None
    # ctx: RTCtx = None

    # Aggregation functions

    @classmethod
    def iter_results(cls, *receipts) -> Iterator[Any]:
        return (receipt.result for receipt in receipts if receipt.result is not None)

    @classmethod
    def last_result(cls, *receipts: Self):
        if len(receipts) < 1:
            raise IndexError
        return next(cls.iter_results(*receipts), None)

    @classmethod
    def first_result(cls, *receipts: Self):
        # this is equivalent to _any_ result is true
        if len(receipts) < 1:
            raise IndexError
        return next(cls.iter_results(*reversed(receipts)), None)

    @classmethod
    def all_results_true(cls, *receipts: Self):
        return all([bool(r) for r in cls.iter_results(*receipts)])


class DeferredReceipt(CallReceipt):
    # carries callback and context, so don't serialize
    callback: Any
    result: Any = None  # No longer required, set by resolve

    def resolve(self, *args, **kwargs) -> Any:
        result = self.callback(*self.args, ctx=self.ctx, **self.kwargs)
        setattr(self, 'result', result)  # frozen
        setattr(self, 'args', args)
        setattr(self, 'kwargs', kwargs)
        return result


class Behavior(RegistryAware, NonUnstructurable, HasOrder, Entity):

    func: Callable = lambda *_, **__: True
    task: Tag = None
    priority: int = Priority.NORMAL
    dispatch_layer: int = DispatchLayer.LOCAL

    def __call__(self, *args, ctx: RTCtx = None, **kwargs) -> CallReceipt:
        # could do some introspection here, if the func wants caller, etc.
        return CallReceipt(
            origin_id=self.origin_id,
            result=self.func(*args, ctx=ctx, **kwargs),
            args=args,
            kwargs=kwargs,
            ctx=ctx
        )

    def defer(self, ctx: RTCtx) -> DeferredReceipt:
        return DeferredReceipt(
            origin_id=self.origin_id,
            callback=self.func,
            ctx=ctx
        )

    @property
    def sort_key(self):
        return self.dispatch_layer, self.priority, self.seq

# def dispatches(meth):
#     # deco for methods that want a dispatch context for a task with their name
#     setattr(meth, '_dispatches', True)
#     return meth


class BehaviorRegistry(Registry[Behavior]):

    default_task: Tag = None
    default_priority: Priority = Priority.NORMAL
    default_dispatch_layer: DispatchLayer = DispatchLayer.APPLICATION

    def register(self, func: Callable, **kwargs) -> Callable:
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

    def execute_all(self, *,
                    call_args: tuple[Any] = None,
                    call_kwargs: dict[str, Any] = None,
                    ctx: RTCtx = None,
                    task: Tag = None,
                    selector: Selector = None,
                    inline_behaviors: Iterable[Behavior] = None
                    ) -> Iterator[CallReceipt]:

        if task is not None:
            selector = selector or Selector()
            selector = selector.with_attrib(task=task)

        # selector from task, sort_key from prio, seq
        # if inline behaviors or ctx carries dispatch layers
        #   do a chain_find_all
        behaviors = self.find_all(selector=selector,
                                  sort_key=lambda v: v.sort_key)
        return self._get_receipts(behaviors, call_args=call_args, call_kwargs=call_kwargs, ctx=ctx)

    @classmethod
    def chain_execute(cls, *registries, call_args = None, call_kwargs = None, ctx = None, task = None, selector) -> Iterator[CallReceipt]:
        if task is not None:
            selector = selector or Selector()
            selector = selector.with_attrib(task=task)

        behaviors = cls.chain_find_all(
            *registries,
            selector=selector,
            sort_key=lambda v: v.sort_key)
        return cls._get_receipts(behaviors, call_args=call_args, call_kwargs=call_kwargs, ctx=ctx)
