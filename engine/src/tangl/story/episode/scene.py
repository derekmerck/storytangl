from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.vm import TraversableNode


class Scene(TraversableNode):
    """Scene()

    Container node that groups blocks into a traversable narrative segment.

    Why
    ----
    Scenes provide the structural scope that blocks, roles, and settings hang
    from. They also maintain source and sink pointers so container traversal is
    deterministic once children are materialized.

    Key Features
    ------------
    * Groups blocks into a shared traversal and namespace scope.
    * Carries scene-level role and setting declarations.
    * Owns source/sink cursor pointers used by container traversal.

    API
    ---
    - :attr:`title` stores the authored scene heading.
    - :attr:`roles` and :attr:`settings` hold scene-scope provider
      declarations.
    - :meth:`finalize_container_contract` derives missing source/sink ids from
      current child order.
    """

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
