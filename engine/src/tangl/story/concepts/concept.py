"""Simple concept node for the reference narrative domain."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tangl.core import BaseFragment, Graph, Node, global_domain
from tangl.core.domain import NS
from tangl.vm.context import Context
from tangl.vm.frame import ResolutionPhase as P
from pydantic import Field
import logging

__all__ = ["Concept"]

logger = logging.getLogger(__name__)

class Concept(Node):
    """Concept(label: str, content: str = "")

    Minimal narrative node that stores textual content and renders it into the
    journal.

    Why
    ----
    Story graphs need a lightweight primitive for emitting prose without pulling
    in application-specific abstractions. ``Concept`` keeps the behavior
    focused on formatting text during the JOURNAL phase.

    Key Features
    ------------
    * **Text content** – the :attr:`content` field holds raw prose for the node.
    * **Templating** – :meth:`render` performs best-effort ``str.format``
      substitution from the active namespace.
    * **Auto-journal** – a domain handler converts the rendered text into a
      :class:`~tangl.core.fragment.BaseFragment`.

    API
    ---
    - :attr:`content` – raw string assigned by builders or parsers.
    - :meth:`render` – resolve the content against a namespace mapping.
    """

    content: str = ""
    locals: Mapping[str, Any] = Field(default_factory=dict)

    # concepts render pre-fragments with 'describe()'?
    # render is for episodes to assemble a fragment stream with any required describe() pre-fragments

    def describe(self):
        ...

    def render(self, ns: NS | Mapping[str, Any]) -> str:
        """Return :attr:`content` with namespace variables substituted.

        Parameters
        ----------
        ns:
            Namespace mapping exposed by the active :class:`~tangl.core.domain.Scope`.

        Notes
        -----
        Missing keys or malformed format strings fall back to the raw content to
        ensure journal output is never interrupted by template errors.
        """

        mapping: Mapping[str, Any]
        if isinstance(ns, Mapping):
            mapping = ns
        else:
            mapping = dict(ns)

        try:
            return self.content.format_map(mapping)
        except (KeyError, ValueError) as e:
            logger.debug(f"Caught an error: {e}")
            logger.debug(dict(ns))
            return self.content

# todo: this should _very_ obviously be added to the 'story domain' domain rather than the global domain...
from tangl.vm.simple_handlers import on_journal
from tangl.core.dispatch import HandlerPriority as Prio
@on_journal(priority=Prio.EARLY)
# @global_domain.handlers.register(phase=P.JOURNAL, priority=45)
def render_concept_to_fragment(concept: Concept, *, ctx: Context, **_: Any) -> BaseFragment | None:
    """Emit a :class:`~tangl.core.fragment.BaseFragment` when the cursor is a concept."""

    if not isinstance(concept, Concept):  # pragma: no cover - defensive guard
        return None

    ns = ctx.get_ns()
    rendered = concept.render(ns)
    return BaseFragment(
        content=rendered,
        source_id=concept.uid,
        source_label=concept.label,
        fragment_type="content",
    )


Concept.model_rebuild(_types_namespace={"Graph": Graph})
