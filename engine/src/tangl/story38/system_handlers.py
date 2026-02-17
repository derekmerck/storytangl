from __future__ import annotations

from tangl.core38 import Selector
from tangl.vm38 import ChoiceFragment, ContentFragment, on_journal

from .episode import Action, Block


@on_journal
def render_block(*, caller, ctx, **_kw):
    """Render block content and available choices into vm38 fragments."""
    if not isinstance(caller, Block):
        return None

    fragments = []
    if caller.content:
        fragments.append(ContentFragment(content=caller.content, source_id=caller.uid))

    for edge in caller.edges_out(Selector(has_kind=Action, trigger_phase=None)):
        fragments.append(
            ChoiceFragment(
                edge_id=edge.uid,
                text=edge.text or edge.get_label(),
                available=edge.available(ctx=ctx),
            )
        )

    return fragments or None
