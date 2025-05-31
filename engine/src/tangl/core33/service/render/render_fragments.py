from ...type_hints import StringMap
from ...enums      import CoreScope, CoreService
from ...graph      import Node, Graph
from ...scope      import GlobalScope, Domain
from ..tier_view  import TierView
from .fragment     import Fragment

def render_fragments(node: Node, graph: Graph, domain: Domain, ctx: StringMap) -> list[Fragment]:
    # ---------------------------------------------------------
    # 1. compose view
    handlers = TierView.compose(
        service=CoreService.RENDER,
        NODE=node.handler_layer(CoreService.RENDER),
        GRAPH=graph.handler_layer(CoreService.RENDER),
        DOMAIN=domain.handler_layer(CoreService.RENDER),
        GLOBAL=GlobalScope.get_instance().handler_layer(CoreService.RENDER)
    )

    frags: list[Fragment] = []

    # ---------------------------------------------------------
    # 2. iterate by CoreScope precedence
    for scope in CoreScope.range_outwards(CoreScope.NODE):          # NODE → GLOBAL
        layer = handlers._get_layer(scope)               # helper: returns the mapping for that CoreScope
        if not layer:
            continue
        for cap in layer:                               # already filtered to RENDER service
            if scope is CoreScope.NODE and cap.owner_uid not in (None, node.uid):
                continue
            part = cap.apply(node, None, graph, ctx)
            if part:
                frags.extend(part if isinstance(part, (list, tuple)) else [part])

    # ---------------------------------------------------------
    # 3. finalise
    for f in frags:
        f.node_uid = node.uid
    return frags
