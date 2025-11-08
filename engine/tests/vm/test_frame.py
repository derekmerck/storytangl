import uuid

from tangl.core import Node, Graph, CallReceipt, BehaviorRegistry
from tangl.core.graph.edge import AnonymousEdge
from tangl.vm.resolution_phase import ResolutionPhase as P
from tangl.vm.frame import Frame, ChoiceEdge
from tangl.vm.provision import Requirement, ProvisioningPolicy, Dependency


def test_phase_order_is_total_and_strict(frame: Frame):
    """Phases execute in defined order with no gaps."""
    phases = P.ordered_phases()
    assert len(phases) == 9
    assert len(P) == 9
    assert phases[0] == P.INIT
    assert phases[-1] == P.POSTREQS

    # Mock handler that records execution order
    executed = []

    frame.cursor.tags = { "domain:local_domain" }

    def tracking_handler(phase):
        def handler(cursor, *, ctx):
            print("executing phase {}".format(phase))
            executed.append(phase)
            return None

        return handler

    for phase in phases:
        frame.local_behaviors.register(task=phase, priority=-1)(tracking_handler(phase))
    frame._invalidate_context()

    frame.follow_edge(AnonymousEdge(destination=frame.cursor))
    assert executed == phases[2:]  # P.INIT and P.DISCOVER doen't count currently
import pytest
@pytest.mark.skip()
def test_global_handlers_visible_in_scope():
    g = Graph(label="x")
    n = g.add_node(label="n1")
    frame = Frame(graph=g, cursor_id=n.uid)
    ns = frame.context.get_ns()

    print("Registered")
    for h in global_domain.handlers.values():
        print(h.func.__name__)
        assert hasattr(h, "phase")

    print("Has VALIDATE")
    for h in global_domain.handlers.find_all(task=P.VALIDATE):
        print(h.func.__name__)

    ns = frame.run_phase(P.VALIDATE)
    print( ns )
    # validate_cursor should have produced a receipt
    receipts = frame.phase_receipts[P.VALIDATE]
    assert len(receipts) >= 1
    assert isinstance(receipts[0], CallReceipt)

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

# This is in context now
# def test_session_context_ns_has_phase_and_results():
#     g = Graph()
#     n = g.add_node(label="A")
#     frame = Frame(graph=g, cursor_id=n.uid)
#     ns = frame.get_ns(P.VALIDATE)
#     assert ns["phase"] is P.VALIDATE
#     assert isinstance(ns["results"], list)

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

    frame.run_phase(P.PLANNING)
    assert not req.satisfied

    receipt = frame.run_phase(P.FINALIZE)
    assert receipt is not None
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
    # line = CallReceipt.last_result(*ns.get('results'))
    assert len(fragments) == 1
    line = fragments[0].content
    assert "[step " in line
    assert "end" in line

def test_postreq_redirect():
    g = Graph(); a = g.add_node(label="A"); b = g.add_node(label="B")
    ChoiceEdge(graph=g, source_id=a.uid, destination_id=b.uid, trigger_phase=P.POSTREQS)
    f = Frame(graph=g, cursor_id=a.uid)
    nxt = f.follow_edge(AnonymousEdge(source=a, destination=b))
    assert nxt is None  # but ensure POSTREQS found and would have been returned if available
    # Or directly assert f.run_phase(P.POSTREQS) returns the ChoiceEdge

def test_rand_is_deterministic_for_same_context():
    guid = uuid.uuid4()
    nuid = uuid.uuid4()

    g1 = Graph(uid=guid, label="demo")
    a1 = g1.add_node(uid=nuid, label="A")
    s1 = Frame(graph=g1, cursor_id=a1.uid)
    r1 = [s1.context.rand.random() for _ in range(3)]

    g2 = Graph(uid=guid, label="demo")
    a2 = g2.add_node(uid=nuid, label="A")
    s2 = Frame(graph=g2, cursor_id=a2.uid)
    r2 = [s2.context.rand.random() for _ in range(3)]

    assert r1 == r2

def test_local_domain():
    g = Graph(); n = g.add_node(label="A", tags="domain:local_domain")
    f = Frame(graph=g, cursor_id=n.uid)
    assert isinstance(f.local_behaviors, BehaviorRegistry)

    # lines = f.context.inspect_scope()
    # print(lines)

def test_journal_empty_is_persisted_as_empty_list():
    g = Graph(); n = g.add_node(label="A", tags="domain:local_domain")
    f = Frame(graph=g, cursor_id=n.uid)
    # Add a compositor that returns []
    def empty_fragments(*args, ctx, **kw): return []
    # This works, but it will pollute global handlers permanently and we have no reset func
    # global_domain.handlers.register(task=P.JOURNAL, priority=999)(empty_fragments)
    f.local_behaviors.register(task=P.JOURNAL, priority=999)(empty_fragments)
    f._invalidate_context()
    # logging.debug( f.context.inspect_scope() )
    frags = f.run_phase(P.JOURNAL)
    # Decide your policy: if you want to persist empties:
    assert isinstance(frags, list) and frags == []