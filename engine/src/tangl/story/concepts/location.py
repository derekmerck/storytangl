from __future__ import annotations

from typing import Any

from tangl.core import contribute_ns
from tangl.vm import TraversableNode


class Location(TraversableNode):
    """Location()

    Named place provider published into the story namespace.
    """

    name: str = ""

    @contribute_ns
    def provide_location_symbols(self) -> dict[str, Any]:
        """Publish location attributes for namespace composition."""
        return {
            "label": self.get_label(),
            "name": self.name or self.get_label(),
        }
