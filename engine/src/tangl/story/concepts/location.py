from __future__ import annotations

from typing import Any

from tangl.core import contribute_ns
from tangl.vm import TraversableNode
from .narrator_knowledge import HasNarratorKnowledge


class Location(HasNarratorKnowledge, TraversableNode):
    """Location()

    Named place provider published into the story namespace.

    Why
    ----
    ``Location`` provides a concrete traversable node that settings and runtime
    namespace gathering can reference when a story needs a place-oriented
    provider.

    Key Features
    ------------
    * Carries a human-friendly ``name`` alongside the graph label.
    * Carries narrator-facing epistemic annotations on the location itself.
    * Publishes location metadata into the scoped namespace through
      :meth:`provide_location_symbols`.

    API
    ---
    - :attr:`name` stores the authored display name.
    - :meth:`provide_location_symbols` returns the namespace payload exposed by
      this location.
    """

    name: str = ""

    @contribute_ns
    def provide_location_symbols(self) -> dict[str, Any]:
        """Publish location attributes for namespace composition."""
        return {
            "label": self.get_label(),
            "name": self.name or self.get_label(),
        }
