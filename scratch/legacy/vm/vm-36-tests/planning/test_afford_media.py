# tests/test_afford_media.py
from uuid import uuid4
from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.core36.types import EdgeKind
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.afford import enable_affordances, AffordanceRegistry
from tangl.vm36.planning.provision import Provisioner

# minimal media affordance using Provisioner
from tangl.domains.afford_demo import LandscapeImageAffordance

def test_media_affordance_emits_requirement_nonblocking():
    g = Graph()
    loc = Node(label="ridge", tags={"mountains"}); g._add_node_silent(loc)
    beat = Node(label="beat"); g._add_node_silent(beat)
    g._add_edge_silent(Edge(src_id=loc.uid, dst_id=beat.uid, kind="contains"))

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="m1", base_hash=0, graph=g)
    scope = Scope.assemble(g, ctx.facts, cursor_uid=beat.uid, domains=DomainRegistry())
    ctx.mount_scope(scope)

    # provreg = ProvisionRegistry();
    prov = Provisioner(scope.resolvers_by_kind)  # no media realizer registered (stays pending/skipped)
    areg = AffordanceRegistry(); areg.register(LandscapeImageAffordance())

    enable_affordances(ctx, areg, anchor_uid=beat.uid)

    from tangl.vm36.execution.patch import apply_patch
    apply_patch(g, ctx.to_patch(uuid4()))

    # We should see a 'requires' edge from beat to a requirement node
    assert any(isinstance(e, Edge) and e.kind == EdgeKind.REQUIRES for e in g.edges())