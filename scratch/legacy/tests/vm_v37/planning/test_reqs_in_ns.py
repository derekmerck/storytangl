
from tangl.core import Node, Graph, CallReceipt
from tangl.vm import Requirement
from tangl.vm.dispatch import do_get_ns
from tangl.vm.provision import Affordance, Dependency

def test_dep_in_ns(NodeL, SubgraphL, GraphL, trivial_ctx) -> None:
    g = Graph()
    m = NodeL(graph=g, locals={"foo": 1})  # NodeL's have locals
    n = Node(graph=g)
    r = Requirement(graph=g, provider_id=n.uid)
    assert r.satisfied and r.provider is n

    d = Dependency(graph=g, label="dep", source_id=m.uid, requirement=r)
    assert d.source is m
    assert d in list(g.find_edges(source=m))
    assert d.satisfied and d.destination is n

    o = Node(graph=g)
    rr = Requirement(graph=g, provider_id=m.uid)
    a = Affordance(graph=g, label="req", requirement=rr, destination_id=o.uid)
    assert a.destination is o
    assert a in list(g.find_edges(source=m))
    assert a.satisfied and a.source is m

    ns = do_get_ns(m, ctx=trivial_ctx)
    print( ns )
    assert 'foo' in ns
    assert 'dep' in ns
    assert ns['dep'] is n
    assert ns['req'] is o
