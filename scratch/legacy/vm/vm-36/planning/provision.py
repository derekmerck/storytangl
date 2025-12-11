# tangl/vm/planning/provision.py
from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from tangl.core36 import Node, Graph, Facts, EdgeKind
# from tangl.vm36.execution import StepContext
from .ticket import ProvisionRequirement, ProvisionOffer, ProvisionTicket as ProvisionOutcome
from .resolver import ProposalResolver
# from .specs import ProvisionOutcome  # keep ProvisionOutcome where it lives today


class Provisioner:
    def __init__(self, resolvers_by_kind: dict[str, list[ProposalResolver]]):
        # Sort deterministically by (weight, resolver_id)
        self.by = {
            k: sorted(v, key=lambda r: (r.weight, getattr(r, "resolver_id", "")))
            for k, v in (resolvers_by_kind or {}).items()
        }

    @classmethod
    def from_scope(cls, scope) -> "Provisioner":
        return cls(getattr(scope, "resolvers_by_kind", {}))

    # --- lifecycle ------------------------------------------------------------

    def require(self, ctx: StepContext, owner_uid: UUID, spec: ProvisionRequirement) -> ProvisionOutcome:
        """Create a requirement ticket, solicit quotes, accept the cheapest, bind it."""
        # 1) Ticket node + owner → requires → ticket
        req_uid = ctx.create_node(
            "tangl.core36.entity:Node",
            label=f"require:{spec.kind}:{spec.name}",
            tags={"requirement"},
        )
        ctx.add_edge(owner_uid, req_uid, EdgeKind.REQUIRES)
        ctx.set_attr(req_uid, ("locals", "status"), "pending")
        ctx.set_attr(req_uid, ("locals", "spec"), {
            "kind": spec.kind, "name": spec.name, "policy": dict(spec.policy or {})
        })

        g, facts = ctx.preview(), ctx.facts
        resolvers = self.by.get(spec.kind, [])

        # 2) Gather quotes
        quotes: list[ProvisionOffer] = []
        for r in resolvers:
            try:
                for q in r.propose(g, facts, owner_uid, spec) or ():
                    # Consistent guard: same shape as narrative Offer guard
                    if q.guard(g, facts, ctx, owner_uid):
                        quotes.append(q)
            except Exception:
                # keep discovery resilient; tests will catch resolver bugs
                continue

        # may want more flexible policy filtering later, should include it here,
        # not on the proposal resolvers.

        pol = spec.policy or {}
        create_ok = bool(pol.get("create_if_missing", False))

        # If creation not allowed, keep only bind-existing quotes
        if not create_ok:
            quotes = [q for q in quotes if q.existing_uid is not None]

        # 3) Pick cheapest deterministically
        if quotes:
            chosen = min(
                quotes,
                key=lambda q: (q.cost, getattr(q, "resolver_id", ""), q.quote_id),
            )
            bound_uid = chosen.accept(ctx, owner_uid)

            # 4) Bind: owner --(role:.../req:...)--> bound; bound --(fulfills)--> ticket
            edge_kind = (
                f"{EdgeKind.ROLE.prefix()}{spec.name}"
                if spec.kind == "role"
                else f"req:{spec.kind}:{spec.name}"
            )
            ctx.add_edge(owner_uid, bound_uid, edge_kind)
            ctx.add_edge(bound_uid, req_uid, EdgeKind.FULFILLS)
            ctx.set_attr(req_uid, ("locals", "status"), "bound")
            return ProvisionOutcome(status="bound", bound_uid=bound_uid, requirement_uid=req_uid)

        # 5) Pending vs unsat by policy
        if pol.get("optional") or not pol.get("prune_if_unsatisfied", True):
            return ProvisionOutcome(status="pending", requirement_uid=req_uid)

        ctx.set_attr(req_uid, ("locals", "status"), "unsat")
        return ProvisionOutcome(status="unsat", requirement_uid=req_uid)


# --- Validation helper (edge-centric) ----------------------------------------

def has_unsatisfied_requirements(g: Graph, facts: Facts, owner_uid: UUID) -> bool:
    """
    True if owner has any requirement ticket (owner --(requires)--> R)
    without an inbound fulfills edge (X --(fulfills)--> R).
    """
    owner = g.get(owner_uid)
    if not isinstance(owner, Node):
        return False

    for e in g.find_edges(owner, direction="out", kind=EdgeKind.REQUIRES):
        rid = getattr(e, "dst_id", None) or getattr(e, "dst", None)
        if rid is None:
            continue
        req = g.get(rid)
        if not isinstance(req, Node):
            continue
        st = (req.locals or {}).get("status")
        pol = ((req.locals or {}).get("spec") or {}).get("policy", {})
        prune = bool(pol.get("prune_if_unsatisfied", True))
        if prune and st in {"unsat", "pending"}:
            return True

    return False
