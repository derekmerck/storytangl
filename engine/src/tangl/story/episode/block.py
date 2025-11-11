"""Block primitive for the reference narrative domain."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from tangl.type_hints import StringMap
from tangl.core import BaseFragment, Node, Graph
from tangl.core.behavior import HasBehaviors
from tangl.vm import ResolutionPhase as P, ChoiceEdge, Context
from tangl.story.dispatch import story_dispatch
from tangl.story.runtime import ContentRenderer
from tangl.story.concepts import Concept
from .action import Action

class Block(Node, HasBehaviors):
    """Block(label: str, content: str = "")

    Structural node that groups :class:`Concept` children and presents
    player choices.

    Why
    ----
    Blocks act as the smallest interactive unit—collecting prose fragments and
    then surfacing decisions to advance the story.

    Key Features
    ------------
    * **Inline prose** – optional :attr:`content` rendered before child concepts.
    * **Concept aggregation** – :meth:`get_concepts` yields child
      :class:`Concept` nodes in creation order.
    * **Choice presentation** – :meth:`get_choices` filters available
      :class:`~tangl.vm.frame.ChoiceEdge` options using the active namespace.

    API
    ---
    - :attr:`content` – convenience prose field.
    - :meth:`get_concepts` – iterate child concepts.
    - :meth:`get_choices` – list available choices for UI rendering.
    """

    content: str = ""

    def get_concepts(self) -> list[Concept]:
        """Return child :class:`Concept` nodes in stable order."""

        concepts: list[Concept] = []
        for edge in self.edges_out():
            destination = edge.destination
            if isinstance(destination, Concept):
                concepts.append(destination)
        return concepts

    def get_choices(self, *, ns: Mapping[str, Any] | None = None, **criteria) -> list[ChoiceEdge]:
        """Return available :class:`Action` instances from this block."""

        choices: list[ChoiceEdge] = []
        criteria.setdefault("trigger_phase", None)  # only blocking choices by default
        criteria.setdefault("is_instance", ChoiceEdge)
        for edge in self.edges_out(**criteria):
            if ns is not None and not edge.available(ns):
                continue
            choices.append(edge)
        return choices

    @story_dispatch.register(task=P.JOURNAL)
    def block_fragment(self: Block, *, ctx: Context, **locals_: Any) -> BaseFragment | None:
        """Render inline content for a block."""
        content = ContentRenderer.render_with_ctx(self.content, self, ctx=ctx)
        if content:
            return BaseFragment(
                content=content,
                source_id=self.uid,
                source_label=self.label,
                fragment_type="block",
            )

    @story_dispatch.register(task=P.JOURNAL)
    def provide_choices(self: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
        ns = ctx.get_ns(self)
        fragments: list[BaseFragment] = []
        for choice in self.get_choices(ns=ns, is_instance=Action):
            f = choice.choice_fragment(ctx=ctx)
            if f:
                fragments.append(f)
        return fragments or None

    @story_dispatch.register(task=P.JOURNAL)
    def describe_concepts(self: Block, *, ctx: Context, **_: Any) -> StringMap | None:
        fragments: list[BaseFragment] = []
        for concept in self.get_concepts():
            fragments.append(concept.concept_fragment(ctx=ctx))
        return fragments or None
