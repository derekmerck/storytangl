# tangl/service/controllers/runtime_controller.py
"""Runtime controller bridging orchestrator calls to the VM layer."""

from __future__ import annotations
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from tangl.core import BaseFragment, StreamRegistry
from tangl.journal.content import ContentFragment
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)
from tangl.vm.frame import ChoiceEdge, Frame, ResolutionPhase
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
        if limit == 0:
            return []
        if limit >= len(fragments):
            return fragments
        return fragments[-limit:]

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.CONTENT,
    )
    def resolve_choice(self, frame: Frame, choice_id: UUID) -> dict[str, Any]:
        """Resolve a player choice and return journal fragments for the step."""

        choice = frame.graph.get(choice_id)
        if not isinstance(choice, ChoiceEdge):
            raise ValueError(f"Choice {choice_id} not found")

        baseline_seq = frame.records.max_seq
        frame.resolve_choice(choice)
        fragments = list(
            frame.records.iter_channel(
                "fragment",
                predicate=lambda record: record.seq > baseline_seq,
            )
        )
        return {
            "fragments": fragments,
            "cursor_id": frame.cursor_id,
            "step": frame.step,
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
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.CONTENT,
    )
    def jump_to_node(self, frame: Frame, node_id: UUID) -> dict[str, Any]:
        """Set the frame cursor to ``node_id`` and journal the new context."""

        node = frame.graph.get(node_id)
        if node is None:
            raise ValueError(f"Node {node_id} not found")

        frame.cursor_id = node.uid
        frame._invalidate_context()  # rebuild context for new cursor
        frame.run_phase(ResolutionPhase.VALIDATE)
        fragments = frame.run_phase(ResolutionPhase.JOURNAL)
        if isinstance(fragments, Iterable):
            fragments_list = list(fragments)
        else:
            fragments_list = [ContentFragment(content=str(fragments))]
        return {
            "fragments": fragments_list,
            "cursor_id": frame.cursor_id,
        }

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> dict[str, Any]:
        """Create a fully-materialized story ledger for ``user``."""

        from tangl.story.story_domain.world import World

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

        try:
            user.current_ledger_id = ledger.uid  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            user.current_story_id = ledger.uid
        else:
            user.current_story_id = ledger.uid

        start_node = story_graph.get(start_cursor_id)
        cursor_label = start_node.label if start_node is not None else "unknown"

        return {
            "ledger_id": str(ledger.uid),
            "world_id": world_id,
            "title": story_graph.label,
            "cursor_id": str(start_cursor_id),
            "cursor_label": cursor_label,
            "ledger": ledger,
        }
