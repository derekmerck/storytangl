from __future__ import annotations
from typing import Any, Mapping, ClassVar, Callable, Literal, Type, TypeVar, Generic, Iterator, overload
from functools import cached_property, total_ordering
from dataclasses import dataclass, field
from uuid import UUID, uuid4
from collections import ChainMap
from itertools import chain

Namespace = dict[str, Any]

@dataclass
class Entity:
    label: str = None
    uid: UUID = field(default_factory=uuid4)

    def match(self, **criteria) -> bool:
        for k, v in criteria.items():
            if getattr(self, k, None) != v:
                return False
        return True

RegistryT = TypeVar("RegistryT", bound=Entity)

@dataclass
class Registry(Entity, Generic[RegistryT]):
    data: dict = field(default_factory=dict)

    def add(self, entity: RegistryT) -> None:
        self.data[entity.uid] = entity

    def find(self, **criteria: Any) -> list[RegistryT]:
        return [item for item in self.data.values() if self.match(**criteria)]


CallType = Literal['static', 'inst', 'class', 'indirect', 'structural', 'domain', 'global']
"""
Types of caller sigs:

- static:     func( caller, ctx ), dist = 999
- inst:       caller.func( ctx ), dist = mro dist func owner cls
- class:      owner_cls.func( caller, ctx ), dist = mro dist expected caller class
- indirect:   owner.func( caller, ctx ) -> result, dist = 999
- structural: indirect, dist = owner ancestor distance from caller
- domain:     indirect, dist = owner index in declared domain order
- global:     special domain singleton
"""
# todo: all these distances seem like a lot of work for collisions that will happen very rarely if
#       priorities are assigned conscientiously and services broken up by phase

ResultT = TypeVar('ResultT', bound=(bool, dict, list, Entity))
SortKey = tuple[int, ...]

@total_ordering
@dataclass
class Handler(Entity, Generic[ResultT]):
    func: Callable[..., ResultT] = lambda: True  # sig will be as required for call type
    registration_order: int = -1
    priority: int = -1
    service: str = None              # service should match this
    owner_cls: Type[Entity] = None   # for binding
    caller_cls: Type[Entity] = None  # caller should match
    call_type: CallType = None       # determines binding, req arguments

    @dataclass
    class HandlerReceipt(Generic[ResultT]):
        handler: Handler[ResultT]
        sort_key: SortKey
        caller: Entity
        ns: Namespace
        result: ResultT
        owner: Entity = None  # if this is a delegated type

    def execute(self, caller: Entity, ns: Namespace, owner: Entity = None) -> ResultT:
        match self.call_type:
            case ('static', 'inst', 'class'):
                result = self.func(caller, ns)  # i.e. func(caller, ctx) or caller.func(ctx)
            case ('indirect', 'structural', 'domain', 'global'):
                if not owner:
                    # if it's a domain singleton, we can find it if we know which label?
                    raise ValueError("Delegate call type must indicate handler owner")
                # this was previously the binding with a weak-ref trick
                result = self.func(owner, caller, ns)  # i.e. owner.func( caller, ctx )
            case _:
                raise ValueError(f"Bad call type {self.call_type} for handler {self!r}")

        return self.HandlerReceipt(
            handler=self,
            sort_key=self.sort_key(caller, owner),
            caller=caller,
            owner=owner,      # Only if it's an indirect handler
            ns=ns,
            result=result,
        )

    def sort_key(self, caller: Entity = None, owner: Entity = None) -> SortKey:
        if caller is None:
            caller_dist = 999  # assume it's at global dist
        else:
            # Figure out which caller distance to use
            match self.call_type:
                case "class":
                    # include mro distance of owner class to caller's class
                    caller_dist = ...
                case "structure":
                    if not owner:
                        raise ValueError("Delegate call type must indicate handler owner")
                    # include ancestor distance of owner inst to caller
                    caller_dist = ...
                case "domain":
                    if not owner:
                        raise ValueError("Delegate call type must indicate handler owner")
                    # use distance index of domain in the domain declarations
                    caller_dist = ...
                case _:
                    caller_dist = 999
        return self.priority, caller_dist, self.registration_order

    def __lt__(self, other: Handler) -> bool:
        # Use priority and registration order alone
        return self.sort_key() < other.sort_key()


