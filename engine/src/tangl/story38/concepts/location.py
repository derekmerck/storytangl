from __future__ import annotations

from typing import Any

from tangl.core38 import contribute_ns
from tangl.vm38 import TraversableNode


class Location(TraversableNode):
    """Minimal location concept node for story38."""

    name: str = ""

    @contribute_ns
    def provide_location_symbols(self) -> dict[str, Any]:
        """Publish location attributes for namespace composition."""
        return {
            "label": self.get_label(),
            "name": self.name or self.get_label(),
        }
