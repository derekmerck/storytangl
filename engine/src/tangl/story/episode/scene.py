"""Scene primitive for the reference narrative domain."""
from __future__ import annotations
from typing import Any

from pydantic import PrivateAttr

from tangl.core import Graph, Node
from tangl.core.behavior import HasBehaviors
from tangl.vm.dispatch import on_get_ns
from tangl.vm.traversal import TraversableSubgraph
from tangl.story.concepts.actor import Role
from tangl.story.concepts.location import Setting
from .block import Block

# todo: templates for member blocks should be included at the domain level
#       here, so we can ask for a block named "start" and get the one that
#       belongs to _this_ scene and not some other unrelated scene.
#       Need to consider how global domain templates can be restricted to
#       instance structural domains by name or origin or something.

class Scene(TraversableSubgraph, HasBehaviors):
    """Scene(label: str, member_ids: list[Node], entry_ids: list[Node] | None = None, exit_ids: list[Node] | None = None)

    Structural domain that groups :class:`Block` members and projects
    satisfied edges into the namespace.

    Why
    ----
    Scenes provide the narrative boundary around a set of blocks. They expose
    a canonical source/sink for traversal, aggregate shared resources, and make
    dependency results visible to prose through the namespace stack.

    Key Features
    ------------
    * **Canonical traversal** – inherits single source/sink wiring from
      :class:`~tangl.vm.domain.TraversableDomain`.
    * **Block introspection** – :meth:`get_member_blocks` and the
      :attr:`entry_blocks`/:attr:`exit_blocks` helpers expose structural members.
    * **Edge projection** – :meth:`refresh_edge_projections` mirrors satisfied
      :class:`~tangl.vm.planning.open_edge.Dependency` and
      :class:`~tangl.vm.planning.open_edge.Affordance` edges into ``vars``.

    API
    ---
    - :meth:`get_member_blocks` – list the :class:`Block` members.
    - :attr:`entry_blocks` / :attr:`exit_blocks` – resolve entry/exit members.
    - :meth:`refresh_edge_projections` – update namespace mirrors for edges.
    """

    _base_vars: dict[str, Any] | None = PrivateAttr(default=None)
    _projected_keys: set[str] = PrivateAttr(default_factory=set)

    @property
    def blocks(self) -> list[Block]:
        """Return all member nodes that are :class:`Block` instances."""
        return list(self.find_all(is_instance=Block))

    def get_member_blocks(self):
        return self.blocks

    @property
    def entry_blocks(self) -> list[Block]:
        """Return entry nodes filtered to :class:`Block` instances."""

        blocks: list[Block] = []
        for uid in self.entry_node_ids:
            node = self.graph.get(uid)
            if isinstance(node, Block):
                blocks.append(node)
        return blocks

    @property
    def exit_blocks(self) -> list[Block]:
        """Return exit nodes filtered to :class:`Block` instances."""

        blocks: list[Block] = []
        for uid in self.exit_node_ids:
            node = self.graph.get(uid)
            if isinstance(node, Block):
                blocks.append(node)
        return blocks

    @property
    def settings(self) -> list[Setting]:
        """Return all locations assigned to this :class:`Scene`."""
        return list(self.graph.find_edges(source=self, is_instance=Setting))

    @on_get_ns()
    def _contribute_settings_to_ns(self, ctx=None):
        if self.settings:
            return { s.get_label(): s.location for s in self.settings }

    @property
    def roles(self) -> list[Role]:
        """Return all roles assigned to this :class:`Scene`."""
        return list(self.graph.find_edges(source=self, is_instance=Role))

    @on_get_ns()
    def _contribute_roles_to_ns(self, ctx=None):
        if self.roles:
            return { r.get_label(): r.actor for r in self.roles }