@dataclass
class HandlerProvider(Registry[Handler]):
    """
    Can serve a single service or multiple
    Can serve homogeneous callers (common ancestor classes) or heterogeneous (out of class controller)
    """
    # todo: is it useful to track the expected handlers service and caller types?

    _registration_counter: ClassVar[int] = 0

    def add(self, handler: Handler) -> None:
        HandlerProvider._registration_counter += 1
        handler.registration_counter = HandlerProvider._registration_counter
        super().add(handler)

    def register(self, service: str, priority: int = -1):
        def dec(func):
            h = Handler(label=func.__name__, service=service, func=func, priority=priority)
            self.add(h)
        return dec

# Is this like a map-reduce pattern?
AggregationStrategy = Literal["gather", "merge", "unique", "pipe", "all_true", "first", "iter"]
# There are 3 different processing patterns:
# - always do them all: gather, merge -> all receipts, agg result
# - do until true or false: all_true, first -> iter[Receipt] -> truncated receipts, last result
# - do next: iter -> iter[Receipt] -> iterator of receipts, None
# - feed forward, get last: pipe/reduce -> for h in handlers: result = h(result) -> all receipts, last result

@dataclass
class ServiceDispatch:
    # todo: is it in itself a class service registry for a single service with heterogeneous callers?
    """
    Service.dispatch(Entity, ...) goes through a bootstrapping process:
    - discover all providers and their delegates for the entity
    - gather the entity namespace by invoking provider gather ns services
    - invoke provider service handlers with namespace
    """

    @classmethod
    def gather_providers(cls, caller: Entity) -> list[HandlerProvider]:
        # todo: ns independent, check explicit and implicit scopes for handler registries
        ...

    @classmethod
    def gather_namespace(cls, caller: Entity, providers: list[HandlerProvider], extra_handlers: list[Handler] = None) -> Namespace:
        # the service name and agg strategy is hardcoded for bootstrapping other calls
        handlers = cls.gather_handlers(caller, None, providers, extra_handlers=extra_handlers, service="gather_ns")
        receipts = cls.iter_handlers(caller, None, handlers)
        return ChainMap(*receipts)

    @classmethod
    def gather_handlers(cls, caller: Entity, ns: Namespace, providers: list[HandlerProvider], extra_handlers: list[Handler], **criteria) -> list[Handler]:
        handlers = []
        # todo: use entity and ns, entity.match(**handler_criteria) and handler.satisfied(ns) if we have ns
        #       need to gather or bind owner as well..., handler + owner instance for subgraph, for example
        for provider in providers:
            handlers.extend(provider.find(**criteria))
        if extra_handlers is not None:
            for handler in extra_handlers:
                if handler.match(**criteria):
                    handlers.append(handler)
        return sorted(handlers, key=lambda h: h.sort_key(caller=caller))

    @classmethod
    def iter_handlers(cls, caller: Entity, ns: Namespace, handlers: list[Handler]) -> Iterator[Handler.HandlerReceipt]:
        # how do we include "owner" methods in this, pass in owner with handler...?
        for handler in handlers:
            receipt = handler.execute(caller=caller, ns=ns)
            if receipt.result is not None:
                yield receipt

    @dataclass
    class DispatchReceipt:
        service: ServiceDispatch
        caller: Entity
        providers: list[HandlerProvider]
        ns: Namespace
        result: Any
        handler_receipts: list[Handler.HandlerReceipt]

    def dispatch(self,
                 caller: Entity,
                 ns: Namespace = None,
                 providers: list[HandlerProvider] = None,
                 extra_handlers: list[Handler] = None) -> DispatchReceipt:

        if providers is None:
            # could just assume providers is a func/cached property on the node
            providers = self.gather_providers(caller)  # what does this look like? ns-independent

        if ns is None:
            # could just assume ns is a func/cached property on the node
            ns = self.gather_namespace(caller, providers)

        handlers = self.gather_handlers(caller, ns, providers, extra_handlers=extra_handlers, service=self.service)
        handler_receipts = self.iter_handlers(caller, ns, handlers)

        match self.aggregation_strategy:
            case "gather":
                handler_receipts = [*handler_receipts]  # exhaust iterator
                final_result = [r.result for r in handler_receipts]
            case "merge":
                handler_receipts = [*handler_receipts]  # exhaust iterator
                results = [r.result for r in handler_receipts]
                if all([isinstance(r, Mapping) for r in results]):
                    final_result = ChainMap(*results)
                elif all([isinstance(r, list) for r in results]):
                    final_result = chain.from_iterable(results)
                else:
                    raise ValueError(f"Cannot merge results {results!r}")
            case "unique":
                handler_receipts = [*handler_receipts]  # exhaust iterator
                final_result = set( r.result for r in handler_receipts )
            case "all_true":
                called_receipts = []
                final_result = True
                for c in handler_receipts:
                    called_receipts.append(c)
                    if c.result is False:
                        final_result = False
                        break  # fail and early exit
                receipts = called_receipts
            case "first":
                handler_receipts = [next(handler_receipts)]
                final_result = handler_receipts[-1].result  # redundant
            case "iter":
                # can grab the receipt iterator directly out of the dispatch receipt
                final_result = None
            case _:
                raise ValueError(f"Bad aggregation strategy {self.aggregation_strategy}")

        receipt = self.DispatchReceipt(
            service=self,
            caller=caller,
            providers=providers,
            ns=ns,
            handler_receipts=handler_receipts,
            result=final_result,
        )
        if hasattr(caller, '_service_receipts'):
            caller._service_receipts[self.service] = receipt
        return receipt

    # A service instance just has private defaults and an entry point for the class methods
    service: str = None  # label
    aggregation_strategy: AggregationStrategy = "gather"

    # todo: how do we include our own provider if handlers have been registered with this service instance?

