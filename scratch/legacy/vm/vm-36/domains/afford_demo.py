# tangl/domains/afford_demo.py
from __future__ import annotations
from uuid import UUID
from typing import Iterable

from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.core36.types import EdgeKind
from tangl.vm36.planning.provision import ProvisionRequirement
from tangl.vm36.planning.offers import Offer

def _role_target(g: Graph, owner_uid: UUID, role: str) -> UUID | None:
    owner = g.get(owner_uid)
    if not isinstance(owner, Node): return None
    for e in g.find_edges(owner, direction="out", kind=f"{EdgeKind.ROLE.prefix()}{role}"):
        return e.dst_id
    return None

# ---- Annie hint affordance ----

class AnnieHintProvider:
    """
    When a scene has a villain bound (Annie), attach a one-time hint affordance
    from Annie -> scene and add a transition when enabled.
    """
    def enumerate(self, g, facts, ctx, anchor_uid) -> Iterable[Offer]:
        # Find first villain bound to this scene
        villain_uid = None
        for eid in g.find_edge_ids(src=anchor_uid, kind=f"{EdgeKind.ROLE.prefix()}villain"):
            e = g.get(eid)
            villain_uid = getattr(e, "dst_id", None) or getattr(e, "dst", None)
            if villain_uid:
                break
        if not villain_uid:
            return []

        # Example guard: only in/near a 'dragon_lair' context (simple ancestor tag check)
        def _guard(g2, facts2, ctx2, a_uid):
            for pid in facts2.ancestors(a_uid):
                n = g2.get(pid)
                if "dragon_lair" in (getattr(n, "tags", set()) or set()):
                    return True
            return False

        def _produce(c, a_uid):
            # Add exactly one transition from the scene when the affordance is applied
            hint = c.create_node("tangl.core36.entity:Node", label="dragon_hint")
            c.add_edge(a_uid, hint, EdgeKind.TRANSITION)

        return [
            Offer(
                id="annie.dragon_hint",
                label="Annie hints about dragons",
                mode="attachment",
                source_uid=villain_uid,     # ANNIE -> scene marker
                requires=[],                # no provisioning needed here
                guard=_guard,
                produce=_produce,
            )
        ]

# ---- Landscape media affordance (non-blocking requirement ticket) ----

class LandscapeImageAffordance:
    """
    Attaches a non-blocking media requirement (inline landscape image).
    No builder registered → ticket remains pending/unsat per policy; test checks the 'requires' edge.
    """
    def __init__(self):
        pass  # no Provisioner injection needed; enable_affordances will call from scope

    def enumerate(self, g, facts, ctx, anchor_uid) -> Iterable[Offer]:
        # Very simple guard; return True for the test, or check tags if you like.
        def _guard(g2, f2, c2, a_uid): return True

        req = ProvisionRequirement(
            kind="media",
            name="inline-image",
            policy={"optional": True, "prune_if_unsatisfied": False, "create_if_missing": False},
        )

        return [
            Offer(
                id="media.inline_landscape",
                label="Inline landscape media",
                mode="attachment",
                source_uid=anchor_uid,   # scene/beat-level afford marker
                requires=[req],          # emit ticket via Provisioner.require
                guard=_guard,
                produce=lambda c, a_uid: None,
            )
        ]