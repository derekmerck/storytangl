from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.vm import TraversableNode


class Scene(TraversableNode):
    """Container node grouping block members."""

    title: str = ""
    roles: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)

    def finalize_container_contract(self) -> None:
        """Populate source/sink ids from current child order when absent."""
        children = list(self.children())
        if children:
            if self.source_id is None:
                self.source_id = children[0].uid
            if self.sink_id is None:
                self.sink_id = children[-1].uid
