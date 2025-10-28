from tangl.core import Node, Graph, CallReceipt
from tangl.core.domain import DomainNode
from tangl.vm import Requirement
from tangl.vm.vm_dispatch.on_get_ns import on_get_ns
from tangl.vm.planning import Affordance, Dependency


def test_dep_in_ns():
    g = Graph()
    m = DomainNode(graph=g, locals={"foo": 1})  # DomainNodes have locals
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

    receipts = on_get_ns.dispatch(m, ctx=None)
    ns = CallReceipt.merge_results(*receipts)
    print( ns )
    assert 'foo' in ns
    assert 'dep' in ns
    assert ns['dep'] is n
    assert ns['req'] is o
