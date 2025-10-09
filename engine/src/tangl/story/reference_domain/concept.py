"""Simple concept node for the reference narrative domain."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tangl.core import BaseFragment, Graph, Node, global_domain
from tangl.core.domain import NS
from tangl.vm import Context, ResolutionPhase as P

__all__ = ["SimpleConcept"]


class SimpleConcept(Node):
    """SimpleConcept(label: str, content: str = "")

    Minimal narrative node that stores textual content and renders it into the
    journal.

    Why
    ----
    Story graphs need a lightweight primitive for emitting prose without pulling
    in application-specific abstractions. ``SimpleConcept`` keeps the behavior
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
        except (KeyError, ValueError):
            return self.content


@global_domain.handlers.register(phase=P.JOURNAL, priority=45)
def render_concept_to_fragment(cursor: Node, *, ctx: Context, **_: Any) -> BaseFragment | None:
    """Emit a :class:`~tangl.core.fragment.BaseFragment` when the cursor is a concept."""

    if not isinstance(cursor, SimpleConcept):  # pragma: no cover - defensive guard
        return None

    ns = ctx.get_ns()
    rendered = cursor.render(ns)
    return BaseFragment(
        content=rendered,
        source_id=cursor.uid,
        source_label=cursor.label,
        fragment_type="content",
    )


SimpleConcept.model_rebuild(_types_namespace={"Graph": Graph})
