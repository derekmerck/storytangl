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
    def get_journal_entries(
        self, ledger: Ledger, limit: int = 10, *, current_only: bool = False
    ) -> list[BaseFragment]:
        """Return journal fragments from a ledger.

        Parameters
        ----------
        ledger:
            Ledger to read from.
        limit:
            Maximum number of fragments to return. ``0`` means no limit.
        current_only:
            If true, return only the fragments from the latest step marker.
        """

        if limit < 0:
            raise ValueError("limit must be non-negative")

        fragments = list(ledger.records.iter_channel("fragment"))
        if 0 < limit < len(fragments):
            fragments = fragments[-limit:]

        if current_only:
            fragments = self._latest_step_slice(fragments)

        return fragments

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
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
    )
    def jump_to_node(self, ledger: Ledger, node_id: UUID) -> dict[str, Any]:
        """Teleport the ledger cursor to ``node_id`` for debugging purposes."""

        destination = ledger.graph.get(node_id)
        if destination is None:
            raise ValueError(f"Node {node_id} not found in graph")

        if not destination.has_tags("dirty"):
            destination.tags = set(destination.tags) | {"dirty"}

        frame = ledger.get_frame()
        frame.jump_to_node(destination, include_postreq=True)

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
        start_cursor_id = story_graph.initial_cursor_id
        if start_cursor_id is None:
            raise RuntimeError("Story graph did not define an initial cursor")

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

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
    )
    def drop_story(
        self,
        user: User,
        ledger: Ledger | None = None,
        *,
        archive: bool = False,
    ) -> dict[str, Any]:
        """Clear the user's active story and optionally schedule ledger deletion."""

        current_ledger_id = getattr(user, "current_ledger_id", None)
        if current_ledger_id is None:
            raise ValueError("User has no active story to drop")

        user.current_ledger_id = None

        result: dict[str, Any] = {
            "status": "dropped",
            "dropped_ledger_id": str(current_ledger_id),
            "archived": archive,
        }

        if not archive:
            result["_delete_ledger_id"] = str(current_ledger_id)

        return result

    @staticmethod
    def _latest_step_slice(fragments: list[BaseFragment]) -> list[BaseFragment]:
        """Return fragments from the most recent ``[step ...]`` marker onward."""

        step_indices: list[int] = []

        for idx, fragment in enumerate(fragments):
            content = getattr(fragment, "content", None)
            if isinstance(content, str) and content.startswith("[step "):
                step_indices.append(idx)

        if not step_indices:
            return fragments

        step_indices.append(len(fragments))
        slices = [
            fragments[start:end]
            for start, end in zip(step_indices[:-1], step_indices[1:])
        ]

        for fragment_slice in reversed(slices):
            if len(fragment_slice) > 1:
                return fragment_slice

        return slices[-1]
