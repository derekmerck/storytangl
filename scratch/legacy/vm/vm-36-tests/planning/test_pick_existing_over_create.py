from uuid import uuid4
from collections import ChainMap

from tangl.core36.graph import Graph, Node
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.patch import apply_patch
from tangl.vm36.scoping import Scope
from tangl.vm36.planning import ProvisionRequirement, Provisioner
from tangl.vm36.planning.resolver import SimpleRoleResolver

def test_proposal_pick_existing_over_create():
    g = Graph(); scene = Node(label="scene"); g._add_node_silent(scene)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="t", base_hash=0, graph=g)
    ctx.cursor_uid = scene.uid
    # pre-existing villain
    v = Node(label="Annie", tags={"character"}); g._add_node_silent(v)

    spec = ProvisionRequirement(kind="role", name="villain", constraints={"tags": {"character"}})
    scope = Scope(
        ns=ChainMap({}), handlers=[], offer_providers=[],
        resolvers_by_kind={"role": [SimpleRoleResolver()]},
        active_domains=set(), cursor_uid=scene.uid, cursor_label="scene"
    )
    ctx.mount_scope(scope)

    out = Provisioner.from_scope(scope).require(ctx, scene.uid, spec)
    patch = ctx.to_patch(uuid4()); apply_patch(g, patch)

    assert out.status == "bound"
    assert g.find_edge_ids(src=scene.uid, kind="role:villain")  # bound to existing
