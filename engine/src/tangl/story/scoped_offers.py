"""Scoped owned-scene offers and their ordinary Action projections."""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import Field

from tangl.core import EntityTemplate, Node, Priority, Selector
from tangl.vm import Affordance, FindProvisioner, Requirement, TraversableNode, on_provision
from tangl.vm.ctx import VmPhaseCtx
from tangl.vm.provision.provisioner import _next_provision_uid
from tangl.vm.traversable import HasAvailability

from .episode import Action, Block, MenuBlock
from .concepts import Role
from .story_graph import StoryGraph


class ScopedActionOffer(Affordance):
    """A scoped offer carrying a reusable, non-graph Action declaration."""

    action_template: EntityTemplate[Action] = Field(
        json_schema_extra={"include": True, "unstructurable": True},
    )


def add_local_action_offer(
    owner: Block, template: EntityTemplate[Action], *, ctx: VmPhaseCtx | None = None,
) -> ScopedActionOffer:
    """Attach a declaration whose structural scope is this receiving block."""
    return ScopedActionOffer(
        uid=_next_provision_uid(_ctx=ctx),
        registry=owner.graph, predecessor_id=owner.uid, requirement=Requirement(),
        source_requirement=Requirement(uid=owner.uid), action_template=template,
    )


def _scoped_offers(receiver: Block, *, ctx: VmPhaseCtx) -> dict[UUID, ScopedActionOffer]:
    if isinstance(receiver, MenuBlock) and not receiver.auto_provision:
        return {}
    ns = ctx.get_ns(receiver)
    values = [receiver, *ns.values()]
    for name in ("roles", "settings", "role_edges"):
        bindings = ns.get(name)
        if isinstance(bindings, Mapping):
            values.extend(bindings.values())
    owners = {value.uid: value for value in values
              if (isinstance(value, Node) or isinstance(value, Role) and value.provider is not None)
              and receiver.graph.get(value.uid) is value}
    candidates = []
    for owner in owners.values():
        if isinstance(owner, Node):
            edges = owner.edges_out(Selector(has_kind=Affordance))
        else:
            edges = receiver.graph.find_edges(Selector(
                has_kind=Affordance, predecessor_id=owner.uid,
            ))
        candidates.extend(edge for edge in edges if isinstance(edge, ScopedActionOffer))
    contexts = list(receiver.ancestors)
    offers = FindProvisioner(values=candidates).get_scoped_affordance_offers(contexts)
    return {offer.candidate.uid: offer.candidate for offer in offers}


def _target(offer: ScopedActionOffer, receiver: Block) -> TraversableNode | None:
    declaration = offer.action_template.payload
    if declaration.successor_id is not None:
        return receiver.graph.get(declaration.successor_id)
    if declaration.successor_ref == "current":
        return receiver
    if declaration.successor_ref:
        from .fabula.materializer import StoryMaterializer

        return StoryMaterializer()._find_runtime_entity(
            graph=receiver.graph, reference=declaration.successor_ref, kind=TraversableNode,
        )
    return None


def _attached_offer(action: Action, receiver: Block, *, ctx: VmPhaseCtx) -> ScopedActionOffer | None:
    offer = _scoped_offers(receiver, ctx=ctx).get(action.offer_id)
    if offer is None or "retired_offer" in action.tags:
        return None
    if action.templ_hash != offer.action_template.content_hash():
        return None
    target = _target(offer, receiver)
    if target is None or action.successor_id != target.uid:
        return None
    return offer


def offer_is_attached(action: Action, receiver: Block, *, ctx: VmPhaseCtx) -> bool:
    """Read-only check of structural and construction identity."""
    return _attached_offer(action, receiver, ctx=ctx) is not None


def offer_is_eligible(action: Action, receiver: Block, *, ctx: VmPhaseCtx) -> bool:
    """Recheck structure and live offer gates at the actual receiver."""
    offer = _attached_offer(action, receiver, ctx=ctx)
    if offer is None:
        return False
    if not offer.available_for(receiver, ctx=ctx):
        return False
    owner = offer.predecessor
    return not isinstance(owner, HasAvailability) or owner.available_for(receiver, ctx=ctx)


@on_provision(wants_caller_kind=Block, wants_exact_kind=False, priority=Priority.LATE)
def project_scoped_action_offers(
    *, caller: Block, ctx: VmPhaseCtx, _setup: bool = False, **_kw,
) -> None:
    """Reconcile local Actions against the receiver's currently scoped offers."""
    ctx.invalidate_namespaces()
    offers = _scoped_offers(caller, ctx=ctx)
    frozen = isinstance(caller.graph, StoryGraph) and caller.graph.frozen_shape and not _setup
    if frozen:
        actions = {edge.offer_id: edge for edge in caller.edges_out(Selector(has_kind=Action))
                   if edge.offer_id is not None and "retired_offer" not in edge.tags}
        for offer_id, offer in offers.items():
            target = _target(offer, caller)
            action = actions.get(offer_id)
            if ((action is not None and action.templ_hash != offer.action_template.content_hash())
                    or (target is not None and (action is None or action.successor_id != target.uid))):
                raise ValueError(
                    f"Frozen story cannot bind scoped Action offer {offer.get_label()!r} "
                    f"at {caller.get_label()!r}"
                )
        return None
    pinned = set(ctx.get_meta().get("call_stack_ids") or ())
    actions = {}
    for edge in list(caller.edges_out(Selector(has_kind=Action))):
        if edge.offer_id is None:
            continue
        if "retired_offer" in edge.tags:
            if edge.uid not in pinned:
                caller.graph.remove(edge.uid, _ctx=ctx)
            continue
        actions[edge.offer_id] = edge
    for offer_id, action in list(actions.items()):
        offer = offers.get(offer_id)
        target = _target(offer, caller) if offer is not None else None
        if (offer is None or target is None
                or action.templ_hash != offer.action_template.content_hash()
                or action.successor_id != target.uid):
            if action.uid in pinned:
                action.tags = action.tags | {"retired_offer"}
            else:
                caller.graph.remove(action.uid, _ctx=ctx)
            del actions[offer_id]
    for offer_id, offer in offers.items():
        if offer_id not in actions:
            target = _target(offer, caller)
            if target is None:
                continue
            offer.record_source(caller, reattach=caller.uid in offer.source_ids)
            action = offer.action_template.materialize(
                uid=_next_provision_uid(_ctx=ctx),
                predecessor_id=caller.uid,
                successor_id=target.uid,
                offer_id=offer.uid,
            )
            caller.graph.add(action, _ctx=ctx)
    return None
