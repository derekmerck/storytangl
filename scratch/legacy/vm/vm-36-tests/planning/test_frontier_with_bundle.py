from uuid import uuid4
from collections import ChainMap

from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.scope import Scope
from tangl.vm36.planning.offers import Offer
from tangl.vm36.planning.ticket import ProvisionRequirement
from tangl.vm36.planning.frontier import discover_frontier
from tangl.vm36.planning.resolver import SimpleRoleResolver
from tangl.vm36.execution.patch import apply_patch

class StaticOffers:
    def __init__(self, specs): self.specs = specs
    def enumerate(self, g, facts, ctx, anchor_uid):
        return list(self.specs)

def test_exec_provisions_and_updates_graph():
    g = Graph()
    anchor = Node(label="scene"); g._add_node_silent(anchor)

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="tA", base_hash=0, graph=g)
    ctx.cursor_uid = anchor.uid

    offers = [
        Offer(
            id="inspect",
            label="Inspect",
            requires=[ProvisionRequirement(kind="role", name="villain", policy={"create_if_missing": True})],
            produce=lambda c, a: None,  # your domain-specific side effects here
        )
    ]

    # Scope = offers + satisfiers (finder + builder)
    scope = Scope(
        ns=ChainMap({}),
        handlers=[],
        offer_providers=[StaticOffers(offers)],
        resolvers_by_kind={"role": [SimpleRoleResolver()]},
        active_domains=set(),
        cursor_uid=anchor.uid,
        cursor_label=anchor.label,
    )
    ctx.mount_scope(scope)

    # PLAN
    choices = discover_frontier(ctx, anchor_uid=anchor.uid)
    enabled = [c for c in choices if c.status == "enabled"]
    assert any(c.id == "inspect" for c in enabled)  # todo: FAILS HERE

    # EXECUTE (this calls Provisioner.from_scope(scope).require(...) under the hood)
    pick = next(c for c in enabled if c.id == "inspect")
    pick.execute(ctx)

    # COMMIT the effects and refresh the context (or build a new StepContext)
    patch = ctx.to_patch(uuid4())
    apply_patch(g, patch)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="tA2", base_hash=0, graph=g)
    ctx.cursor_uid = anchor.uid

    # Now the graph is updated; assert edges/resources exist as expected…
    # e.g., villain binding edge:
    assert g.find_edge_ids(src=anchor.uid, kind="role:villain")