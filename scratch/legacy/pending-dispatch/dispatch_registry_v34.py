from __future__ import annotations
from typing import Type, Self, ClassVar, Iterator, Literal, Any, Mapping, Optional
from itertools import chain
import logging
import heapq
from collections import ChainMap
from datetime import datetime, timedelta

from pydantic import model_validator, Field, field_validator, PrivateAttr

from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Registry
from .handler import Handler, HandlerCallReceipt

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

receipt_logger = logging.getLogger("tangl.core.handler.service_receipt")

class ServiceCallReceipt(Entity):
    """
    These objects are similar to fragments in that they exist on the graph,
    but have no knowledge of the graph.  They serialize by value.
    """
    # This needs to be created in the orchestrator `_exec_many` and finalized on exit
    service: str   # HandlerRegistry
    aggregator: AggregationStrategy
    caller: Entity
    initial_ctx: Optional[StringMap] = Field(default=None, exclude=True)  # would need a copy
    # matched_handlers: list[Handler] = Field(default_factory=list)
    # ordered by sort key, there may be _more_ matched handlers than the number of results
    # returned, if there is an early exit
    # don't do this -- handlers is an iterator, reading it out to create this will empty it
    ts: datetime = Field(default_factory=datetime.now)
    handler_receipts: list[HandlerCallReceipt] = Field(default_factory=list)
    final_result: Any = Field(default=None)
    # after aggregation strategy applied
    final_ctx_delta: Optional[StringMap] = Field(default=None, exclude=True)
    # Only want to indicate what is different
    processing_time: timedelta = Field(default_factory=datetime.now)

    def __repr__(self):
        """<ServiceCallReceipt:gather_context>"""
        return f"<{self.__class__.__name__}:{self.label_ or self.service}>"

    def summary_repr(self, max_len=-1, max_items=-1) -> str:
        """<svc:gather_context(<Entity:abc>)->[<h:my_func()->1>,<h:my_func()->2>,...]>"""
        label = f"svc:{self.label_ or self.service}"
        data = self.caller.summary_repr()
        if max_items > 0:
            receipts = self.handler_receipts[:max_items]
        else:
            receipts = self.handler_receipts
        result = "[" + ", ".join([h.summary_repr() for h in receipts]) + "]"
        return f"<{label}({data})->{result}>"


AggregationStrategy = Literal["gather", "merge", "pipeline", "all_true", "first", "iter"]

# todo: Consider if instance-bound methods should be limited to singletons to avoid
#       serialization/deserialization issues?

