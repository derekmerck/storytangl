from ..tier_view  import TierView
from ..enums      import Tier, Phase, Service
from ..graph      import GlobalScope, EdgeTrigger
from .fragment    import Fragment

def render_fragments(node, graph, domain, ctx) -> list[Fragment]:
    # ---------------------------------------------------------
    # 1. compose view
    handlers = TierView.compose(
        service=Service.RENDER,
        NODE=node.handler_layer(Service.RENDER),
        GRAPH=graph.handler_layer(Service.RENDER),
        DOMAIN=domain.handler_layer(Service.RENDER),
        GLOBAL=GlobalScope.get_instance().handler_layer(Service.RENDER)
    )

    frags: list[Fragment] = []

    # ---------------------------------------------------------
    # 2. iterate by tier precedence
    for tier in Tier.range_outwards(Tier.NODE):          # NODE → GLOBAL
        layer = handlers._get_layer(tier)               # helper: returns the mapping for that tier
        if not layer:
            continue
        for cap in layer:                               # already filtered to RENDER service
            if tier is Tier.NODE and cap.owner_uid not in (None, node.uid):
                continue
            part = cap.apply(node, None, graph, ctx)
            if part:
                frags.extend(part if isinstance(part, (list, tuple)) else [part])

    # ---------------------------------------------------------
    # 3. finalise
    for f in frags:
        f.node_uid = node.uid
    return frags
