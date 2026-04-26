"""Location-hub facade for sandbox mechanics."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core import contribute_ns
from tangl.story import MenuBlock


class SandboxLocation(MenuBlock):
    """A visitable dynamic hub with location links."""

    links: dict[str, str] = Field(default_factory=dict)
    sandbox_scope: str | None = None
    location_name: str = ""

    @contribute_ns
    def provide_sandbox_location_symbols(self) -> dict[str, Any]:
        """Publish location metadata to the gathered namespace."""
        payload: dict[str, Any] = {
            "current_location": self,
            "current_location_label": self.get_label(),
            "current_location_name": self.location_name or self.get_label(),
        }
        if self.sandbox_scope:
            payload["sandbox_scope"] = self.sandbox_scope
        return payload
