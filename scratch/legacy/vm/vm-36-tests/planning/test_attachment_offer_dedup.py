from uuid import uuid4

from tangl.core36.graph import Graph, Node
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.offers import Offer, OfferProvider
from tangl.vm36.planning.frontier import discover_frontier



class HintProvider(OfferProvider):
    def enumerate(self, g, facts, ctx, anchor_uid):
        return [Offer(id="hint", label="Hint", mode="attachment",
                      source_uid=anchor_uid,
                      requires=[], produce=lambda c,a: c.say({"type":"aside","text":"tip"}))]

def test_attachment_offer_dedup():
    g = Graph(); scene = Node(label="scene"); g._add_node_silent(scene)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t1", base_hash=0, graph=g)
    facts = Facts.compute(g)
    scope = Scope.assemble(g, facts, scene.uid, domains=None)
    scope = Scope(ns=scope.ns,
                  handlers=scope.handlers,
                  offer_providers=[HintProvider()],
                  resolvers_by_kind=scope.resolvers_by_kind,
                  active_domains=scope.active_domains,
                  cursor_uid=scene.uid, cursor_label="scene")
    ctx.mount_scope(scope)

    choices = discover_frontier(ctx, anchor_uid=scene.uid)
    ch = next(c for c in choices if c.id == "hint" and c.status == "enabled")
    ch.execute(ctx)  # first time: produces + marks afford edge
    # execute again within same tick → dedup prevents double produce
    ch.execute(ctx)

    # exactly one afford edge exists
    g2 = ctx.preview()
    assert len(g2.find_edge_ids(src=scene.uid, dst=scene.uid, kind="afford:hint")) == 1