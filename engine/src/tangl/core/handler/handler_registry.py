from typing import ClassVar, Type, Callable, Any, Literal, Self, Optional, Iterator
from collections import ChainMap
import itertools
import logging

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Registry
from tangl.core.entity.registry import RegistryP
from .base_handler import BaseHandler, BaseHandlerP

logger = logging.getLogger(__name__)

AggregationStrategy = Literal["gather", "merge", "pipeline", "all_true", "first"]

class HandlerRegistryP(RegistryP[BaseHandlerP]):

    # REGISTRATION
    def register(self, **kwargs) -> Callable: ...      # instance decorator
    @classmethod
    def mark_register(cls, **kwargs) -> Callable: ...  # sub-class decorator
    @classmethod
    def register_marked(cls, caller_cls: Type[Entity]): ...  # sub-class init discovery

    # DISCOVERY
    def find_all_for(self, entity: Entity, *, ctx: StringMap, **criteria) -> Iterator[BaseHandlerP]: ...
    def find_first_for(self, entity: Entity, *, ctx: StringMap, **criteria) -> Optional[BaseHandlerP]: ...
    @classmethod
    def chain_find_all_for(cls, entity: Entity, *registries: Self, ctx: StringMap, **criteria) -> Iterator[BaseHandlerP]: ...
    @classmethod
    def chain_find_first_for(cls, entity: Entity, *registries: Self, ctx: StringMap, **criteria) -> Iterator[BaseHandlerP]: ...

    # EXECUTION

    def execute_first(self, caller: Entity, *, ctx: StringMap, **criteria): ...
    @classmethod
    def chain_execute_first(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria): ...

    default_aggregation_strategy: AggregationStrategy
    def execute_all(self, caller: Entity, *, ctx: StringMap, strategy: AggregationStrategy = None, **criteria): ...
    @classmethod
    def chain_execute_all(cls, caller: Entity, *registries: Self, ctx: StringMap, strategy: AggregationStrategy = None, **criteria): ...


class HandlerRegistry(Registry[BaseHandler]):

    # REGISTRATION

    def register(self, **kwargs):
        def decorator(func):
            h = BaseHandler(func=func, **kwargs)
            self.add(h)
            return func
        return decorator

    @classmethod
    def mark_register(cls, **kwargs):
        # Defer registering class-level handler definitions
        def decorator(func):
            h = BaseHandler(func=func, **kwargs)
            setattr(func, "_register_handler", h)
            return func
        return decorator

    def register_marked_handlers(self, owner_cls):
        # This handler registry should manage class handlers for owner_cls
        for name, func in vars(owner_cls).items():
            if hasattr(func, "_register_handler"):
                h = func._register_handler
                if not h.owner_class:
                    h.owner_class = owner_cls
                self.add(h)

    _global_registration_counter: ClassVar[int] = 0

    def add(self, item: BaseHandler) -> None:
        item.registration_order = HandlerRegistry._global_registration_counter
        HandlerRegistry._global_registration_counter += 1
        return super().add(item)

    # SORTED FIND FOR

    def find_all_for(self, caller: Entity, *, ctx: StringMap, **criteria) -> Iterator[BaseHandler]:
        # There are 2 types of criteria here:
        # - criteria for the _handler_ to activate
        # - criteria for the _calling entity_ to access the handler
        criteria = criteria or {}
        handlers = self.find_all(sort_key=lambda x: x.sort_key(caller=caller),
                                 filt = lambda x: caller.matches(**x.caller_criteria),
                                 **criteria, has_owner_cls=caller)
        return handlers

    def find_first_for(self, caller: Entity, *, ctx: StringMap, **criteria) -> Optional[BaseHandler]:
        return next(self.find_all_for(caller, ctx=ctx, **criteria), None)

    @classmethod
    def chain_find_all_for(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria) -> Iterator[BaseHandler]:
        criteria = criteria or {}
        # todo: add criteria/filters, entity matches handler criteria, has class handler wants, ctx satisfied on h
        criteria.update({})
        return cls.chain_find_all(*registries, sort_key=lambda x: x.sort_key(caller=caller), **criteria)

    @classmethod
    def chain_find_first_for(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria) -> Optional[BaseHandler]:
        return next(cls.chain_find_all_for(caller, *registries, ctx=ctx, **criteria), None)

    # EXECUTION

    # todo: should this return the result of the first handler period, like for a named handler
    #       with a single registration (original intent), or the first non-None result if any?
    def execute_first(self, caller: Entity, *, ctx: StringMap, **criteria):
        h = self.find_first_for(caller, ctx=ctx, **criteria)
        return h.func(caller, ctx)

    @classmethod
    def chain_execute_first(cls, caller: Entity, *registries: Self, ctx: StringMap, **criteria):
        h = cls.chain_find_first_for(caller, *registries, **criteria)
        return h.func(caller, ctx)

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

    # handler registries may define a default kind if they expect to be homogeneous wrt kind
    default_aggregation_strategy: AggregationStrategy = "gather"

    @classmethod
    def _execute_many(cls, handlers: list[BaseHandler], caller: Entity, *, strategy: AggregationStrategy, ctx: StringMap):

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

    def execute_all(self, caller: Entity, *, ctx: StringMap,
                    strategy: AggregationStrategy = None,
                    extra_handlers: list[BaseHandler] = None,
                    **criteria):
        handlers = self.find_all_for(caller, ctx=ctx, **criteria)
        if extra_handlers:
            def filt_(h: BaseHandler) -> bool:
                nonlocal caller
                return h.matches(**criteria, has_owner_cls=caller) and caller.matches(**h.caller_criteria)
            extra_handlers = filter(filt_, extra_handlers)
            handlers = sorted(itertools.chain(handlers, extra_handlers),
                              key=lambda x: x.sort_key(caller=caller))
        strategy = strategy or self.default_aggregation_strategy
        return self._execute_many(handlers, caller, strategy=strategy, ctx=ctx)

    @classmethod
    def chain_execute_all(cls, caller: Entity, *registries: Self, ctx: StringMap, strategy: AggregationStrategy = None, **criteria):
        handlers = cls.chain_find_all_for(caller, *registries, ctx, **criteria)
        strategy = strategy or cls.default_aggregation_strategy
        return cls._execute_many(handlers, caller, strategy=strategy, ctx=ctx)
