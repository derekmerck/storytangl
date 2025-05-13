from ...enums import CoreScope, CoreService
from ...graph import EdgeState, EdgeKind

def apply_gating(node, graph, handlers_view, ctx):
    # 1) run GATE caps (stat predicates, etc.)
    for scope in CoreScope.range_outwards(CoreScope.NODE):
        for cap in handlers_view.iter_layer(scope):
            if cap.service is not CoreService.GATE:
                continue
            if scope is CoreScope.NODE and cap.owner_uid not in (None, node.uid):
                continue
            cap.apply(node, None, graph, ctx)

    # 2) set edge.state → OPEN when gate passes
    for edge in filter(lambda x: x.kind is EdgeKind.CHOICE, graph.edges_out[node.uid]):
        if edge.state == EdgeState.RESOLVED and edge.gate_pred(ctx):
            edge.state = EdgeState.OPEN
