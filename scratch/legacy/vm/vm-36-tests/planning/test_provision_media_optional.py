# tests/test_provision_unsat_guard.py
from uuid import uuid4
import pytest
from tangl.core36.entity import Node
from tangl.core36.graph import Graph
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.scoping.domains import DomainRegistry
from tangl.vm36.scoping import Scope
from tangl.vm36.planning.provision import Provisioner, ProvisionRequirement, has_unsatisfied_requirements

def test_unsat_requirement_guard_blocks_validation():
    g = Graph()
    scene = Node(label="scene"); g._add_node_silent(scene)
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="p2", base_hash=0, graph=g)
    scope = Scope.assemble(g, ctx.facts, cursor_uid=scene.uid, domains=DomainRegistry())
    ctx.mount_scope(scope)

    # reg = ProvisionRegistry(scope.resolvers_by_kind)
    prov = Provisioner(scope.resolvers_by_kind)

    # Require a non-existent entity, forbid creation, not optional => UNSAT
    spec = ProvisionRequirement(kind="entity", name="mcguffin",
                       constraints={"tags": ["legendary"]},
                       policy={"create_if_missing": False, "optional": False})
    out = prov.require(ctx, scene.uid, spec)
    assert out.status in {"unsat", "pending"}  # pending only if a realizer was registered

    from tangl.vm36.execution.patch import apply_patch
    patch = ctx.to_patch(uuid4()); apply_patch(g, patch)

    # VALIDATE handler prunes if unsatisfied
    bus = PhaseBus()
    def validate(c: StepContext):
        if has_unsatisfied_requirements(g, c.facts, scene.uid):
            raise ValueError("Unsatisfied requirements")
    bus.register(Phase.VALIDATE, "prune_on_unsat", 50, validate)

    with pytest.raises(ValueError):
        bus.run(Phase.VALIDATE, ctx)