# todo: consider how to swap out the entire service dispatcher instance to mock it for testing, like with context vars for named services

on_gather_providers = ServiceDispatch(service="gather_providers", aggregation_strategy="unique")  # dispatch returns set
on_gather_namespace = ServiceDispatch(service="gather_namespace", aggregation_strategy="merge")   # dispatch returns Namespace

class HasHandlers(Entity):

    cls_provider: ClassVar[HandlerProvider] = HandlerProvider()
    # registry for handlers on multiple services for homogeneous callers in mro
    inst_provider: HandlerProvider = field(default_factory=lambda: HandlerProvider())
    # registry for handlers on multiple services for heterogeneous callers

    @classmethod
    def register_handler(cls,
                         service: str,
                         call_type: CallType = 'inst',
                         priority: int = -1):
        def dec(func):
            h = Handler(
                label=func.__name__,
                service=service,
                call_type = call_type,
                priority=priority)
            setattr(func, "_h", h)
        return dec

    def __init_subclass__(cls):
        cls.cls_providers = HandlerProvider(f'{cls.__name__.lower}_cls_handlers')
        for v in vars(cls).values():
            if h := getattr(v, '_h', None):
                h.owner_cls = cls
                match h.scope_type:
                    case "class":
                        cls.cls_providers.add(h)
                    case "global":
                        global_scope.add(h)
                    # otherwise we can defer direct/instance handlers to later

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._service_receipts = dict[str, ServiceDispatch.DispatchReceipt]

        for k, v in vars(self).items():
            if (h := getattr(v, '_h', None)) and h.scope_type in ["indirect", "domain"]:
                # how do we find domain?  All provider-carrying domains are singletons and discoverable by label?
                # pre-bind it?  No, discover it and bind it to owner when called?
                ...

    # not a decorator
    def register_indirect_handler(self,
                                  func: callable,
                                  service: str,
                                  priority: int = -1):
        h = Handler(
            label=func.__name__,
            service=service,
            call_type = 'indirect',
            priority=priority)
        self.inst_provider.add(h)

    @cached_property
    def providers(self) -> list[HandlerProvider]:
        # could cache this and invalidate it whenever new providers are created
        return on_gather_providers.dispatch(self)

    @cached_property
    def namespace(self) -> Namespace:
        # could cache this and invalidate it whenever relevant providers are changed
        return on_gather_namespace.dispatch(self)


class HasNamespace(HasHandlers):

    locals: dict = field(default_factory=dict)

    @on_gather_namespace.register()
    def _provide_locals(self) -> Namespace:
        return self.locals

    def gather_namespace(self) -> Namespace:
        return on_gather_namespace.dispatch(self)

global_scope = HasNamespace(label='global_scope', locals={'__version__': 'next!'})