class HandlerRegistry(Registry[Handler]):
    """
    HandlerRegistry provides a "contextual dispatch" system.  It resolves and
    executes an ordered list of functions for a task and calling class based on:

    - Behavioral grouping ("task" handlers)
    - Class hierarchy (MRO)
    - External categorization ("domain" plugins)

    It can also finalize the result in several different ways, from returning
    the entire list of results, an iterator of method calls, to flattening to a
    single primitive type.

    Functions can be registered directly or using a decorator.
    """
    ### REGISTRATION ###
    registration_count: ClassVar[int] = 0

    @classmethod
    def incr_registration_count(cls) -> int:
        cls.registration_count += 1
        return cls.registration_count

    def register(self, **kwargs):
        # decorator wrapper
        return Handler.define(registry=self, **kwargs)

    def add(self, item: Handler, owner: Entity = None):

        # Check if it's bindable
        if item.requires_binding:
            if owner is None:
                raise RuntimeError(f"owner inst cannot be None for inst method handler {item!r}")
            elif not isinstance(owner, Entity):
                raise RuntimeError(f"owner inst must be Entity, not {type(owner)} for inst method handler {item!r}")
            item = item.bind_to(owner)  # this copies and binds func as a partial with inst if possible
        elif owner is not None:
            raise RuntimeError(f"owner inst {owner!r} cannot be assigned for non-instance method handler {item!r}")

        # check if it's already registered
        if item.registration_order > 0:
            # skip, idempotent registration
            return
        item.registration_order = self.incr_registration_count()

        super().add(item)

    @classmethod
    def annotate_class_handlers(cls, owner_cls: Type[Entity]):
        # This check doesn't work, comes up with a pydantic metaclass
        # if not issubclass(Entity, owner_cls):
        #     raise RuntimeError(f"owner cls must be Type[Entity], not {type(owner_cls)}")
        for item in vars(owner_cls).values():
            logger.debug(f"checking {item!r} for _handler")
            if (h := getattr(item, "_handler", None)) is not None:
                logger.debug(f"handler {h!r} updating cls")
                h.owner_cls = owner_cls

    @classmethod
    def register_instance_handlers(cls, owner: Entity = None, default_registry: Self = None, **criteria) -> None:
        """
        Call in a model validator/post-init process to finalize owner-bound
        instance methods.

        criteria filters for which handlers to try and register.
        """
        if not isinstance(owner, Entity):
            raise RuntimeError(f"owner inst must be Entity, not {type(owner)}")

        # logger.debug(f"looking at attribs on owner {owner.__class__.__mro__!r}")
        # logger.debug(list(chain.from_iterable(vars(_cls).keys() for _cls in owner.__class__.__mro__)))
        for item in chain.from_iterable(list(vars(_cls).values()) for _cls in owner.__class__.__mro__):
            # logger.debug(f"looking for inst handler on {item!r}")
            if (h := getattr(item, "_handler", None)) is not None:
                if not h.matches(**criteria):
                    continue
                # want to consider h

                # try to bind it
                if h.requires_binding:
                    h = h.bind_to(owner)

                # check for a registry annotation or default registry kwarg
                reg = getattr(item, "_handler_registry", None) or default_registry
                if reg is None:
                    logger.warning(f"handler {h!r} matched for registration, but no registry could be identified, skipping, this is probably not what you intended")
                    continue

                # try to register it
                reg.add(h)

    ### DISCOVERY ###

    @classmethod
    def _filt(cls, h: Handler, *, caller: Entity, ctx: StringMap, **criteria) -> bool:
        return h.matches(**criteria) and \
               h.matches_caller(caller) # and \
               # h.is_satisfied(ctx)

    def find_all_for(self, caller: Entity, *, ctx: StringMap, extra_handlers=None, **criteria) -> Iterator[Handler]:
        # There are 2 types of criteria here:
        # - criteria for the _handler_ to activate
        # - criteria for the _calling entity_ to access the handler
        handlers = self.find_all(sort_key=lambda h: h.sort_key(caller=caller),
                                 filt=lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria))
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        return handlers
    
    ### PHASED/PIPELINE EXECUTION ###

    def _merge_handlers(self,
                        caller: Entity,
                        *handlers: Iterator[Handler]) -> Iterator[Handler]:
        # assumes sorted input
        import heapq
        return heapq.merge(handlers, key=lambda h: h.sort_key(caller=caller))

    # handler registries may define a default execute_all strategy
    aggregation_strategy: AggregationStrategy = "gather"

    def execute_all_for(self,
                        caller: Entity, *, ctx: StringMap,
                        strategy: AggregationStrategy = None,
                        extra_handlers: list[Handler] = None,
                        **criteria):
        handlers = self.find_all_for(caller, ctx=ctx, **criteria)
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: self._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        strategy = strategy or self.aggregation_strategy
        return self._execute_many(handlers, caller, strategy=strategy, ctx=ctx, service_name=self.label)

    @classmethod
    def chain_execute_all_for(cls,
                              caller: Entity,
                              *registries: Self,
                              ctx: StringMap,
                              strategy: AggregationStrategy,  # No self.aggregation_strategy, so force explicit
                              extra_handlers: list[Handler] = None,
                              **criteria):
        handlers = cls.chain_find_all_for(caller, *registries, ctx=ctx, **criteria)
        if extra_handlers:
            extra_handlers = sorted(filter(lambda h: cls._filt(h, caller=caller, ctx=ctx, **criteria), extra_handlers), key=lambda h: h.sort_key(caller=caller))
            handlers = heapq.merge(handlers, extra_handlers)
        strategy = strategy or cls.aggregation_strategy
        # todo: check if all registry labels have the same prefix maybe?
        service_name = registries[0].label
        return cls._execute_many(handlers, caller, strategy=strategy, ctx=ctx, service_name=service_name)

    @classmethod
    def _execute_many(cls, handlers: list[Handler], caller: Entity, *, strategy: AggregationStrategy, ctx: StringMap, service_name: str = "anon"):
        # assumes handlers have been sorted and filtered before getting here

        logger.debug(f"Calling many handlers with strategy {strategy}.")
        tic = datetime.now()

        match strategy:
            case "gather":
                # Gather and merge all results if they are all the same type (list or dict)
                receipts = cls._call_handlers(handlers, caller, ctx=ctx)
                final_result = [ receipt.result for receipt in receipts if receipt.result is not None  ]
            case "merge":
                logger.debug(f"Merging results.")
                # gather, if all the same type, list or dict, merge into a single result
                receipts = cls._call_handlers(handlers, caller, ctx=ctx)
                results = [ receipt.result for receipt in receipts if receipt.result is not None  ]
                logger.debug(f"Results: {results}")
                if all([isinstance(r, Mapping) for r in results]):
                    final_result = ChainMap(*reversed(results))
                elif all([isinstance(r, list) for r in results]):
                    final_result = list(chain.from_iterable(results))
                else:
                    logger.warning(f"Unable to merge results of different types {[(type(r), r) for r in results]}.")
                    final_result = results
            case "pipeline":
                # Return _last_ non-None result, feed prior results forward as kwarg/ctx field
                receipts = cls._call_pipeline(handlers, caller, ctx=ctx)
                final_result = receipts[-1].result
            case "all_true":
                # Confirm no non-None results are Falsy
                # todo: implement early exit
                receipts = cls._call_handlers(handlers, caller, ctx=ctx)
                results = [ receipt.result for receipt in receipts if receipt.result is not None ]
                final_result = all(results)
            case "first":
                # Return first non-None result
                # todo: no logging when using _iter_handlers
                return next(cls._iter_handlers(handlers, caller, ctx=ctx), None)
            case "iter":
                # Return an iterator of raw call results for aggregation elsewhere
                # todo: no logging when using _iter_handlers
                return cls._iter_handlers(handlers, caller, ctx=ctx)
            case _:
                raise ValueError(f"Unknown aggregation strategy: {strategy}")

        # todo: need to pass in the service/service name at least
        #       this is a class func, so we've lost self
        receipt = ServiceCallReceipt(
            service=service_name,
            aggregator=strategy,
            caller=caller,
            ts=tic,
            processing_time=datetime.now() - tic,
            handler_receipts=receipts,
            final_result=final_result
        )
        logger.debug(f"Created service receipt {receipt!r}.")
        receipt_logger.debug(receipt.summary_repr())
        if hasattr(caller, 'collect_receipt'):
            caller.collect_receipt(receipt)  # this is on 'HasHandlers'
        return final_result

    @classmethod
    def _call_handlers(cls, handlers: list[Handler], caller: Entity, *, ctx: StringMap) -> list[HandlerCallReceipt]:
        receipts = []
        for h in handlers:
            logger.debug(f"Calling handler {h}")
            receipt = h(caller, ctx=ctx)
            logger.debug(f"Got handler receipt {receipt!r}.")
            receipts.append(receipt)
        return receipts

    @classmethod
    def _call_pipeline(cls, handlers: list[Handler], caller: Entity, *, ctx: StringMap) -> list[HandlerCallReceipt[StringMap]]:
        receipts = []
        for h in handlers:
            receipt = h(caller, ctx=ctx)
            receipts.append(receipt)
            if receipt.result is not None:
                ctx.update(receipt.result)
        return receipts

    @classmethod
    def _iter_handlers(cls, handlers: list[Handler], caller: Entity, *, ctx: StringMap) -> Iterator[Any]:
        # todo: where do we keep the receipts since there is no aggregator and
        #       we are using result directly?
        for h in handlers:
            receipt = h(caller, ctx=ctx)
            if receipt.result is not None:
                yield receipt.result


class HasHandlers(Entity):
    """
    Mixin or automatic annotation on class handlers and binding for owner-instance handlers.
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        logger.debug(f"Updating class ownership for {cls}")
        HandlerRegistry.annotate_class_handlers(cls)
        super().__init_subclass__(**kwargs)

    @model_validator(mode="after")
    def _register_instance_handlers(self):
        logger.debug("Checking instance handlers")
        HandlerRegistry.register_instance_handlers(self, requires_binding=True)
        return self

    # todo: there is no need to include service receipts in serialization for now, I think
    _receipts: dict[str, ServiceCallReceipt] = PrivateAttr(default_factory=dict)
    def collect_receipt(self, receipt: ServiceCallReceipt):
        self._receipts[receipt.service] = receipt

    # def __del__(self):
    #     # todo: unregister on del
    #     # Only want to remove this instance's bound handlers
    #     HandlerRegistry.unregister_instance_handlers(self, requires_binding=True)
