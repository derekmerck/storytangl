from tangl.core.graph import Graph
from tangl.core.domain import global_domain
from tangl.vm.context import Context

# ---------- context & scope ----------

def test_scope_includes_global_domain_only_when_empty_registry():
    g = Graph()
    n = g.add_node(label="here")
    ctx = Context(graph=g, cursor_id=n.uid)
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
