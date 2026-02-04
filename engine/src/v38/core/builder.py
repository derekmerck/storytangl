# from __future__ import annotations
# from typing import Optional, Iterator, TypeVar, Generic, Type
# from enum import Flag, auto
# from copy import deepcopy
#
# from pydantic import Field
#
# from tangl.type_hints import UnstructuredData
# from .entity import Entity
# from .selector import Selector
# from .registry import Registry
# from .record import Record
# from .behavior import Behavior, RTCtx, DeferredReceipt, CallReceipt
# from .singleton import Singleton  #, Token
#
#
# class BuildCtx(RTCtx):
#     def get_requirements(self): ...
#
# class ProvisioningPolicy(Flag):
#     NONE = auto()  # Never try to satisfy
#     EXISTING = auto()  # find one in scope
#     UPDATE = auto()    # find closest in scope and update
#     CREATE = auto()    # find builder in scope and create new
#     ANY = EXISTING | UPDATE | CREATE
#
# class BuildOffer(DeferredReceipt):
#     policy: ProvisioningPolicy = ProvisioningPolicy.CREATE
#     cost: int = 0
#
#     def sort_key(self):
#         return self.cost, self.policy, self.seq
#
#     def accept(self, *args, **kwargs):
#         return self.resolve(*args, **kwargs)
#
# ET = TypeVar("ET", bound=Entity)
#
# # Behavior-like API, returns a deferred receipt, satisfy req -> select for req
# class Builder(Behavior):
#
#     # This is matches
#     def can_satisfy(self, req: Selector) -> bool: ...
#     # This is builder.defer() if it satisfies
#     def get_receipt(self, req: Selector) -> Optional[BuildOffer]: ...
#
#     def defer(self, ctx: BuildCtx) -> BuildOffer: ...
#
# class TemplateBuilder(Builder, Generic[ET]):
#     # semi-instantiated copy
#
#     is_archetype: bool = False  # Reusable builder
#
#     # creates new instances according to a spec
#     def can_satisfy(self, req: Selector) -> bool: ...
#
#     # want selector to compare vs. the _template_ here for most properties
#     kind: Type[ET]
#     template: ET = None
#
#     # @dispatches('on_build')
#     def build(self, **changes) -> ET:
#         return self.template.__replace__(**changes)  # todo: evolve?
#
# class TokenBuilder(Builder):
#     # wraps singletons according to a spec
#     reference_singleton: Singleton
#     def can_satisfy(self, req: Selector) -> bool: ...
#
# # this is the _same_ as a template now
# class EntitySnapshot(Record, Builder):
#     kind: Type[Entity] = Field(..., json_schema_extra={'exclude': True})
#     payload: UnstructuredData
#
#     def is_instance(self, kind: Type) -> bool:
#         if issubclass(kind, self.kind):
#             return True
#         return super().is_instance(kind)
#
#     @classmethod
#     def from_entity(cls, entity: Entity):
#         return cls(kind=entity.__class__,
#                    payload=entity.unstructure())
#
#     def materialize(self):
#         data = deepcopy(self.payload)
#         return self.kind.structure(**data)  # kind already in unstructured data
#
# # class EntityTemplate(Record, Generic[ET]):
# #     # Wrapper that masquerades as an object of the type it instantiates
# #     # Useful for representing objects by schema in a script
# #
# #     kind: Type[ET]
# #     is_archetype: bool = Field(default=False, json_schema_extra={'is_meta': True})
# #
# #     # represents a general class of things or an instance
# #
# #     def is_instance(self, kind: Type) -> bool:
# #         if issubclass(kind, self.kind):
# #             return True
# #         return super().is_instance(kind)
# #
# #     def get_payload(self) -> UnstructuredData:
# #         data = {k: getattr(self, k) for k in self._match_fields(is_meta=False)}
# #         data['kind'] = self.template_kind
# #         return data
#
#
# class Factory(Registry[Builder]):
#
#     def build_all(self, args, kwargs, ctx) -> Iterator[CallReceipt]:
#         builders = self.find_all(selector=Selector.from_req(ctx.get_requirements()), sort_key=lambda v: v.sort_key)
#         yield from (b.build(*args, ctx=ctx, **kwargs) for b in builders)
#
#     def build_one(self, args, kwargs, ctx) -> Optional[CallReceipt]:
#         builder = self.find_one(selector=Selector.from_req(ctx.get_requiremens()), sort_key=lambda v: v.sort_key)
#         if builder is not None:
#             return builder.build(*args, ctx=ctx, **kwargs)
#
#     def get_offers(self, ctx) -> Iterator[BuildOffer]:
#         builders = self.find_all(selector=Selector.from_req(ctx.get_requirements()), sort_key=lambda v: v.sort_key)
#         yield from (b.defer(ctx=ctx) for b in builders)
