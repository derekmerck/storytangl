from ..enums import Phase, Tier
from ..runtime.handler_cache import HandlerCache
from ..render.fragment import Fragment
from ..type_hints import Context

def render_fragments(node, ctx: Context, cap_cache: HandlerCache) -> list[Fragment]:
    """Run RenderHandlers tier-ordered and collect fragments."""
    frags: list[Fragment] = []

    for tier in Tier.range_inwards(Tier.NODE):          # NODE → GLOBAL
        for cap in cap_cache.iter_phase(Phase.RENDER, tier):
            if cap.owner_uid == node.uid or tier is not Tier.NODE:
                part = cap.apply(node, None, None, ctx)
                if part:
                    # normalise to list
                    if isinstance(part, Fragment):
                        frags.append(part)
                    else:
                        frags.extend(part)

    # guarantee UID and ordering
    for f in frags:
        f.node_uid = node.uid
    return frags
