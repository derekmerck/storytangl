"""Scene primitive for the reference narrative domain."""
from __future__ import annotations
from typing import Any

from pydantic import PrivateAttr

from tangl.core import Graph, Node
from tangl.core.dispatch.behavior_registry import HasBehaviors
from tangl.vm.vm_dispatch.on_get_ns import on_get_ns
from tangl.vm.domain import TraversableDomain
from tangl.vm.planning import Affordance, Dependency
from ..concepts.actor import Role
from ..concepts.location import Setting

from .block import Block

__all__ = ["Scene"]

# todo: templates for member blocks should be included at the domain level
#       here, so we can ask for a block named "start" and get the one that
#       belongs to _this_ scene and not some other unrelated scene.
#       Need to consider how global domain templates can be restricted to
#       instance structural domains by name or origin or something.

class Scene(TraversableDomain, HasBehaviors):
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

    @on_get_ns.register()
    def _contribute_settings_to_ns(self, ctx=None):
        if self.settings:
            return { 'settings': { s.get_label(): s.location for s in self.settings } }

    @property
    def roles(self) -> list[Role]:
        """Return all roles assigned to this :class:`Scene`."""
        return list(self.graph.find_edges(source=self, is_instance=Role))

    @on_get_ns.register()
    def _contribute_roles_to_ns(self, ctx=None):
        if self.roles:
            return { 'roles': { r.get_label(): r.actor for r in self.roles }}

    def refresh_edge_projections(self) -> None:
        """Project satisfied dependency and affordance edges into ``vars``."""

        current_vars = dict(self.vars)
        previous_projected = getattr(self, "_projected_keys", set())
        base_vars = getattr(self, "_base_vars", None)

        if base_vars is None:
            base_vars = current_vars
        else:
            # Remove base keys that were deleted between refreshes.
            for key in list(base_vars.keys()):
                if key not in current_vars and key not in previous_projected:
                    base_vars.pop(key, None)
            # Capture manual updates to non-projected keys.
            for key, value in current_vars.items():
                if key not in previous_projected:
                    base_vars[key] = value

        projected = dict(base_vars)
        projected_keys: set[str] = set()

        for block in self.get_member_blocks():
            for edge in block.edges_out(is_instance=Dependency):
                label = edge.label
                if not label:
                    continue
                satisfied_key = f"{label}_satisfied"
                provider = edge.destination
                if provider is not None:
                    projected[label] = provider
                elif label not in base_vars:
                    projected.pop(label, None)
                projected[satisfied_key] = edge.satisfied
                projected_keys.add(label)
                projected_keys.add(satisfied_key)

            for edge in block.edges_in(is_instance=Affordance):
                label = edge.label
                if not label:
                    continue
                satisfied_key = f"{label}_satisfied"
                provider = edge.source
                if provider is not None:
                    projected[label] = provider
                elif label not in base_vars:
                    projected.pop(label, None)
                projected[satisfied_key] = edge.satisfied
                projected_keys.add(label)
                projected_keys.add(satisfied_key)

        # Update the existing mapping in-place so cached namespaces keep the reference.
        self.vars.clear()
        self.vars.update(projected)
        self._base_vars = base_vars
        self._projected_keys = projected_keys


Scene.model_rebuild(_types_namespace={"Graph": Graph, "Node": Node})
