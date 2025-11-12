# tangl/story/episode/block.py
"""
Block: cursor node that orchestrates JOURNAL fragments.

Three JOURNAL handlers (same task, different priorities):
1) block_fragment (EARLY): render inline block content → "block" fragment
2) describe_concepts (NORMAL): render child concepts → "concept" fragments
3) provide_choices (LATE): render outgoing actions → "choice" fragments

Only blocks register JOURNAL handlers; other nodes contribute fragments on request.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from tangl.core import BaseFragment, Node, Graph
from tangl.core.behavior import HasBehaviors, HandlerPriority as Prio
from tangl.vm import ResolutionPhase as P, ChoiceEdge, Context
from tangl.story.dispatch import story_dispatch
from tangl.story.runtime import ContentRenderer
from tangl.story.concepts import Concept
from .action import Action

class Block(Node, HasBehaviors):
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

    def get_concepts(self) -> list[Concept]:
        """
        Return direct child :class:`Concept` nodes in creation order.

        Returns
        -------
        list[Concept]
        """
        concepts: list[Concept] = []
        for edge in self.edges_out():
            destination = edge.destination
            if isinstance(destination, Concept):
                concepts.append(destination)
        return concepts

    def get_choices(self, *, ns: Mapping[str, Any] | None = None, **criteria) -> list[ChoiceEdge]:
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
        for edge in self.edges_out(**criteria):
            if ns is not None and not edge.available(ns):
                continue
            choices.append(edge)
        return choices

    @story_dispatch.register(task=P.JOURNAL, priority=Prio.EARLY)
    def block_fragment(self: Block, *, ctx: Context, **locals_: Any) -> BaseFragment | None:
        """
        JOURNAL (EARLY): render `content` and wrap as a "block" fragment.

        Returns
        -------
        BaseFragment | None
        """
        content = ContentRenderer.render_with_ctx(self.content, self, ctx=ctx)
        if content:
            return BaseFragment(
                content=content,
                source_id=self.uid,
                source_label=self.label,
                fragment_type="block",
            )
        # todo: the Block fragment type actually expects a list of 'choice' fragments as a parameter, we can consider that later

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
            fragments.append(concept.concept_fragment(ctx=ctx))
        return fragments or None

    @story_dispatch.register(task=P.JOURNAL, priority=Prio.LATE)
    def provide_choices(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
        """
        JOURNAL (LATE): collect "choice" fragments for available actions.

        Returns
        -------
        list[BaseFragment] | None
        """
        ns = ctx.get_ns(self)
        fragments: list[BaseFragment] = []
        for choice in self.get_choices(ns=ns, is_instance=Action):
            f = choice.choice_fragment(ctx=ctx)
            if f:
                fragments.append(f)
        return fragments or None
