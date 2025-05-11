from ..enums import Phase, Tier
from ..runtime.handler_cache import HandlerCache
from ..render.fragment import Fragment
from ..type_hints import StringMap

def render_fragments(node, ctx: StringMap, cap_cache: HandlerCache) -> list[Fragment]:
    """Run RenderCaps tier-ordered and collect fragments."""
    frags: list[Fragment] = []

    for tier in Tier.range_inwards(Tier.NODE):          # NODE → GLOBAL
        for cap in cap_cache.iter_phase(Phase.RENDER, tier):
            # ── run NODE-tier handlers bound to *this* node
            #    and any handler whose owner_uid == None (global renderer)
            if tier is Tier.NODE and cap.owner_uid not in (None, node.uid):
                continue

            part = cap.apply(node, None, None, ctx)
            if part:
                frags.extend(part if isinstance(part, (list, tuple)) else [part])

    # guarantee UID and ordering
    for f in frags:
        f.node_uid = node.uid
    return frags
