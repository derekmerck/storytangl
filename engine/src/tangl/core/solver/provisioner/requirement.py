from typing import Generic, TypeVar, Optional
from uuid import UUID

from pydantic import Field, field_validator

from tangl.type_hints import StringMap
from tangl.core.entity import Node, Graph  # Graph req for pydantic
from tangl.core.dispatch import HandlerRegistry, HandlerPriority as Priority
from tangl.core.handler import Satisfiable, Predicate
from .template import EntityTemplate

#### HANDLERS ####

on_provision_requirement = HandlerRegistry(
    label="provision_requirement", aggregation_strategy="first")
"""
The global pipeline for provisioning requirements. Handlers for resolving 
requirements should decorate methods with ``@on_provision_requirement.register(...)``.
"""

NodeT = TypeVar("NodeT", bound=Node)

class HasRequirement(Satisfiable, Node, Generic[NodeT]):

    provider_id: Optional[UUID] = None
    req_criteria: Optional[StringMap] = Field(default_factory=dict)
    req_predicate: Optional[Predicate] = Field(None)
    is_unresolvable: bool = False  # tried to resolve but failed
    hard_requirement: bool = True
    fallback_template: EntityTemplate = None

    @field_validator("fallback_template", mode="before")
    def _cast_fallback_template(cls, v):
        if isinstance(v, dict):
            v = EntityTemplate(data=v)
        return v

    @property
    def provider(self) -> NodeT:
        if self.provider_id is not None:
            return self.graph.get(self.provider_id)
        return None

    @provider.setter
    def provider(self, value: NodeT | None):
        if value is not None:
            if value not in self.graph:
                self.graph.add(value)
            self.provider_id = value.uid
        else:
            self.provider_id = None

    @property
    def is_resolved(self) -> bool:
        # Note: resolvability is _not_ part of satisfied/available.
        # - Satisfied on the req is for if the req is _active_
        # - Resolved is for if it has been _linked_
        # - Satisfied on the owner is _either_ dep is inactive or dep is active and linked
        return self.provider is not None or not self.hard_requirement

    def resolve_requirement(self, ctx: StringMap = None) -> bool:
        if self.provider is not None:
            raise RuntimeError("Can not reprovision without clearing provider first")

        ctx = ctx or self.gather_context()
        provider = on_provision_requirement.execute_all_for(self, ctx=ctx)
        # this checks satisfied, matches, and tries to create and register

        if provider is not None:
            self.provider = provider
        else:
            self.is_unresolvable = True

        return self.is_resolved

    # todo: this is an ad hoc implementation, should do it more carefully with scopes,
    #       but it should work for now.
    #       Idea is to look for an existing node, then a template, then invoke fallback.

    @on_provision_requirement.register(priority=Priority.EARLY)
    def _check_graph_for_existing(self, *, ctx: StringMap) -> NodeT | None:
        # todo: Should make a scoped search provider that matches on "in_scope=graph"
        # todo: inject NodeT into criteria as default
        candidates = self.graph.find_all(**self.req_criteria)
        # todo: filter by req_predicate(req.ctx)?
        candidates = list(candidates)
        if len(candidates) > 0:
            return candidates[0]

    @on_provision_requirement.register(priority=Priority.LATE)
    def _check_domain_for_template(self, *, ctx: StringMap) -> NodeT | None:
        # todo: Should make domain scoped build provider that matches on "in_scope=domain"
        # this is where the domain template registry should be defined
        if hasattr(self, "domain") and hasattr(self.domain, "provision"):
            return self.domain.provision(criteria=self.req_criteria)

    @on_provision_requirement.register(priority=Priority.LAST)
    def _use_fallback_template(self, *, ctx: StringMap) -> NodeT | None:
        from .template import EntityTemplate
        if self.fallback_template is not None:
            # this just calls structure, but we can use NodeTemplate for consistency
            # todo: inject NodeT into the template as obj_cls default
            return self.fallback_template.build()
