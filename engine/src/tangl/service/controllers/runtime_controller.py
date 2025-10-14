# tangl/service/controllers/runtime_controller.py
"""Runtime controller bridging orchestrator calls to the VM layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from tangl.core import BaseFragment, StreamRegistry
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)
from tangl.vm.frame import ChoiceEdge, Frame
from tangl.vm.ledger import Ledger
from tangl.service.user.user import User


class RuntimeController(HasApiEndpoints):
    """Orchestrate ledger/frame interactions for live story state."""

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.CONTENT,
    )
    def get_journal_entries(self, ledger: Ledger, limit: int = 10) -> list[BaseFragment]:
        """Return the most recent journal fragments from a ledger."""

        if limit < 0:
            raise ValueError("limit must be non-negative")

        fragments = list(ledger.records.iter_channel("fragment"))
        if limit == 0 or limit >= len(fragments):
            return fragments
        return fragments[-limit:]

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
    )
    def resolve_choice(
        self,
        ledger: Ledger,
        frame: Frame,
        choice_id: UUID,
    ) -> dict[str, Any]:
        """Resolve a player choice and update the ledger cursor."""

        choice = frame.graph.get(choice_id)
        if not isinstance(choice, ChoiceEdge):
            raise ValueError(f"Choice {choice_id} not found")

        frame.resolve_choice(choice)

        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step

        return {
            "status": "resolved",
            "cursor_id": str(ledger.cursor_id),
            "step": ledger.step,
        }

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
    )
    def get_story_info(self, ledger: Ledger) -> dict[str, Any]:
        """Summarize the current ledger state for diagnostics."""

        return {
            "title": ledger.graph.label,
            "step": ledger.step,
            "cursor_id": ledger.cursor_id,
            "journal_size": sum(1 for _ in ledger.records.iter_channel("fragment")),
        }

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
    )
    def get_available_choices(self, ledger: Ledger) -> list[dict[str, Any]]:
        """Return lightweight metadata for the cursor's outgoing choices."""

        node = ledger.graph.get(ledger.cursor_id)
        if node is None:
            return []

        choices: list[dict[str, Any]] = []
        for edge in ledger.graph.find_edges(source_id=node.uid):
            if not isinstance(edge, ChoiceEdge):
                continue
            label = getattr(edge, "text", None) or getattr(edge, "label", None) or ""
            choices.append({"uid": edge.uid, "label": label})
        return choices

    @ApiEndpoint.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
    )
    def jump_to_node(self, ledger: Ledger, node_id: UUID) -> dict[str, Any]:
        """Teleport the ledger cursor to ``node_id`` for debugging purposes."""

        from tangl.core.graph.edge import AnonymousEdge

        destination = ledger.graph.get(node_id)
        if destination is None:
            raise ValueError(f"Node {node_id} not found in graph")

        if not destination.has_tags("dirty"):
            destination.tags = set(destination.tags) | {"dirty"}

        source = ledger.graph.get(ledger.cursor_id)
        if source is None:
            raise RuntimeError(f"Ledger cursor {ledger.cursor_id} not found in graph")

        jump_edge = AnonymousEdge(source=source, destination=destination)

        frame = ledger.get_frame()
        frame.resolve_choice(jump_edge)

        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step

        return {
            "status": "jumped",
            "cursor_id": str(ledger.cursor_id),
            "step": ledger.step,
            "dirty": True,
        }

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> dict[str, Any]:
        """Create a fully-materialized story ledger for ``user``."""

        from tangl.story.fabula.world import World

        world = World.get_instance(world_id)
        if world is None:
            raise ValueError(f"World '{world_id}' not found. Load it first.")

        story_label = kwargs.get("story_label") or f"story_{user.uid}"
        story_graph = world.create_story(story_label, mode="full")
        start_cursor_id = story_graph.cursor.cursor_id

        ledger = Ledger(
            graph=story_graph,
            cursor_id=start_cursor_id,
            records=StreamRegistry(),
            label=story_label,
        )
        ledger.push_snapshot()
        ledger.init_cursor()

        user.current_ledger_id = ledger.uid  # type: ignore[attr-defined]

        cursor_node = story_graph.get(ledger.cursor_id)
        cursor_label = cursor_node.label if cursor_node is not None else "unknown"

        return {
            "status": "created",
            "ledger_id": str(ledger.uid),
            "world_id": world_id,
            "title": story_graph.label,
            "cursor_id": str(ledger.cursor_id),
            "cursor_label": cursor_label,
            "step": ledger.step,
            "ledger": ledger,
        }
