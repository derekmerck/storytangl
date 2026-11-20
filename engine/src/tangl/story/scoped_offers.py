"""Scoped owned-scene offers and their ordinary Action projections."""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from tangl.core import Node, Priority, Selector
from tangl.vm import Affordance, FindProvisioner, ResolutionPhase, on_provision
from tangl.vm.ctx import VmPhaseCtx
from tangl.vm.traversable import HasAvailability

from .episode import Action, Block, Scene
from .concepts import Role
from .story_graph import StoryGraph


def _scoped_offers(receiver: Block, *, ctx: VmPhaseCtx) -> dict[UUID, Affordance]:
    ns = ctx.get_ns(receiver)
    values = list(ns.values())
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
        candidates.extend(edge for edge in edges if "owned_scene_offer" in edge.tags)
    contexts = list(receiver.ancestors)
    offers = FindProvisioner(values=candidates).get_scoped_affordance_offers(contexts)
    return {offer.candidate.uid: offer.candidate for offer in offers}


def offer_is_eligible(action: Action, receiver: Block, *, ctx: VmPhaseCtx) -> bool:
    """Recheck structure and live offer gates at the actual receiver."""
    offer = _scoped_offers(receiver, ctx=ctx).get(action.offer_id)
    if offer is None or offer.successor_id != action.successor_id:
        return False
    if not offer.available_for(receiver, ctx=ctx):
        return False
    owner = offer.predecessor
    return not isinstance(owner, HasAvailability) or owner.available_for(receiver, ctx=ctx)


@on_provision(wants_caller_kind=Block, wants_exact_kind=False, priority=Priority.LATE)
def project_owned_scene_offers(*, caller: Block, ctx: VmPhaseCtx, **_kw) -> None:
    """Reconcile local Actions against the receiver's currently scoped offers."""
    if isinstance(caller.graph, StoryGraph) and caller.graph.frozen_shape:
        return None
    ctx.invalidate_namespaces()
    offers = _scoped_offers(caller, ctx=ctx)
    actions = {edge.offer_id: edge for edge in caller.edges_out(Selector(has_kind=Action))
               if edge.offer_id is not None}
    for offer_id, action in actions.items():
        if offer_id not in offers:
            caller.graph.remove(action.uid, _ctx=ctx)
    for offer_id, offer in offers.items():
        scene = offer.successor
        if not isinstance(scene, Scene) or scene.offer is None:
            continue
        if offer_id not in actions:
            offer.record_source(caller, reattach=caller.uid in offer.source_ids)
            Action(
                registry=caller.graph, predecessor_id=caller.uid, successor_id=scene.uid,
                offer_id=offer.uid, once=scene.offer.once,
                return_phase=ResolutionPhase.PLANNING,
            )
    return None
