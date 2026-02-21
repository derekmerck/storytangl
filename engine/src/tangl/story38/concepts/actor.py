from __future__ import annotations

from typing import Any

from tangl.vm38 import TraversableNode, on_get_ns


class Actor(TraversableNode):
    """Minimal actor concept node for story38."""

    name: str = ""

    @on_get_ns
    def on_get_ns(self, ctx) -> dict[str, Any]:
        """Publish actor attributes for namespace composition.

        Temporary bridge: ``on_get_ns`` remains transitional until scoped-dispatch
        returns as a first-class mechanism.
        """
        payload: dict[str, Any] = {
            "label": self.get_label(),
            "name": self.name or self.get_label(),
        }
        if hasattr(self, "locals") and self.locals:
            payload.update(dict(self.locals))
        return payload
