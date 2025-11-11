"""Simple concept node for the reference narrative domain."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import logging

from pydantic import Field

from tangl.core import BaseFragment, Node, Graph
from tangl.core.behavior import HasBehaviors
from tangl.story.runtime.render import ContentRenderer
from tangl.vm.context import Context

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class Concept(Node, HasBehaviors):
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
      :class:`~tangl.core.BaseFragment`.

    API
    ---
    - :attr:`content` – raw string assigned by builders or parsers.
    - :meth:`render` – resolve the content against a namespace mapping.
    """

    content: str = ""
    locals: Mapping[str, Any] = Field(default_factory=dict)

    # concepts generate pre-fragments with 'describe()'

    def describe(self, *, ctx: Context = None, ns: dict = None, **locals_) -> str:
        """Return :attr:`content` with namespace variables substituted.

        Parameters
        ----------
        ns:
            Namespace mapping exposed by the active behavior layers.

        Notes
        -----
        Missing keys or malformed format strings fall back to the raw content to
        ensure journal output is never interrupted by template errors.
        """
        if not self.content:
            return
        if ctx is not None:
            renderer = ContentRenderer.from_context(ctx)
            ns = ctx.get_ns(self)
        else:
            renderer = ContentRenderer()
            ns = ns or {}
        return renderer.render_str(self.content, ns=ns, **locals_)

    def concept_fragment(self, ctx: Context = None, **locals_: Any) -> BaseFragment:
            content = self.describe(ctx=ctx, **locals_)
            if content:
                return BaseFragment(
                    content=content,
                    source_id=self.uid,
                    source_label=self.label,
                    fragment_type="concept",
                )
