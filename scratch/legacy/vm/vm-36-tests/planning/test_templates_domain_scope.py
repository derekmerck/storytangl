# tests/test_templates_domain_scope.py
from uuid import uuid4
from tangl.core36.entity import Node, Edge
from tangl.core36.graph import Graph
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.frontier import discover_frontier


class BlackjackDomain:
    def templates(self, g, node):
        from tangl.vm36.planning.offers import Offer
        return (Offer(id="hit", label="Hit"), Offer(id="stand", label="Stand"))

def test_blackjack_templates_only_with_domain():
    g = Graph()
    table = Node(label="table", tags={"domain:blackjack"})
    hand  = Node(label="hand")
    g._add_node_silent(table); g._add_node_silent(hand)
    g._add_edge_silent(Edge(src_id=table.uid, dst_id=hand.uid, kind="contains"))

    dreg = DomainRegistry()
    dreg.add("blackjack", provider=BlackjackDomain())

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="bj", base_hash=0, graph=g)
    scope = Scope.assemble(g, ctx.facts, cursor_uid=hand.uid, domains=dreg)
    ctx.mount_scope(scope)

    # treg = TemplateRegistry()
    # for p in ctx.scope_templates: treg.register(p)

    choices = discover_frontier(ctx, anchor_uid=hand.uid)
    labels = {c.label for c in choices}
    assert {"Hit","Stand"}.issubset(labels)