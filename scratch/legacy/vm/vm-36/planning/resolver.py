# tangl/vm/planning/resolver.py
from typing import Protocol, Iterable, Optional
from uuid import UUID

from tangl.vm36.execution.tick import StepContext
from .ticket import ProvisionRequirement, ProvisionOffer


class ProposalResolver(Protocol):
    """Unifies 'find' and 'create' into a single proposal surface."""
    kind: str                 # e.g. "role", "entity", "media"
    weight: int               # tie-breaker (lower = preferred)
    resolver_id: str          # stable, deterministic id for ordering

    def propose(self, g, facts, owner_uid: UUID, spec: ProvisionRequirement) -> Iterable[ProvisionOffer]:
        """Yield zero or more quotes to satisfy `spec`."""

# ---- helpers ---------------------------------------------------------------

# helpers
def _role_req_to_entity_for_find(spec: ProvisionRequirement) -> ProvisionRequirement:
    cons = dict(spec.constraints or {})
    # ensure the 'character' tag but DO NOT force a label
    tags = set(cons.get("tags", set()) or set())
    tags.add("character")
    cons["tags"] = tags
    cons.pop("label", None)  # critical: do not inject label for find
    return ProvisionRequirement(kind="entity", name=spec.name, constraints=cons,
                                policy=spec.policy, meta=spec.meta)

def _role_req_to_entity_for_build(spec: ProvisionRequirement) -> ProvisionRequirement:
    cons = dict(spec.constraints or {})
    tags = set(cons.get("tags", set()) or set())
    tags.add("character")
    cons["tags"] = tags
    # for creation, default label to role name if not provided
    cons.setdefault("label", spec.name)
    return ProvisionRequirement(kind="entity", name=spec.name, constraints=cons,
                                policy=spec.policy, meta=spec.meta)

# ---- generic builder --------------------------

class GenericEntityBuilder:
    kind = "entity"
    weight = 20
    resolver_id = "entity.builder.generic"

    def propose(self, g, facts, owner_uid, spec: ProvisionRequirement):
        cons = dict(spec.constraints or {})
        cls_fqn = cons.pop("cls_fqn", "tangl.core36.entity:Node")
        label = cons.pop("label", None) or spec.name
        tags = set(cons.pop("tags", set()) or set())
        attrs = cons.pop("attrs", {}) or {}

        def _accept(ctx, _owner_uid):
            return ctx.create_node(cls_fqn, label=label, tags=tags, **attrs)

        yield ProvisionOffer(
            resolver_id=self.resolver_id,
            kind=self.kind,
            cost=50,
            label=f"create:{label}",
            existing_uid=None,
            accept=_accept,
            req=spec,
        )

class GenericEntityFinder:
    kind = "entity"
    weight = 40
    resolver_id = "entity.finder.generic"

    def propose(self, g, facts, owner_uid: UUID, spec: ProvisionRequirement):
        cons = dict(spec.constraints or {})
        # Assume g.items.find(**cons) yields Nodes that match label/tags/attrs
        for node in g.items.find(**cons):
            uid = node.uid
            def _accept(ctx: StepContext, _owner: UUID, u=uid) -> UUID:
                # Existing resource; still go through accept for uniformity
                return u
            yield ProvisionOffer(
                resolver_id=self.resolver_id,
                kind=self.kind,
                cost=10,                      # cheaper than create
                label=f"bind:{getattr(node, 'label', uid)}",
                existing_uid=uid,
                accept=_accept,
                req=spec,
            )

class SimpleRoleResolver:
    """Unifies role provisioning by delegating to generic entity finder/builder.
    It returns role-kind quotes, mapping entity quotes to role quotes while
    injecting role semantics (character tag/label).
    """
    kind = "role"
    weight = 15
    resolver_id = "role.resolver.simple"

    def __init__(self, finder: Optional[ProposalResolver] = None, builder: Optional[ProposalResolver] = None):
        self.finder = finder or GenericEntityFinder()
        self.builder = builder or GenericEntityBuilder()

    def propose(self, g, facts, owner_uid, spec: ProvisionRequirement):
        # 1) existing-bind quotes (no label constraint)
        ent_find = _role_req_to_entity_for_find(spec)
        for q in self.finder.propose(g, facts, owner_uid, ent_find) or ():
            guard = getattr(q, "guard", (lambda *_: True))

            def _accept(ctx, owner, qq=q): return qq.accept(ctx, owner)

            yield ProvisionOffer(
                resolver_id=f"{self.resolver_id}+{getattr(self.finder, 'resolver_id', 'finder')}",
                kind="role", cost=q.cost, label=q.label,
                existing_uid=q.existing_uid, accept=_accept, req=spec, guard=guard,
            )

        # 2) create-new quotes (with label defaulted)
        ent_build = _role_req_to_entity_for_build(spec)
        for q in self.builder.propose(g, facts, owner_uid, ent_build) or ():
            guard = getattr(q, "guard", (lambda *_: True))

            def _accept(ctx, owner, qq=q): return qq.accept(ctx, owner)

            yield ProvisionOffer(
                resolver_id=f"{self.resolver_id}+{getattr(self.builder, 'resolver_id', 'builder')}",
                kind="role", cost=q.cost, label=q.label,
                existing_uid=q.existing_uid, accept=_accept, req=spec, guard=guard,
            )
#
# # NOTE: The two classes below are legacy role-specific resolvers. Prefer using
# # `SimpleRoleResolver`, which consolidates both find and create via the generic
# # entity resolver pair.
#
# # ---- role finder (bind existing) --------------------------------------------
#
# class SimpleRoleFinder:
#     kind = "role"
#     weight = 80
#     resolver_id = "role.finder.simple"
#
#     def propose(self, g, facts, owner_uid: UUID, spec: ProvisionRequirement) -> Iterable[ProvisionOffer]:
#         cons = dict(spec.constraints or {})
#         tags = set(cons.get("tags", ()))
#         tags.add("character")
#         cons["tags"] = tags
#         # Assume g.items.find(**cons) yields candidate Node uids
#         for node in g.items.find(**cons):
#             uid = node.uid
#             # existing binding; still require explicit accept for uniformity
#             def _accept(ctx: StepContext, _owner: UUID, u=uid) -> UUID:
#                 return u
#
#             yield ProvisionOffer(
#                 resolver_id=self.resolver_id,
#                 kind=self.kind,
#                 cost=10,                           # cheaper than create
#                 label=f"bind:{uid}",
#                 existing_uid=uid,
#                 accept=_accept,
#                 req=spec,
#             )
#
#
# # ---- role builder (create new) ----------------------------------------------
#
# class SimpleRoleBuilder:
#     kind = "role"
#     weight = 10
#     resolver_id = "role.builder.simple"
#
#     def propose(self, g, facts, owner_uid: UUID, spec: ProvisionRequirement) -> Iterable[ProvisionOffer]:
#         def _accept(ctx: StepContext, _owner: UUID) -> UUID:
#             label = (spec.constraints or {}).get("label") or spec.name
#             return ctx.create_node("tangl.core36.entity:Node", label=label, tags={"character"})
#
#         yield ProvisionOffer(
#             resolver_id=self.resolver_id,
#             kind=self.kind,
#             cost=50,                              # higher than bind
#             label="create:character",
#             existing_uid=None,
#             accept=_accept,
#             req=spec,
#         )