import uuid

from tangl.core import Node, Graph, JobReceipt, global_domain
from tangl.core.graph.edge import AnonymousEdge
from tangl.vm.frame import ResolutionPhase as P, Frame, ChoiceEdge
from tangl.vm import simple_handlers
from tangl.vm.planning import Requirement, ProvisioningPolicy, Dependency

def test_global_handlers_visible_in_scope():
    g = Graph(label="x")
    n = g.add_node(label="n1")
    frame = Frame(graph=g, cursor_id=n.uid)
    ns = frame.get_ns(P.VALIDATE)

    print("Registered")
    for h in global_domain.handlers.values():
        print(h.func.__name__)
        assert hasattr(h, "phase")

    print("Has VALIDATE")
    for h in global_domain.handlers.find_all(phase=P.VALIDATE):
        print(h.func.__name__)

    ns = frame.run_phase(P.VALIDATE)
    print( ns )
    # validate_cursor should have produced a receipt
    receipts = frame.phase_receipts[P.VALIDATE]
    assert len(receipts) >= 1
    assert isinstance(receipts[0], JobReceipt)

# def test_ns_contract(session):
#     ns = session.run_phase(P.VALIDATE)
#     assert "cursor" in ns and "phase" in ns and "results" in ns

def test_follow_edge_stops_without_next(frame):
    g = frame.graph
    n = Node(label="def")
    g.add(n)
    assert n in g
    assert frame.cursor.label == "abc"
    assert frame.context.cursor.label == "abc"
    e = g.add_edge(frame.cursor, n)
    assert e in g
    assert frame.follow_edge(e) is None
    assert frame.cursor_id == n.uid
    assert frame.cursor is n, f'cursor should be {n!r}, not {frame.cursor!r}'
    assert frame.context.cursor is n


def test_session_follow_edge_updates_cursor_and_stops():
    g = Graph()
    n1 = g.add_node(label="A")
    n2 = g.add_node(label="B")
    e  = g.add_edge(n1, n2)
    frame = Frame(graph=g, cursor_id=n1.uid, event_sourced=False)

    out = frame.follow_edge(e)
    assert out is None
    assert frame.cursor.uid == n2.uid

def test_session_context_ns_has_phase_and_results():
    g = Graph()
    n = g.add_node(label="A")
    frame = Frame(graph=g, cursor_id=n.uid)
    ns = frame.get_ns(P.VALIDATE)
    assert ns["phase"] is P.VALIDATE
    assert isinstance(ns["results"], list)

def test_provisioning_create_policy_assigns_provider():
    g = Graph(label="demo")
    scene = g.add_node(label="scene")

    req = Requirement[Node](
        graph=g,
        policy=ProvisioningPolicy.CREATE,
        template={"obj_cls": Node, "label": "Companion"}
    )
    Dependency[Node](graph=g, source_id=scene.uid, requirement=req, label="needs_companion")

    frame = Frame(graph=g, cursor_id=scene.uid)

    ns = frame.run_phase(P.PLANNING)
    assert req.satisfied
    assert g.get("Companion") is not None

def test_prereq_redirect_and_journal_line():
    g = Graph(label="demo")
    start = g.add_node(label="start")
    end = g.add_node(label="end")

    ChoiceEdge(graph=g, source_id=start.uid, destination_id=end.uid, trigger_phase=P.PREREQS)

    frame = Frame(graph=g, cursor_id=start.uid)

    nxt = frame.follow_edge(AnonymousEdge(source=start, destination=end))  # first hop returns ChoiceEdge on PREREQS
    # After following, step incremented and JOURNAL should run
    fragments = frame.run_phase(P.JOURNAL)
    # line = JobReceipt.last_result(*ns.get('results'))
    assert len(fragments) == 1
    line = fragments[0].content
    assert "[step " in line
    assert "end" in line

def test_rand_is_deterministic_for_same_context():
    guid = uuid.uuid4()
    nuid = uuid.uuid4()

    g1 = Graph(uid=guid, label="demo")
    a1 = g1.add_node(uid=nuid, label="A")
    s1 = Frame(graph=g1, cursor_id=a1.uid)
    r1 = [s1.rand.random() for _ in range(3)]

    g2 = Graph(uid=guid, label="demo")
    a2 = g2.add_node(uid=nuid, label="A")
    s2 = Frame(graph=g2, cursor_id=a2.uid)
    r2 = [s2.rand.random() for _ in range(3)]

    assert r1 == r2
