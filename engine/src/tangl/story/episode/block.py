# tangl/story/episode/block.py
"""
Block: cursor node that orchestrates JOURNAL fragments.

JOURNAL handlers (same task, different priorities):
1) block_fragment (EARLY): render inline block content → content fragments
2) describe_concepts (NORMAL): render child concepts → "concept" fragments
3) collect_choices (LATE): gather outgoing actions → "choice" fragments

Only blocks register JOURNAL handlers; other nodes contribute fragments on request.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from uuid import UUID
import logging

from pydantic import Field

from tangl.core import BaseFragment, Node, CallReceipt, Graph  # noqa
from tangl.core.behavior import HandlerPriority as Prio
from tangl.vm import ResolutionPhase as P, ChoiceEdge, Context
from tangl.journal.content import ContentFragment
from tangl.journal.media import MediaFragment
from tangl.story.discourse import DialogHandler
from tangl.story.dispatch import on_get_choices, on_journal_content, story_dispatch
from tangl.story.fabula.media import attach_media_deps_for_block
from tangl.story.runtime import ContentRenderer
from tangl.story.concepts import Concept
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_resource.media_dependency import MediaDep
from tangl.media.media_resource.media_resource_inv_tag import (
    MediaResourceInventoryTag as MediaRIT,
)
from tangl.vm.runtime import HasEffects
from .action import Action

logger = logging.getLogger(__name__)

class Block(Node, HasEffects):
    """
    Block(label: str, content: str = "")

    Smallest interactive unit. Aggregates prose and presents choices at the cursor.

    Key features
    ------------
    - Inline prose via `content` (Jinja2 template).
    - Concept aggregation via `get_concepts()`.
    - Choice filtering via `get_choices(ns=...)`.
    - Multi-handler JOURNAL pattern for composable output.

    Notes
    -----
    Fragment order is content → concepts → choices (enforced by handler priority).
    """

    content: str = ""
    locals: dict[str, Any] = Field(default_factory=dict)

    def get_concepts(self) -> list[Concept]:
        """
        Return direct child :class:`Concept` nodes in creation order.

        Returns
        -------
        list[Concept]
        """
        concepts: list[Concept] = []
        seen: set[UUID] = set()

        def _append_concept(candidate: Concept | None) -> None:
            if candidate is None or not isinstance(candidate, Concept):
                return
            if candidate.graph is not self.graph:
                return
            if candidate.uid in seen:
                return
            seen.add(candidate.uid)
            concepts.append(candidate)

        for edge in self.edges_out():
            destination = getattr(edge, "destination", None)
            _append_concept(destination)

        for ancestor in self.ancestors():
            if hasattr(ancestor, "roles"):
                for role in getattr(ancestor, "roles") or ():
                    actor = getattr(role, "actor", None)
                    _append_concept(actor)
            if hasattr(ancestor, "settings"):
                for setting in getattr(ancestor, "settings") or ():
                    location = getattr(setting, "location", None)
                    _append_concept(location)

        return concepts

    def attach_concept(self, concept: Concept) -> None:
        """Attach ``concept`` to the block if not already linked."""

        if concept.graph is not self.graph:
            raise ValueError("Concept does not belong to the same graph as the block")

        if self.graph.find_edge(source=self, destination=concept) is not None:
            return

        self.graph.add_edge(source=self, destination=concept)

    def detach_concept(self, concept: Concept) -> None:
        """Remove edges between this block and ``concept`` if present."""

        for edge in list(self.graph.find_edges(source=self, destination=concept)):
            self.graph.remove(edge)

    def get_choices(
        self,
        *,
        ns: Mapping[str, Any] | None = None,
        ctx: Context | None = None,
        **criteria,
    ) -> list[ChoiceEdge]:
        """
        Return available :class:`ChoiceEdge` (usually :class:`Action`) edges.

        By default excludes prereq/postreq triggers (`trigger_phase=None`).
        If `ns` is provided, filters by `edge.available(ns)`.

        Parameters
        ----------
        ns : Mapping[str, Any] | None
        **criteria : additional edge filters (e.g., `is_instance=Action`, `has_tags={...}`)

        Returns
        -------
        list[ChoiceEdge]
        """
        choices: list[ChoiceEdge] = []
        criteria.setdefault("trigger_phase", None)  # only blocking choices by default
        criteria.setdefault("is_instance", ChoiceEdge)
        block_ns = ns
        if block_ns is None and ctx is not None:
            block_ns = ctx.get_ns(self)

        for edge in self.edges_out(**criteria):
            if ctx is not None and isinstance(edge, Action):
                if not edge.is_available(ctx=ctx, ns=block_ns):
                    continue
            else:
                if block_ns is not None and not edge.available(block_ns):
                    continue
            choices.append(edge)
        return choices

    @story_dispatch.register(task=P.JOURNAL, priority=Prio.EARLY)
    def block_fragment(
        self: Block, *, ctx: Context, **locals_: Any
    ) -> list[BaseFragment] | None:
        """
        JOURNAL (EARLY): render inline content via ``journal_content`` handlers.

        Returns
        -------
        list[BaseFragment] | None
        """

        with ctx._fresh_call_receipts():
            content_receipts = story_dispatch.dispatch(
                self, ctx=ctx, task="journal_content"
            )
            content_fragments = CallReceipt.merge_results(*content_receipts)

        return content_fragments or None

    @on_journal_content(priority=Prio.NORMAL)
    def render_inline_content(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment]:
        """
        journal_content (NORMAL): render the inline ``content`` field.

        Checks for dialog syntax and emits attributed fragments when detected.
        """

        if not self.content:
            return []

        rendered = ContentRenderer.render_with_ctx(self.content, self, ctx=ctx)

        if DialogHandler.has_mu_blocks(rendered):
            mu_blocks = DialogHandler.parse(rendered, source_id=self.uid)
            return DialogHandler.render(mu_blocks)

        return [
            ContentFragment(
                content=rendered,
                source_id=self.uid,
                tags={f"source_label:{self.label}"} if self.label else None,
            )
        ]

    @story_dispatch.register(task=P.JOURNAL, priority=Prio.NORMAL)
    def describe_concepts(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
        """
        JOURNAL (NORMAL): collect "concept" fragments from child concepts.

        Returns
        -------
        list[BaseFragment] | None
        """
        fragments: list[BaseFragment] = []
        for concept in self.get_concepts():
            fragment = concept.concept_fragment(ctx=ctx)
            if fragment:
                fragments.append(fragment)
        return fragments or None

    # @story_dispatch.register(task=P.JOURNAL, priority=Prio.NORMAL)
    @on_get_choices(priority=Prio.EARLY)
    def provide_choices(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
        """
        get_choices (EARLY): collect "choice" fragments for outgoing actions.

        Returns
        -------
        list[ChoiceFragment] | None
        """
        fragments: list[BaseFragment] = []
        for choice in self.edges_out(is_instance=Action, trigger_phase=None):
            f = choice.choice_fragment(ctx=ctx)
            if f:
                fragments.append(f)
        return fragments or None

    @story_dispatch.register(task=P.JOURNAL, priority=Prio.LATE)
    def collect_choices(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
        """
        JOURNAL (LATE): merge choice fragments provided by ``get_choices`` handlers.
        """

        with ctx._fresh_call_receipts():
            choice_receipts = story_dispatch.dispatch(self, ctx=ctx, task="get_choices")
            choices = CallReceipt.merge_results(*choice_receipts)

        return choices or None


@story_dispatch.register(task=P.JOURNAL, priority=Prio.NORMAL)
def emit_media_fragments(block: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
    """JOURNAL: emit media fragments for resolved media dependencies."""

    fragments: list[MediaFragment] = []

    for edge in block.edges_out():
        if not isinstance(edge, MediaDep):
            continue
        if edge.destination is None:
            continue

        rit: MediaRIT = edge.destination
        content_type = rit.data_type or MediaDataType.MEDIA

        fragments.append(
            MediaFragment(
                content=rit,
                content_format="rit",
                content_type=content_type,
                media_role=edge.media_role,
                text=getattr(edge, "caption", None),
                source_id=block.uid,
                scope=getattr(edge, "scope", "world"),
            )
        )

    return fragments or None


@story_dispatch.register(task=P.INIT, priority=Prio.NORMAL)
def init_block_media(block: Block, *, ctx: Context, **_: Any) -> None:
    """INIT: attach static media dependencies declared on the block script."""

    world = getattr(ctx.graph, "world", None)
    if world is None:
        return

    block_script = None
    if hasattr(world, "get_block_script"):
        block_script = world.get_block_script(block.uid)

    if block_script is None:
        return

    attach_media_deps_for_block(graph=ctx.graph, block=block, script=block_script)
