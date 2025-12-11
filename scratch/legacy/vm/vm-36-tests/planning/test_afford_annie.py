# tests/test_afford_annie.py
from uuid import uuid4
from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.core36.types import EdgeKind
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.afford import enable_affordances, AffordanceRegistry
from tangl.domains.afford_demo import AnnieHintProvider

def test_annie_hint_affordance_enables_once():
    g = Graph()
    # scene in dragon_lair; villain Annie bound to scene
    loc = Node(label="lair", tags={"dragon_lair"}); g._add_node_silent(loc)
    scene = Node(label="scene"); g._add_node_silent(scene)
    g._add_edge_silent(Edge(src_id=loc.uid, dst_id=scene.uid, kind="contains"))

    annie = Node(label="Annie", tags={"character"}); g._add_node_silent(annie)
    g._add_edge_silent(Edge(src_id=scene.uid, dst_id=annie.uid, kind=f"{EdgeKind.ROLE.prefix()}villain"))

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="a1", base_hash=0, graph=g)
    scope = Scope.assemble(g, ctx.facts, cursor_uid=scene.uid, domains=DomainRegistry())
    ctx.mount_scope(scope)

    areg = AffordanceRegistry(); areg.register(AnnieHintProvider())

    # Run enabling pass twice; second shouldn’t duplicate
    enable_affordances(ctx, areg, anchor_uid=scene.uid)
    enable_affordances(ctx, areg, anchor_uid=scene.uid)

    from tangl.vm36.execution.patch import apply_patch
    patch = ctx.to_patch(uuid4()); apply_patch(g, patch)

    # marker: annie --(afford:annie.dragon_hint)--> scene
    assert g.find_edge_ids(src=annie.uid, dst=scene.uid, kind=f"{EdgeKind.AFFORD.prefix()}annie.dragon_hint")
    # transition added exactly once
    trans = g.find_edge_ids(src=scene.uid, kind=EdgeKind.TRANSITION)
    assert len(trans) == 1