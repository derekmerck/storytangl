from uuid import uuid4

from tangl.core36.graph import Graph, Node
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.planning.resolver import GenericEntityBuilder
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.offers import Offer
from tangl.vm36.planning.ticket import ProvisionRequirement
from tangl.vm36.planning.frontier import discover_frontier


# class EntityBuilderSat:
#     kind = "entity"; cost_hint = 10
#     def find_existing(self, g, facts, anchor_uid, req): return ()
#     def can_create(self, constraints): return 10
#     def create(self, ctx, owner_uid, req):
#         return ctx.create_node("tangl.core36.entity:Node", label=req.name)

def test_enabled_when_creatable_via_satisfier():
    g = Graph(); anchor = Node(label="anchor"); g._add_node_silent(anchor)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t2", base_hash=0, graph=g)
    facts = Facts.compute(g)
    scope = Scope.assemble(g, facts, anchor.uid, domains=None)
    scope = Scope(ns=scope.ns, handlers=scope.handlers, offer_providers=[
        # one offer requiring an entity creatable if missing
        type("Static", (), {"enumerate": lambda *_: [Offer(
            id="inspect", label="Inspect",
            requires=[ProvisionRequirement(kind="entity", name="torch", policy={"create_if_missing": True})],
            produce=lambda c,a: None
        )]})()
    ], resolvers_by_kind={"entity":[GenericEntityBuilder()]}, active_domains=scope.active_domains,
    cursor_uid=anchor.uid, cursor_label="anchor")
    ctx.mount_scope(scope)

    # provreg = ProvisionRegistry()
    choices = discover_frontier(ctx, anchor_uid=anchor.uid)
    assert ("inspect","enabled") in {(c.id,c.status) for c in choices}