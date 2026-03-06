from __future__ import annotations

from typing import Any

from tangl.core import Node, contribute_ns


class Actor(Node):
    """Actor()

    Named character provider published into the story namespace.
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
