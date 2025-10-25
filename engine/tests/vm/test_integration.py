from tangl.core import Graph, Node, global_domain
from tangl.vm import ChoiceEdge, ResolutionPhase as P, Requirement, Dependency, Affordance, ProvisioningPolicy, Frame

def test_tiny_integration():
    # Build a tiny graph
    g = Graph(label="demo")
    start = g.add_node(label="start")
    scene = g.add_node(label="scene")

    # choice edge: start -> scene, auto-follow on PREREQS for demo
    choice = ChoiceEdge(graph=g, source_id=start.uid, destination_id=scene.uid, trigger_phase=P.PREREQS)

    # a dependency hanging off `scene` that must be provisioned
    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "Companion"}
    )
    dep = Dependency[Node](graph=g, source_id=scene.uid, requirement=req, label="needs_companion")

    # Frame
    sess = Frame(graph=g, cursor_id=start.uid)

    # drive
    ns = sess.context.get_ns()
    assert sess.run_phase(P.VALIDATE)  # basic sanity

    # follow the choice; the loop runs PREREQS -> UPDATE -> JOURNAL -> FINALIZE -> POSTREQS
    sess.resolve_choice(choice)

    # Did provisioning happen?
    assert req.satisfied
    assert g.get("Companion") is not None