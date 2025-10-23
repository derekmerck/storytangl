from tangl.core.graph import Graph
from tangl.core.domain import global_domain
from tangl.vm.context import Context

# ---------- context & scope ----------

def test_scope_includes_global_domain_only_when_empty_registry():
    g = Graph()
    n = g.add_node(label="here")
    ctx = Context(graph=g, cursor_id=n.uid, step=-1)
    doms = list(ctx.scope.active_domains)
    assert global_domain in doms

def test_context_namespace_has_top_layer_and_is_not_polluting_domains():
    g = Graph()
    n = g.add_node(label="here")
    ctx = Context(graph=g, cursor_id=n.uid)
    ns = ctx.get_ns()
    ns["foo"] = 1
    # top layer write works
    assert ns["foo"] == 1
    # but domain maps below remain unpolluted
    for m in ns.maps[1:]:
        assert "foo" not in m

from tangl.core.domain import DomainNode
def test_ns_gather():
    # check that ctx collects ns same as scope
    g = Graph()
    n = g.add_node(label="here", locals={"foo": 1}, obj_cls=DomainNode)
    assert n.locals["foo"] == 1
    ctx = Context(graph=g, cursor_id=n.uid)

    print( ctx.inspect_scope() )

    ns = ctx.get_ns()
    # _ns = ctx._get_ns()

    print(ns)
    # print(_ns)

    # assert dict(ns) == dict(_ns)

# Doesn't work like this anymore?  Alternate test?
# def test_get_ns_returns_fresh_top_layer_per_phase(frame):
#     from tangl.vm.frame import ResolutionPhase as P
#     ns1 = frame.context.get_ns()
#     ns1["sentinel"] = True
#     ns2 = frame.context.get_ns()
#     assert "sentinel" not in ns2
#     assert ns2["phase"] is P.FINALIZE
