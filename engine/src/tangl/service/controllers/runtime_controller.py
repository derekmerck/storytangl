# tangl/service/controllers/runtime_controller.py
"""Runtime controller bridging orchestrator calls to the VM layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pathlib import Path

from tangl.core import BaseFragment, StreamRegistry
from tangl.journal.media import MediaFragment
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResponseType,
)
from tangl.service.exceptions import InvalidOperationError
from tangl.service.response import ChoiceInfo, RuntimeInfo, StoryInfo
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
        self,
        ledger: Ledger,
        limit: int = 0,
        *,
        current_only: bool = True,
        marker: str | None = None,
        marker_type: str = "entry",
        start_marker: str | None = None,
        end_marker: str | None = None,
    ) -> list[BaseFragment]:
        """Return journal fragments from a ledger.

        Parameters
        ----------
        ledger:
            Ledger to read from.
        limit:
            Maximum number of fragments to return. ``0`` means no limit. Limits are
            ignored when a marker-based slice is requested so a full step is
            returned.
        current_only:
            If true (the default), return only fragments for the latest journal
            marker/step.
        marker:
            Return the journal section beginning at ``marker`` (inclusive) and
            ending at the next marker of the same type.
        marker_type:
            Marker namespace to use. Defaults to ``"entry"``, which marks each resolved player input; a single entry may cover multiple per-step "journal" markers emitted by :class:`Frame` during auto-follows.
        start_marker:
            Inclusive starting marker name for a marker range.
        end_marker:
            Optional exclusive ending marker. When provided, the slice ends at the
            marker immediately following ``end_marker``.
        """

        marker = marker or "latest"
        marker_type = marker_type or "entry"

        if limit < 0:
            raise ValueError("limit must be non-negative")

        marker_channels = ledger.records.markers.get(marker_type, {})

        def _slice_between(start: str, stop: str | None) -> list[BaseFragment]:
            start_seq = marker_channels[start]
            end_seq = (
                marker_channels[stop]
                if stop is not None
                else ledger.records._next_marker_seq(start_seq, marker_type)
            )
            if end_seq <= start_seq:
                return []
            return list(
                ledger.records.get_slice(
                    start_seq=start_seq,
                    end_seq=end_seq,
                    has_channel="fragment",
                )
            )

        fragments: list[BaseFragment]

        # --- explicit marker-based access ---
        if end_marker is None:  # Not doing a slice
            try:
                fragments = list(
                    ledger.records.get_section(
                        marker,
                        marker_type=marker_type,
                        has_channel="fragment",
                    )
                )
            except KeyError:
                # Unknown marker: behave like the old implementation and return empty.
                return []

        # --- explicit range access ---
        elif start_marker is not None or end_marker is not None:
            start_name = start_marker or self._latest_marker_name(marker_channels)
            if end_marker is not None and end_marker not in marker_channels:
                return []
            if start_name is None or start_name not in marker_channels:
                return []
            fragments = _slice_between(start_name, end_marker)

        # --- default: latest step ---
        elif current_only:
            try:
                # Prefer the StreamRegistry's notion of the latest marker.
                fragments = list(
                    ledger.records.get_section(
                        "latest",
                        marker_type=marker_type,
                        has_channel="fragment",
                    )
                )
            except KeyError:
                # Fallback to legacy behavior that scans for "[step ...]" markers.
                fragments = list(ledger.records.iter_channel("fragment"))
                fragments = self._latest_step_slice(fragments)

        # --- full journal (optionally limited) ---
        else:
            fragments = list(ledger.records.iter_channel("fragment"))

        if limit > 0 and not (marker or start_marker or end_marker or current_only):
            fragments = fragments[-limit:]

        return fragments

    def _world_id_for_ledger(self, ledger: Ledger) -> str:
        """Return the stable world identifier for URL construction."""

        world_obj = getattr(ledger, "world", None)
        if world_obj is None:
            graph = getattr(ledger, "graph", None)
            world_obj = getattr(graph, "world", graph)

        if world_obj is None:
            return "unknown"

        return getattr(world_obj, "uid", None) or getattr(world_obj, "label", "unknown")

    def _dereference_media(self, fragment: MediaFragment, world_id: str) -> dict:
        """Convert a :class:`MediaFragment` containing a :class:`MediaRIT` into a JSON-ready mapping."""

        rit = fragment.content
        if not isinstance(rit, MediaRIT):
            raise TypeError(
                f"Expected MediaRIT in MediaFragment.content, got {type(rit)}"
            )

        filename: str | None = None
        path_value = getattr(rit, "path", None)
        if isinstance(path_value, Path):
            filename = path_value.name
        elif rit.label:
            filename = rit.label

        if not filename:
            raise ValueError(f"Cannot determine filename for MediaRIT {rit!r}")

        scope = getattr(fragment, "scope", None) or "world"
        if scope == "sys":
            url_prefix = "/media/sys"
        else:
            url_prefix = f"/media/world/{world_id}"

        url = f"{url_prefix}/{filename}"

        return {
            "fragment_type": "media",
            "media_role": fragment.media_role,
            "url": url,
            "media_type": rit.data_type.value if rit.data_type else None,
            "text": fragment.text,
            "source_id": str(fragment.source_id),
            "scope": scope,
        }

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.RUNTIME,
    )
    def get_story_update(self, *, ledger: Ledger, frame: Frame, **_: Any) -> RuntimeInfo:
        """Return the current story update, dereferencing media fragments to URLs."""

        world_id = self._world_id_for_ledger(ledger)
        fragments = self.get_journal_entries(
            ledger,
            current_only=True,
            marker_type="entry",
        )

        # # todo: we don't actually want to unstructure here, much less rely on model_dump
        output_fragments: list[dict] = []
        for fragment in fragments:
            if isinstance(fragment, MediaFragment) and fragment.content_format == "rit":
                output_fragments.append(self._dereference_media(fragment, world_id))
                continue
            if hasattr(fragment, "model_dump"):
                output_fragments.append(fragment.model_dump())
            else:
                output_fragments.append({"content": str(fragment)})

        return RuntimeInfo.ok(
            cursor_id=frame.cursor_id,
            step=ledger.step,
            message="Story update",
            fragments=output_fragments,
        )

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
    ) -> RuntimeInfo:
        """Resolve a player choice and update the ledger cursor."""

        choice = frame.graph.get(choice_id)
        if not isinstance(choice, ChoiceEdge):
            raise InvalidOperationError(f"Choice {choice_id} not found")

        frame.resolve_choice(choice)

        ledger.cursor_id = frame.cursor_id
        ledger.step = frame.step
        ledger.record_stack_snapshot()

        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Choice resolved",
            choice_label=choice.label,
            choice_id=str(choice_id),
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        response_type=ResponseType.INFO,
    )
    def get_story_info(self, ledger: Ledger) -> StoryInfo:
        """Summarize the current ledger state for diagnostics."""

        cursor_node = ledger.graph.get(ledger.cursor_id)

        return StoryInfo(
            title=ledger.graph.label,
            step=ledger.step,
            cursor_id=ledger.cursor_id,
            journal_size=sum(1 for _ in ledger.records.iter_channel("fragment")),
            cursor_label=cursor_node.label if cursor_node else None,
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.RESTRICTED,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
    )
    def jump_to_node(self, ledger: Ledger, node_id: UUID) -> RuntimeInfo:
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
        ledger.record_stack_snapshot()

        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Jumped",
            dirty=True,
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
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

        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story created",
            ledger_id=str(ledger.uid),
            world_id=world_id,
            title=story_graph.label,
            cursor_label=cursor_label,
            ledger=ledger,
        )

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
    ) -> RuntimeInfo:
        """Clear the user's active story and optionally schedule ledger deletion."""

        current_ledger_id = getattr(user, "current_ledger_id", None)
        if current_ledger_id is None:
            raise ValueError("User has no active story to drop")

        user.current_ledger_id = None

        details: dict[str, Any] = {
            "dropped_ledger_id": str(current_ledger_id),
            "archived": archive,
        }

        if not archive:
            details["_delete_ledger_id"] = str(current_ledger_id)

        return RuntimeInfo.ok(
            cursor_id=getattr(ledger, "cursor_id", None),
            step=getattr(ledger, "step", None),
            message="Story dropped",
            **details,
        )

    # @staticmethod
    # def _latest_step_slice(fragments: list[BaseFragment]) -> list[BaseFragment]:
    #     """Return fragments from the most recent ``[step ...]`` marker onward."""
    #
    #     step_indices: list[int] = []
    #
    #     for idx, fragment in enumerate(fragments):
    #         content = getattr(fragment, "content", None)
    #         if isinstance(content, str) and content.startswith("[step "):
    #             step_indices.append(idx)
    #
    #     if not step_indices:
    #         return fragments
    #
    #     step_indices.append(len(fragments))
    #     slices = [
    #         fragments[start:end]
    #         for start, end in zip(step_indices[:-1], step_indices[1:])
    #     ]
    #
    #     for fragment_slice in reversed(slices):
    #         if len(fragment_slice) > 1:
    #             return fragment_slice
    #
    #     return slices[-1]
    #
    # @staticmethod
    # def _latest_marker_name(markers: dict[str, int]) -> str | None:
    #     if not markers:
    #         return None
    #     latest_seq = max(markers.values())
    #     for name, seq in markers.items():
    #         if seq == latest_seq:
    #             return name
    #     return None
