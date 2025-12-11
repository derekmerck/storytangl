from uuid import uuid4
from collections import ChainMap

from tangl.vm36.planning import Provisioner, ProvisionRequirement
from tangl.vm36.planning.resolver import SimpleRoleResolver
from tangl.vm36.scoping import Scope
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.patch import apply_patch
from tangl.core36.graph import Graph, Node

def test_role_find_ignores_label_default():
    g = Graph(); scene = Node(label="scene"); g._add_node_silent(scene)
    annie = Node(label="Annie", tags={"character"}); g._add_node_silent(annie)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t", base_hash=0, graph=g)
    ctx.cursor_uid = scene.uid

    spec = ProvisionRequirement(kind="role", name="villain", constraints={"tags": {"character"}})
    scope = Scope(ns=ChainMap({}), handlers=[], offer_providers=[],
                  resolvers_by_kind={"role": [SimpleRoleResolver()]},
                  active_domains=set(), cursor_uid=scene.uid, cursor_label="scene")
    ctx.mount_scope(scope)

    out = Provisioner.from_scope(scope).require(ctx, scene.uid, spec)
    apply_patch(g, ctx.to_patch(uuid4()))

    assert out.status == "bound"
    assert g.find_edge_ids(src=scene.uid, kind="role:villain")