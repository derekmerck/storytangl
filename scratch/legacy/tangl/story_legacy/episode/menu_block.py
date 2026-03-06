# tangl/story/episode/menu_block.py
"""
MenuBlock: hub block with dynamic choice provisioning.

MenuBlock extends :class:`Block` with two VM handlers:

* **PLANNING** – declare pull-style dependencies for compatible blocks.
* **UPDATE** – convert satisfied dependencies and affordances into
  :class:`Action` edges.

Rendering and journaling reuse :class:`Block`'s existing handlers.
"""

from __future__ import annotations

from typing import Any
import logging

from pydantic import Field

from tangl.core import Entity
from tangl.core.behavior import HandlerPriority as Prio
from tangl.core.entity import Selectable
from tangl.vm import Affordance, Context, Dependency, ProvisioningPolicy, Requirement
from tangl.vm import ResolutionPhase as P
from tangl.vm.dispatch import on_planning, on_update
from .action import Action
from .block import Block

logger = logging.getLogger(__name__)


class MenuBlock(Block, Selectable):
    """
    MenuBlock(selection_criteria: dict, within_scene: bool = True, auto_provision: bool = True)

    Hub block that auto-provisions choices from compatible blocks.

    Why
    ---
    Menu blocks act as hubs that surface available destinations without hardcoding
    outgoing :class:`Action` edges. They support both pull-style discovery via
    dependencies and push-style offerings via affordances.

    Key Features
    ------------
    * **Pull pattern** – declare :attr:`selection_criteria` and create
      dependencies during :class:`~tangl.vm.ResolutionPhase.PLANNING`.
    * **Push pattern** – accept incoming affordances and convert them to actions
      during :class:`~tangl.vm.ResolutionPhase.UPDATE`.
    * **Dynamic refresh** – clears old dynamic actions every update pass to keep
      menus in sync with the graph.

    Notes
    -----
    Action labels respect ``locals['action_text']`` first, then
    ``locals['menu_text']``, then the target label.
    """

    within_scene: bool = Field(default=True)
    auto_provision: bool = Field(default=True)

    @on_planning(priority=Prio.EARLY)
    def menu_create_dependencies(self, *, ctx: Context, **_: Any) -> list[Dependency] | None:
        """PLANNING: create dependencies for blocks matching ``selection_criteria``."""

        if not self.auto_provision:
            return None

        criteria = self.get_selection_criteria()
        if not criteria:
            return None

        candidates = self._find_menu_candidates(ctx=ctx, criteria=criteria)
        if not candidates:
            return None

        dependencies: list[Dependency] = []
        for candidate in candidates:
            if self._has_action_to(candidate):
                continue

            existing_deps = list(
                self.graph.find_edges(
                    source_id=self.uid,
                    destination_id=candidate.uid,
                    is_instance=Dependency,
                )
            )
            if existing_deps:
                continue

            requirement = Requirement(
                graph=self.graph,
                identifier=candidate.uid,
                criteria=criteria,
                policy=ProvisioningPolicy.EXISTING,
            )
            requirement.provider = candidate

            dependency = Dependency(
                graph=self.graph,
                source_id=self.uid,
                destination_id=None,
                requirement=requirement,
                label=f"menu_target_{candidate.label}" if candidate.label else "menu_target",
            )
            dependencies.append(dependency)

        return dependencies or None

    @on_update(priority=Prio.NORMAL)
    def menu_materialize_actions(self, *, ctx: Context, **_: Any) -> list[Action] | None:
        """UPDATE: convert satisfied dependencies and affordances into :class:`Action` edges."""

        if not self.auto_provision:
            return None

        self._clear_dynamic_menu_actions()

        actions: list[Action] = []

        menu_deps = list(
            self.graph.find_edges(
                source_id=self.uid,
                is_instance=Dependency,
            )
        )
        for dependency in menu_deps:
            if not dependency.satisfied:
                continue

            target_block = dependency.destination
            if target_block is None:
                continue

            action = self._create_menu_action(
                target=target_block,
                tags={"dynamic", "menu", "dependency"},
            )
            if action is not None:
                actions.append(action)

        affordances = list(
            self.graph.find_edges(
                destination_id=self.uid,
                is_instance=Affordance,
            )
        )
        for affordance in affordances:
            if not affordance.satisfied:
                continue

            source_block = affordance.source
            if source_block is None:
                continue

            action = self._create_menu_action(
                target=source_block,
                tags={"dynamic", "menu", "affordance"},
            )
            if action is not None:
                actions.append(action)

        return actions or None

    def _create_menu_action(self, *, target: Entity, tags: set[str]) -> Action | None:
        """Create an :class:`Action` edge to ``target`` unless one already exists."""

        if self._has_action_to(target):
            return None

        destination = self._resolve_destination(target)
        action_label = self._get_action_label(target)

        return Action(
            graph=self.graph,
            source_id=self.uid,
            destination_id=destination.uid,
            label=action_label,
            content=action_label,
            tags=tags,
        )

    def _clear_dynamic_menu_actions(self) -> None:
        """Remove stale dynamic actions before reprovisioning."""

        for edge in list(
            self.graph.find_edges(
                source_id=self.uid,
                is_instance=Action,
                has_tags={"dynamic", "menu"},
            )
        ):
            self.graph.remove(edge)

    def _find_menu_candidates(self, *, ctx: Context, criteria: dict[str, Any] | None = None) -> list[Entity]:
        """Return nodes matching ``selection_criteria`` within the configured scope."""

        criteria = criteria or self.get_selection_criteria()
        if self.within_scene:
            scene = self._get_scene()
            if scene is None:
                candidates = list(self.graph.find_nodes(**criteria))
            else:
                candidates = list(scene.find_all(**criteria))
        else:
            candidates = list(self.graph.find_nodes(**criteria))

        return [candidate for candidate in candidates if candidate.uid != self.uid]

    def _get_scene(self):
        from .scene import Scene

        for scene in self.graph.find_nodes(is_instance=Scene):
            if self.uid in scene.member_ids:
                return scene
        return None

    def _resolve_destination(self, node: Entity) -> Entity:
        from .scene import Scene

        if isinstance(node, Scene):
            return node.source
        return node

    def _get_action_label(self, block: Entity) -> str:
        return (
            getattr(block, "locals", {}).get("action_text")
            or getattr(block, "locals", {}).get("menu_text")
            or block.label
        )

    def _has_action_to(self, target: Entity) -> bool:
        return self.graph.find_edge(
            source_id=self.uid,
            destination_id=target.uid,
            is_instance=Action,
        ) is not None
