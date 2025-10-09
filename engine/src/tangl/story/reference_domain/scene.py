"""Scene primitive for the reference narrative domain."""

from __future__ import annotations

from typing import Any

from pydantic import PrivateAttr

from tangl.core import Graph, Node
from tangl.vm.domain import TraversableDomain
from tangl.vm.planning import Affordance, Dependency

from .block import SimpleBlock

__all__ = ["SimpleScene"]


class SimpleScene(TraversableDomain):
    """SimpleScene(label: str, member_ids: list[Node], entry_ids: list[Node] | None = None, exit_ids: list[Node] | None = None)

    Structural domain that groups :class:`SimpleBlock` members and projects
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
    - :meth:`get_member_blocks` – list the :class:`SimpleBlock` members.
    - :attr:`entry_blocks` / :attr:`exit_blocks` – resolve entry/exit members.
    - :meth:`refresh_edge_projections` – update namespace mirrors for edges.
    """

    _base_vars: dict[str, Any] | None = PrivateAttr(default=None)
    _projected_keys: set[str] = PrivateAttr(default_factory=set)

    def get_member_blocks(self) -> list[SimpleBlock]:
        """Return all member nodes that are :class:`SimpleBlock` instances."""

        blocks: list[SimpleBlock] = []
        for member_id in self.member_ids:
            node = self.graph.get(member_id)
            if isinstance(node, SimpleBlock):
                blocks.append(node)
        return blocks

    @property
    def entry_blocks(self) -> list[SimpleBlock]:
        """Return entry nodes filtered to :class:`SimpleBlock` instances."""

        blocks: list[SimpleBlock] = []
        for uid in self.entry_node_ids:
            node = self.graph.get(uid)
            if isinstance(node, SimpleBlock):
                blocks.append(node)
        return blocks

    @property
    def exit_blocks(self) -> list[SimpleBlock]:
        """Return exit nodes filtered to :class:`SimpleBlock` instances."""

        blocks: list[SimpleBlock] = []
        for uid in self.exit_node_ids:
            node = self.graph.get(uid)
            if isinstance(node, SimpleBlock):
                blocks.append(node)
        return blocks

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

        self.vars = projected
        self._base_vars = base_vars
        self._projected_keys = projected_keys


SimpleScene.model_rebuild(_types_namespace={"Graph": Graph, "Node": Node})
