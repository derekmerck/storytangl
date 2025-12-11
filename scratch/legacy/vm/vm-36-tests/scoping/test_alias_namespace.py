from uuid import uuid4
from collections import ChainMap

import pytest

from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.core36.facts import Facts
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.patch import apply_patch
from tangl.vm36.scoping import Scope
from tangl.vm36.planning import ProvisionRequirement, Provisioner
from tangl.vm36.planning.resolver import SimpleRoleResolver

ScopeBuilder = object

# todo: implement improved scope assemble
@pytest.mark.skip(reason="Not implemented yet")
def test_role_alias_ns_resolves_to_bound_node():
    g = Graph(); scene = Node(label="scene"); g._add_node_silent(scene)
    annie = Node(label="Annie", tags={"character"}); g._add_node_silent(annie)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t", base_hash=0, graph=g)
    ctx.cursor_uid = scene.uid

    spec = ProvisionRequirement(kind="role", name="villain", constraints={"tags": {"character"}})
    scope = Scope(
        ns=ChainMap({}), handlers=[], offer_providers=[],
        resolvers_by_kind={"role": [SimpleRoleResolver()]},
        active_domains=set(), cursor_uid=scene.uid, cursor_label="scene"
    )
    ctx.mount_scope(scope)

    out = Provisioner.from_scope(scope).require(ctx, scene.uid, spec)
    apply_patch(g, ctx.to_patch(uuid4()))

    # rebuild scope for the next tick to see new bindings
    facts = Facts.compute(g)
    scope2 = ScopeBuilder().structural_layers(g, facts, scene.uid).domain_layers(g, facts, scene.uid, dreg=None).build()
    ns = scope2.ns

    assert out.status == "bound"
    assert "villain" in ns
    assert getattr(ns["villain"], "label") == "Annie"