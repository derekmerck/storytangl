# tests/test_frontier_discovery.py
from uuid import uuid4
from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.planning.frontier import discover_frontier
from tangl.vm36.planning.resolver import SimpleRoleResolver
from tangl.domains.templates_demo import DemoTemplateProvider
from tangl.vm36.execution.patch import apply_patch
from tangl.vm36.scoping.scope import Scope
from collections import ChainMap


def test_frontier_enabled_and_blocked():
    g = Graph()
    anchor = Node(label="scene", tags={"secret"})  # satisfies guard for open_secret
    g._add_node_silent(anchor)

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="fr1", base_hash=0, graph=g)
    ctx.cursor_uid = anchor.uid

    # mount a Scope with the demo offer provider and role satisfiers
    scope = Scope(
        ns=ChainMap({}),
        handlers=[],
        offer_providers=[DemoTemplateProvider()],
        resolvers_by_kind={
            "role": [SimpleRoleResolver()],
        },
        active_domains=set(),
        cursor_uid=anchor.uid,
        cursor_label=anchor.label,
    )
    ctx.mount_scope(scope)
    choices = discover_frontier(ctx, anchor_uid=anchor.uid)

    labels = { (c.id, c.status) for c in choices }
    # 'inspect_lair' should be enabled (we can create Annie), 'open_secret' blocked (no key)
    assert ("inspect_lair", "enabled") in labels
    assert ("open_secret", "blocked") in labels

    # execute the enabled choice and apply
    chosen = next(c for c in choices if c.id == "inspect_lair")
    chosen.execute(ctx)
    apply_patch(g, ctx.to_patch(uuid4()))

    # graph should now have a transition edge out of anchor
    assert any(e.kind == "transition" for e in g.find_edges(anchor, direction="out"))