import heapq
from typing import ClassVar, Type, Callable, Any, Literal, Self, Optional, Iterator
from collections import ChainMap
import itertools
import logging

from pydantic import Field

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Registry
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AggregationStrategy = Literal["gather", "merge", "pipeline", "all_true", "first"]


class HandlerRegistry(Registry[BaseHandler]):

    # label_: str = Field(..., alias="label")  # Mandatory now

    # REGISTRATION

    def register(self, **kwargs):
        def decorator(func):
            # Has a defined label
            kwargs.setdefault("service_name", self.label)
            h = BaseHandler(func=func, **kwargs)
            self.add(h)
            return func
        return decorator

    @classmethod
    def mark_register(cls, **kwargs):
        # Defer registering class-level handler definitions
        def decorator(func):
            logger.debug(f"Marking handler {func} for registration.")
            h = BaseHandler(func=func, **kwargs)
            setattr(func, "_register_handler", h)
            return func
        return decorator

    def register_marked_handlers(self, owner_cls: Type[Entity]):
        # This handler registry should manage class handlers for owner_cls
        # todo: This is fragile and promiscuous, it does _not_ filter by criteria,
        #       so the same function annotation might bind to multiple registries.
        #       At a minimum, it should probably check the label of the registry.
        logger.debug(f"Registering marked handlers for {owner_cls}.")
        for name, func in owner_cls.__dict__.items():
            if hasattr(func, "_register_handler"):
                logger.debug(f"-> Registering {func} for {owner_cls}.")
                h = func._register_handler
                if h.service_name is None:
                    h.service_name = self.label
                # This is confusing, we want to test and set the cardinal owner class here
                if h.owner_cls_ is None:
                    h.owner_cls_ = owner_cls
                self.add(h)

    _registration_counter: ClassVar[int] = 0

    def add(self, item: BaseHandler) -> None:
        item.registration_order = HandlerRegistry._registration_counter
        HandlerRegistry._registration_counter += 1
        return super().add(item)

    # SORTED FIND FOR

    @classmethod
    def _filt(cls, h: BaseHandler, *, caller: Entity, ctx: StringMap, **criteria) -> bool:
        return h.matches(**criteria) and \
               caller.matches(has_cls=h.owner_cls, **h.caller_criteria) # and \
               # h.is_satisfied(ctx)

    def find_all_for(self, caller: Entity, *, ctx: StringMap, **criteria) -> Iterator[BaseHandler]:
        # There are 2 types of criteria here:
        # - criteria for the _handler_ to activate
        # - criteria for the _calling entity_ to access the handler
        handlers = self.find_all(sort_key= lambda h: h.sort_key(caller=caller),
                                 filt = lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria))
        return handlers

    # todo: I don't think this will get used, it doesn't find the first non-none handler b/c it's not an execute, and its unclear whether execute first should return the first handler result, or the first non-none result, as everything else does
    def find_first_for(self, caller: Entity, *, ctx: StringMap, **criteria) -> Optional[BaseHandler]:
        return next(self.find_all_for(caller, ctx=ctx, **criteria), None)

    @classmethod
    def chain_find_all_for(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria) -> Iterator[BaseHandler]:
        handlers = cls.chain_find_all(*registries,
                                      sort_key=lambda h: h.sort_key(caller=caller),
                                      filt=lambda h: cls._filt(h, caller=caller, ctx=ctx, **criteria))
        return handlers

    @classmethod
    def chain_find_first_for(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria) -> Optional[BaseHandler]:
        return next(cls.chain_find_all_for(caller, *registries, ctx=ctx, **criteria), None)

    # SORTED EXECUTE FOR

    def _merge_handlers(self,
                        caller: Entity,
                        *handlers: Iterator[BaseHandler]) -> Iterator[BaseHandler]:
        # assumes sorted input
        import heapq
        return heapq.merge(handlers, key=lambda h: h.sort_key(caller=caller))

    # todo: this is maybe clearer as execute_all_for(strategy=first)??
    def execute_first_for(self,
                          caller: Entity, *, ctx: StringMap,
                          extra_handlers: list[BaseHandler] = None,
                          **criteria):
        handlers = self.find_all_for(caller, ctx=ctx, **criteria)
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        self._execute_many(handlers, caller, ctx=ctx, strategy="first")
        h = next(handlers, None)
        if h:
            return h.func(caller, ctx)

    # handler registries may define a default execute_all strategy
    aggregation_strategy: AggregationStrategy = "gather"

    def execute_all_for(self,
                        caller: Entity, *, ctx: StringMap,
                        strategy: AggregationStrategy = None,
                        extra_handlers: list[BaseHandler] = None,
                        **criteria):
        handlers = self.find_all_for(caller, ctx=ctx, **criteria)
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        strategy = strategy or self.aggregation_strategy
        return self._execute_many(handlers, caller, strategy=strategy, ctx=ctx)

    @classmethod
    def chain_execute_all_for(cls,
                              caller: Entity,
                              *registries: Self,
                              ctx: StringMap,
                              strategy: AggregationStrategy,  # No self.aggregation_strategy, so force explicit
                              extra_handlers: list[BaseHandler] = None,
                              **criteria):
        handlers = cls.chain_find_all_for(caller, *registries, ctx=ctx, **criteria)
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: cls._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        strategy = strategy or cls.aggregation_strategy
        return cls._execute_many(handlers, caller, strategy=strategy, ctx=ctx)

    @classmethod
    def _execute_many(cls, handlers: list[BaseHandler], caller: Entity, *, strategy: AggregationStrategy, ctx: StringMap):
        # assumes handlers have been sorted and filtered before getting here

        logger.debug(f"Calling many handlers with strategy {strategy}.")
        match strategy:
            case "gather":
                # Gather and merge all results if they are all the same type (list or dict)
                return cls._call_handlers(handlers, caller, ctx=ctx)
            case "merge":
                logger.debug(f"Merging results.")
                # gather, if all the same type, list or dict, merge into a single result
                results = cls._call_handlers(handlers, caller, ctx=ctx)
                if all([isinstance(r, dict) for r in results]):
                    return ChainMap(*reversed(results))
                if all([isinstance(r, list) for r in results]):
                    return list(itertools.chain.from_iterable(results))
                logger.warning(f"Unable to merge results of different types {[(type(r), r) for r in results]}.")
                return results
            case "pipeline":
                # Return _last_ non-None result, feed prior results forward as kwarg/ctx field
                return cls._call_pipeline(handlers, caller, ctx=ctx)
            case "all_true":
                # Confirm no non-None results are Falsy
                return all(cls._call_handlers(handlers, caller, ctx=ctx))
            case "first":
                # Return first non-None result
                return next(cls._iter_handlers(handlers, caller, ctx=ctx), None)
            case "iter":
                # Return an iterator of raw call results for aggregation elsewhere
                return cls._iter_handlers(handlers, caller, ctx=ctx)
            case _:
                raise ValueError(f"Unknown aggregation strategy: {strategy}")

    @classmethod
    def _call_handlers(cls, handlers: list[BaseHandler], caller: Entity, *, ctx: StringMap) -> list[Any]:
        results = []
        for h in handlers:
            result = h.func(caller, ctx)
            if result is not None:
                results.append(result)
        return results

    @classmethod
    def _call_pipeline(cls, handlers: list[BaseHandler], caller: Entity, *, ctx: StringMap) -> StringMap:
        for h in handlers:
            result = h.func(caller, ctx)
            if result is not None:
                ctx.update(result)
        return ctx

    @classmethod
    def _iter_handlers(cls, handlers: list[BaseHandler], entity, *, ctx: StringMap) -> Iterator[Any]:
        for h in handlers:
            result = h.func(entity, ctx)
            if result is not None:
                yield result
