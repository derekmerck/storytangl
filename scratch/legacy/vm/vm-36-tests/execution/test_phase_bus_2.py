from uuid import uuid4
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.patch import apply_patch, Op
from tangl.core36.graph import Graph

def test_phase_bus_order_and_provenance():
    g = Graph()
    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c2", base_hash=0)
    bus = PhaseBus()

    def exec_a(c: StepContext):
        # first exec creates a node
        c.create_node("tangl.core36.entity:Node", label="n1")

    def exec_b(c: StepContext):
        # second exec sets a tag on the most recent node (by reading last uid from effects)
        # (just for test: we know first effect is CREATE_NODE)
        first = next(e for e in c.effects if e.op is Op.CREATE_NODE)
        uid = first.args[0]
        c.set_attr(uid, ("tags",), {"x"})

    bus.register(Phase.EXECUTE, "A", 10, exec_a)
    bus.register(Phase.EXECUTE, "B", 20, exec_b)

    bus.run(Phase.EXECUTE, ctx)
    patch = ctx.to_patch(tick_id=uuid4())

    # Provenance is captured from phase + handler id
    provs = [e.provenance for e in patch.effects]
    assert ("EXECUTE","A") in provs
    assert ("EXECUTE","B") in provs

    apply_patch(g, patch)
    # confirm tag set landed
    created_uid = next(e for e in patch.effects if e.op is Op.CREATE_NODE).args[0]
    node = g.get(created_uid)
    assert node and node.tags == {"x"}