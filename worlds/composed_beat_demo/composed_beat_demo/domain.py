"""Domain handlers for the composed beat demo world.

This module is the worked example for journal beat composition. Each handler
exercises one contribution channel of the gather → enrich → compose pipeline:

* ``contribute_default_porter_chunk`` / ``contribute_author_porter_chunk`` —
  named chunk override across dispatch layers (APPLICATION vs AUTHOR).
* ``apply_beat_consequences`` — UPDATE-phase mutation plus cross-phase journal
  enrichment through ``ctx.injected_journal_fragments``.
* ``render_porter_reaction`` — conditional render-time enrichment gated on the
  gathered namespace.
* ``compose_beat`` — post-merge syuzhet assembly: slot ordering, conditional
  replacement, and a beat overlay binding the result.

Data-scope chunk overrides (story ``locals:`` vs block ``locals:``) live in
``script.yaml`` and need no handlers at all.
"""

from __future__ import annotations

from uuid import UUID

from tangl.core import DispatchLayer, Priority, Record
from tangl.journal.compose import REST_SLOT, assemble_slots, beat_overlay, replace_first
from tangl.journal.fragments import ContentFragment
from tangl.story import Block, on_compose_journal, on_gather_ns, on_journal
from tangl.vm import on_update


class BeatBlock(Block):
    """Typed block used by the composed beat demo world."""

    reputation_delta: int = 0
    incident: str = ""


@on_gather_ns(wants_caller_kind=BeatBlock, wants_exact_kind=False)
def contribute_default_porter_chunk(*, caller, ctx, **_kw):
    """APPLICATION-scope default for the named ``porter_greeting`` chunk."""
    return {"porter_greeting": "The porter waves you through without looking up."}


@on_gather_ns(
    wants_caller_kind=BeatBlock,
    wants_exact_kind=False,
    dispatch_layer=DispatchLayer.AUTHOR,
)
def contribute_author_porter_chunk(*, caller, ctx, **_kw):
    """AUTHOR-scope override of ``porter_greeting`` — the later layer wins."""
    return {"porter_greeting": "Old Maro looks up from his ledger and grins."}


@on_update(
    wants_caller_kind=BeatBlock,
    wants_exact_kind=False,
    dispatch_layer=DispatchLayer.AUTHOR,
)
def apply_beat_consequences(*, caller, ctx, **_kw):
    """Apply authored consequences and stage cross-phase journal enrichment."""
    if caller.reputation_delta:
        reputation = int(caller.graph.locals.get("reputation", 0))
        caller.graph.locals["reputation"] = reputation + caller.reputation_delta
    if caller.incident:
        ctx.injected_journal_fragments.append(
            ContentFragment(
                content=caller.incident,
                source_id=caller.uid,
                tags={"incident"},
            )
        )
    return None


@on_journal(wants_caller_kind=BeatBlock, wants_exact_kind=False, priority=Priority.NORMAL)
def render_porter_reaction(*, caller, ctx, **_kw):
    """Conditional enrichment: Maro reacts when reputation has slipped."""
    if not caller.incident:
        return None
    if int(ctx.get_ns(caller).get("reputation", 0)) >= 0:
        return None
    return ContentFragment(
        content="Maro's eyes drop to the mud you tracked up his gangway, then back to you.",
        source_id=caller.uid,
        tags={"reaction"},
    )


BEAT_SLOTS = ("setting", "incident", "reaction", REST_SLOT)


def _classify_beat_fragment(fragment: Record) -> str | None:
    tags = fragment.tags or set()
    if "incident" in tags:
        return "incident"
    if "reaction" in tags:
        return "reaction"
    if isinstance(fragment, ContentFragment):
        return "setting"
    return None


@on_compose_journal(
    wants_caller_kind=BeatBlock,
    wants_exact_kind=False,
    dispatch_layer=DispatchLayer.AUTHOR,
)
def compose_beat(*, caller, ctx, fragments, **_kw):
    """Assemble the beat: slot the telling, veil it in fog, bind the overlay."""
    composed = assemble_slots(
        fragments,
        order=BEAT_SLOTS,
        classify=_classify_beat_fragment,
    )
    if ctx.get_ns(caller).get("fog_in"):
        composed = replace_first(
            composed,
            lambda f: isinstance(f, ContentFragment) and f.source_id == caller.uid,
            ContentFragment(
                content="Fog has come in off the water; the dock is a rumor of shapes.",
                source_id=caller.uid,
            ),
            insert_missing=True,
        )
    members = [f for f in composed if isinstance(f, ContentFragment)]
    return [*composed, beat_overlay(members, beat=caller.get_label())]


BeatBlock.model_rebuild(_types_namespace={"UUID": UUID})


__all__ = ["BEAT_SLOTS", "BeatBlock"]
