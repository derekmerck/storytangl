from __future__ import annotations

from typing import Any

from tangl.core import Node, contribute_ns


class Actor(Node):
    """Actor()

    Named character provider published into the story namespace.

    Why
    ----
    ``Actor`` gives story templates a lightweight provider node for named
    characters. Role edges can resolve against these nodes without needing a
    story-specific provider protocol.

    Key Features
    ------------
    * Stores a human-friendly ``name`` alongside the graph label.
    * Publishes actor metadata into local namespace composition via
      :meth:`provide_actor_symbols`.

    API
    ---
    - :attr:`name` stores the authored display name.
    - :meth:`provide_actor_symbols` returns the namespace payload contributed by
      this actor.
    """

    name: str = ""

    @contribute_ns
    def provide_actor_symbols(self) -> dict[str, Any]:
        """Publish actor attributes for namespace composition."""
        payload: dict[str, Any] = {
            "label": self.get_label(),
            "name": self.name or self.get_label(),
        }
        if hasattr(self, "locals") and self.locals:
            payload.update(dict(self.locals))
        return payload
