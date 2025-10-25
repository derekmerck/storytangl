"""Block primitive for the reference narrative domain."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import jinja2

from tangl.core import BaseFragment, Graph, Node, global_domain
from tangl.vm.context import Context
from tangl.vm.frame import ChoiceEdge, ResolutionPhase as P
from tangl.vm.domain import TraversableDomain

from tangl.story.concepts.concept import Concept

__all__ = ["Block"]


def _normalize_ns(ns: Any) -> Mapping[str, Any] | None:
    """Return a mapping suitable for formatting or ``None`` if unavailable."""

    if ns is None:
        return None
    if isinstance(ns, Mapping):
        return ns
    try:
        return dict(ns)
    except TypeError:
        return None


class Block(TraversableDomain, Node):
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

    def get_choices(self, *, ns: Mapping[str, Any] | None = None) -> list[ChoiceEdge]:
        """Return available :class:`ChoiceEdge` instances from this block."""

        choices: list[ChoiceEdge] = []
        for edge in self.edges_out(is_instance=ChoiceEdge):
            if ns is not None and not edge.available(ns):
                continue
            choices.append(edge)
        return choices


@global_domain.handlers.register(
    phase=P.JOURNAL,
    priority=40,
    selection_criteria={"is_instance": Block},
)
def render_block(cursor: Block, *, ctx: Context, **_: Any) -> list[BaseFragment] | None:
    """Render inline content, child concepts, and choice menu for a block."""

    ns_raw = ctx.get_ns()
    ns = _normalize_ns(ns_raw)
    fragments: list[BaseFragment] = []

    if not isinstance(cursor, Block):  # pragma: no cover - defensive guard
        return None

    if cursor.content:
        if ns is None:
            inline_text = cursor.content
        else:
            tmpl = jinja2.Template(cursor.content)
            inline_text = tmpl.render(**ns)
            # try:
            #     inline_text = cursor.content.format_map(ns)
            # except (KeyError, ValueError):
            #     inline_text = cursor.content
        fragments.append(
            BaseFragment(
                content=inline_text,
                source_id=cursor.uid,
                source_label=cursor.label,
                fragment_type="block_content",
            )
        )

    for concept in cursor.get_concepts():
        rendered = concept.render(ns_raw)
        fragments.append(
            BaseFragment(
                content=rendered,
                source_id=concept.uid,
                source_label=concept.label,
                fragment_type="concept",
            )
        )

    # todo: Choices are themselves fragments, so we need to call render on each of our choices and add them to the stream
    choices = cursor.get_choices(ns=ns)
    if choices:
        lines = [""]
        for index, choice in enumerate(choices, start=1):
            destination = choice.destination
            label = choice.label or (destination.label if destination is not None else "")
            lines.append(f"{index}. {label}")
        fragments.append(
            BaseFragment(
                content="\n".join(lines),
                source_id=cursor.uid,
                source_label=f"{cursor.label}_menu",
                fragment_type="choice_menu",
            )
        )

    return fragments or None


Block.model_rebuild(_types_namespace={"Graph": Graph})
