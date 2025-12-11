# tests/test_provision_role_realize.py
from uuid import uuid4
from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.core36.types import EdgeKind
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.provision import Provisioner, ProvisionRequirement
from tangl.vm36.planning.resolver import SimpleRoleResolver

def test_role_provision_create_and_bind():
    # scene (cursor) in a bare graph
    g = Graph()
    scene = Node(label="scene"); g._add_node_silent(scene)

    # setup session-like bits
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="p1", base_hash=0, graph=g)
    facts = ctx.facts
    # assemble a trivial scope (no domains needed for this test)
    scope = Scope.assemble(g, facts, cursor_uid=scene.uid, domains=DomainRegistry())
    # scope = replace(scope,
    #                 offer_providers=[DemoTemplateProvider()],
    #                 resolvers_by_kind={"role": [SimpleRoleFinder(), SimpleRoleBuilder()]})
    ctx.mount_scope(scope)

    # prov = Provisioner()
    # prov = Provisioner.from_scope(scope)
    prov = Provisioner({"role": [SimpleRoleResolver()]})
    # EXECUTE: require role 'villain' with constraints label=Annie, tags include 'character'
    spec = ProvisionRequirement(kind="role", name="villain",
                       constraints={"label": "Annie", "tags": ["character"]},
                       policy={"create_if_missing": True})
    out = prov.require(ctx, scene.uid, spec)
    assert out.status == "bound" and out.bound_uid

    # Apply patch and verify edges
    from tangl.vm36.execution.patch import apply_patch
    patch = ctx.to_patch(uuid4())
    apply_patch(g, patch)

    # owner --(role:villain)--> resource
    role_kind = f"{EdgeKind.ROLE.prefix()}villain/123"
    assert not any(e.kind == role_kind for e in g.find_edges(scene, direction="out"))

    role_kind = f"{EdgeKind.ROLE.prefix()}villain"
    assert any(e.kind == role_kind for e in g.find_edges(scene, direction="out"))
    # resource --(fulfills)--> requirement
    res = g.get(out.bound_uid)
    assert res and any(
        e.kind == EdgeKind.FULFILLS for e in g.find_edges(res, direction="out")
    )