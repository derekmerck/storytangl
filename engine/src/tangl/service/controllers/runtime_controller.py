"""Runtime controller endpoints for story/vm sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from tangl import core as tangl_core
from tangl.config import get_story_media_dir, get_sys_media_dir
from tangl.core import Selector
from tangl.journal.fragments import MediaFragment
from tangl.media import get_system_resource_manager
from tangl.media.media_resource import MediaInventory
from tangl.media.media_resource import MediaDep
from tangl.media.story_media import remove_story_media
from tangl.story.fabula import InitMode
from tangl.vm.runtime.ledger import Ledger

from ..api_endpoint import (
    AccessLevel,
    ApiEndpoint,
    HasApiEndpoints,
    MethodType,
    ResourceBinding,
    ResponseType,
)
from ..media import MediaRenderProfile, media_fragment_to_payload
from ..response import RuntimeEnvelope, RuntimeInfo
from ..user import User
from .world_controller import resolve_world

BaseFragment = tangl_core.BaseFragment


class RuntimeController(HasApiEndpoints):
    """Runtime endpoints for story sessions."""

    @staticmethod
    def _serialize_fragment(
        fragment: Any,
        *,
        render_profile: MediaRenderProfile | None = None,
        world_id: str | None = None,
        story_id: str | None = None,
        world_media_root: Path | None = None,
        story_media_root: Path | None = None,
        system_media_root: Path | None = None,
    ) -> dict[str, Any] | None:
        media_payload = media_fragment_to_payload(
            fragment,
            render_profile=render_profile,
            world_id=world_id,
            story_id=story_id,
            world_media_root=world_media_root,
            story_media_root=story_media_root,
            system_media_root=system_media_root,
        )
        if media_payload is not None:
            return media_payload
        if isinstance(fragment, MediaFragment):
            return None
        if hasattr(fragment, "model_dump"):
            return fragment.model_dump(mode="json")
        if hasattr(fragment, "unstructure"):
            data = fragment.unstructure()
            kind = data.get("kind")
            if isinstance(kind, type):
                data["kind"] = kind.__name__
            return data
        return {"fragment_type": "unknown", "content": str(fragment)}

    @staticmethod
    def _coerce_media_root(value: Any) -> Path | None:
        if value is None:
            return None
        if isinstance(value, Path):
            return value
        try:
            return Path(value)
        except TypeError:
            return None

    @classmethod
    def _resolve_media_roots(
        cls,
        *,
        ledger: Ledger | None = None,
        world_id: str | None = None,
        story_id: str | None = None,
    ) -> dict[str, Path | None]:
        graph = getattr(ledger, "graph", None)

        world_root = getattr(
            getattr(getattr(graph, "world", None), "resources", None),
            "resource_path",
            None,
        )
        if world_root is None and world_id is not None:
            try:
                world = resolve_world(world_id)
            except Exception:
                world = None
            world_root = getattr(getattr(world, "resources", None), "resource_path", None)

        story_root = getattr(getattr(graph, "story_resources", None), "resource_path", None)
        if story_root is None and story_id is not None:
            story_root = get_story_media_dir(story_id)

        return {
            "world": cls._coerce_media_root(world_root),
            "story": cls._coerce_media_root(story_root),
            "sys": cls._coerce_media_root(get_sys_media_dir()),
        }

    @staticmethod
    def _resolve_static_inventories(
        *,
        ledger: Ledger | None = None,
        world_id: str | None = None,
    ) -> tuple[MediaInventory, ...]:
        graph = getattr(ledger, "graph", None)
        inventories: list[MediaInventory] = []

        world_resources = getattr(getattr(graph, "world", None), "resources", None)
        if world_resources is None and world_id is not None:
            try:
                world = resolve_world(world_id)
            except Exception:
                world = None
            world_resources = getattr(world, "resources", None)

        for provider, scope in (
            (world_resources, "world"),
            (get_system_resource_manager(), "sys"),
        ):
            inventory = MediaInventory.from_provider(provider, scope=scope)
            if inventory is not None and inventory.identity not in {
                existing.identity for existing in inventories
            }:
                inventories.append(inventory)

        return tuple(inventories)

    @staticmethod
    def _resolve_world_id(
        ledger: Ledger,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if metadata and metadata.get("world_id") is not None:
            return str(metadata["world_id"])
        world = getattr(getattr(ledger, "graph", None), "world", None)
        for attr in ("label", "uid"):
            value = getattr(world, attr, None)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _collect_blocker_diagnostics(
        fragments: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        diagnostics: list[dict[str, Any]] = []
        for fragment in fragments:
            fragment_type = fragment.get("fragment_type")
            kind = fragment.get("kind")
            kind_value = kind.lower() if isinstance(kind, str) else None
            is_choice = fragment_type == "choice" or kind_value == "choice"
            if not is_choice:
                continue
            if bool(fragment.get("available", True)):
                continue
            diagnostics.append(
                {
                    "edge_id": fragment.get("edge_id"),
                    "unavailable_reason": fragment.get("unavailable_reason"),
                    "blockers": fragment.get("blockers"),
                }
            )
        return diagnostics

    @staticmethod
    def _to_compat_fragment(
        fragment: Any,
        *,
        render_profile: MediaRenderProfile | None = None,
        world_id: str | None = None,
        story_id: str | None = None,
        world_media_root: Path | None = None,
        story_media_root: Path | None = None,
        system_media_root: Path | None = None,
    ) -> BaseFragment | None:
        """Convert runtime journal records into legacy-compatible BaseFragment payloads."""
        if isinstance(fragment, MediaFragment):
            media_payload = media_fragment_to_payload(
                fragment,
                render_profile=render_profile,
                world_id=world_id,
                story_id=story_id,
                world_media_root=world_media_root,
                story_media_root=story_media_root,
                system_media_root=system_media_root,
            )
            if media_payload is not None:
                return BaseFragment(**media_payload)
            return None

        if isinstance(fragment, BaseFragment):
            return fragment

        if hasattr(fragment, "model_dump"):
            data = fragment.model_dump(mode="python")
        elif hasattr(fragment, "unstructure"):
            data = fragment.unstructure()
        elif isinstance(fragment, dict):
            data = dict(fragment)
        else:
            data = {"fragment_type": "content", "content": str(fragment)}

        fragment_type = str(data.get("fragment_type") or "content")
        if fragment_type == "choice":
            source_id = data.get("source_id") or data.get("edge_id")
            if source_id is not None:
                data["source_id"] = source_id
            if "label" not in data and isinstance(data.get("text"), str):
                data["label"] = data["text"]
            if "active" not in data and "available" in data:
                data["active"] = bool(data["available"])
        elif fragment_type == "content":
            if "content" not in data and isinstance(data.get("text"), str):
                data["content"] = data["text"]

        data["fragment_type"] = fragment_type
        return BaseFragment(**data)

    def _dereference_media(self, fragment: Any, world_id: str) -> dict[str, Any]:
        """Convert MediaRIT-backed fragments to API payloads."""
        story_id = getattr(fragment, "story_id", None) or world_id
        media_roots = self._resolve_media_roots(
            world_id=world_id,
            story_id=story_id,
        )
        render_profile = MediaRenderProfile(
            static_inventories=self._resolve_static_inventories(world_id=world_id),
        )
        payload = media_fragment_to_payload(
            fragment,
            render_profile=render_profile,
            world_id=world_id,
            story_id=story_id,
            world_media_root=media_roots["world"],
            story_media_root=media_roots["story"],
            system_media_root=media_roots["sys"],
        )
        if payload is None:
            raise TypeError(f"Expected media-compatible fragment, got {type(fragment)}")
        return payload

    @staticmethod
    def _collect_media_diagnostics(ledger: Ledger) -> list[dict[str, Any]]:
        cursor = getattr(ledger, "cursor", None)
        if cursor is None or not hasattr(cursor, "media"):
            return []

        graph = getattr(ledger, "graph", None)
        diagnostics: list[dict[str, Any]] = []
        for media_item in getattr(cursor, "media", []) or []:
            if not isinstance(media_item, dict):
                continue

            if media_item.get("source_kind") == "potential":
                diagnostics.append(
                    {
                        "reason": "unsupported_media_spec",
                        "scope": media_item.get("scope") or "story",
                        "fallback": media_item.get("fallback_text") or media_item.get("text"),
                    }
                )
                continue

            dependency_id = media_item.get("dependency_id")
            dependency = graph.get(dependency_id) if graph is not None and dependency_id is not None else None
            if isinstance(dependency, MediaDep):
                if dependency.provider is None:
                    diagnostics.append(
                        {
                            "reason": dependency.requirement.resolution_reason or "unresolved_media",
                            "scope": dependency.scope or media_item.get("scope") or "world",
                            "fallback": media_item.get("fallback_text") or media_item.get("text"),
                            "label": media_item.get("name") or media_item.get("label"),
                        }
                    )
                elif not dependency.render_ready:
                    status = getattr(dependency.provider, "status", None)
                    diagnostics.append(
                        {
                            "reason": (
                                f"media_{status.value}"
                                if status is not None and hasattr(status, "value")
                                else "media_pending"
                            ),
                            "scope": dependency.scope or media_item.get("scope") or "story",
                            "fallback": media_item.get("fallback_text") or media_item.get("text"),
                            "label": media_item.get("name") or media_item.get("label"),
                        }
                    )
        return diagnostics

    @staticmethod
    def _synthetic_journal_from_cursor(ledger: Ledger) -> list[BaseFragment]:
        """Fallback legacy journal view derived from the active cursor state."""
        cursor = getattr(ledger, "cursor", None)
        if cursor is None:
            return []

        fragments: list[BaseFragment] = []
        content = getattr(cursor, "content", None)
        if isinstance(content, str) and content.strip():
            fragments.append(
                BaseFragment(
                    fragment_type="content",
                    content=content.strip(),
                    source_id=getattr(cursor, "uid", None),
                    step=getattr(ledger, "step", 0),
                )
            )

        from tangl.story.episode import Action

        edges_out = getattr(cursor, "edges_out", None)
        choices = list(edges_out(Selector(has_kind=Action, trigger_phase=None))) if callable(edges_out) else []
        for edge in choices:
            text = (
                getattr(edge, "text", None)
                or getattr(edge, "label", None)
                or str(getattr(edge, "uid", "choice"))
            )
            fragments.append(
                BaseFragment(
                    fragment_type="choice",
                    content=text,
                    text=text,
                    label=text,
                    source_id=getattr(edge, "uid", None),
                    available=True,
                    active=True,
                    step=getattr(ledger, "step", 0),
                )
            )
        return fragments

    def _runtime_envelope(
        self,
        *,
        ledger: Ledger,
        fragments: list[Any],
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEnvelope:
        world_id = self._resolve_world_id(ledger, metadata=metadata)
        story_id = str((metadata or {}).get("ledger_id") or ledger.uid)
        media_roots = self._resolve_media_roots(
            ledger=ledger,
            world_id=world_id,
            story_id=story_id,
        )
        render_profile = MediaRenderProfile(
            static_inventories=self._resolve_static_inventories(
                ledger=ledger,
                world_id=world_id,
            ),
        )
        serialized_fragments = [
            payload
            for fragment in fragments
            if (
                payload := self._serialize_fragment(
                    fragment,
                    render_profile=render_profile,
                    world_id=world_id,
                    story_id=story_id,
                    world_media_root=media_roots["world"],
                    story_media_root=media_roots["story"],
                    system_media_root=media_roots["sys"],
                )
            )
            is not None
        ]
        merged_metadata = dict(metadata or {})
        if world_id is not None:
            merged_metadata.setdefault("world_id", world_id)
        merged_metadata.setdefault("ledger_id", str(ledger.uid))
        blockers = self._collect_blocker_diagnostics(serialized_fragments)
        if blockers:
            merged_metadata["blockers"] = blockers
        media_diagnostics = self._collect_media_diagnostics(ledger)
        if media_diagnostics:
            merged_metadata["media_diagnostics"] = media_diagnostics

        return RuntimeEnvelope(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            fragments=serialized_fragments,
            last_redirect=ledger.last_redirect,
            redirect_trace=ledger.redirect_trace,
            metadata=merged_metadata,
        )

    @staticmethod
    def _prime_initial_update(ledger: Ledger) -> None:
        """Seed initial JOURNAL output so legacy surfaces can render entry content."""
        if ledger.get_journal():
            return

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)

        prev_id = ledger.cursor_history[-1] if ledger.cursor_history else None
        for node_id in frame.cursor_trace:
            if prev_id is not None and node_id == prev_id:
                ledger.reentrant_steps += 1
            prev_id = node_id

        ledger.cursor_steps += frame.cursor_steps
        ledger.cursor_id = frame.cursor.uid
        ledger.cursor_history.extend(frame.cursor_trace)
        ledger.call_stack_ids = [edge.uid for edge in frame.return_stack]
        ledger.last_redirect = frame.last_redirect
        ledger.redirect_trace = list(frame.redirect_trace)
        ledger.save_snapshot(cadence=ledger.checkpoint_cadence)

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        """Create a story graph and bootstrap a runtime ledger for ``user``."""
        import tangl.story  # noqa: F401  # ensure story-level hooks are registered

        world = kwargs.pop("world", None)
        if world is None:
            world = resolve_world(world_id)

        story_label = kwargs.get("story_label") or f"story_{user.uid}"
        mode_raw = kwargs.get("init_mode") or kwargs.get("mode") or InitMode.EAGER.value
        if isinstance(mode_raw, str):
            mode = InitMode(mode_raw.lower())
        else:
            mode = InitMode(mode_raw)

        freeze_shape = bool(kwargs.get("freeze_shape", False))
        worker_dispatcher = kwargs.pop("worker_dispatcher", None)
        init_result = world.create_story(
            story_label,
            init_mode=mode,
            freeze_shape=freeze_shape,
        )
        story_graph = init_result.graph
        if story_graph.initial_cursor_id is None:
            raise RuntimeError("Story graph did not define an initial cursor")

        ledger = Ledger.from_graph(
            graph=story_graph,
            entry_id=story_graph.initial_cursor_id,
            uid=story_graph.story_id or story_graph.uid,
        )
        ledger.user = user
        ledger.user_id = user.uid
        ledger.worker_dispatcher = worker_dispatcher
        self._prime_initial_update(ledger)
        user.current_ledger_id = ledger.uid  # type: ignore[attr-defined]

        cursor_node = story_graph.get(ledger.cursor_id)
        cursor_label = cursor_node.label if cursor_node is not None else "unknown"
        envelope = self._runtime_envelope(
            ledger=ledger,
            fragments=ledger.get_journal(),
            metadata={"world_id": world_id, "ledger_id": str(ledger.uid)},
        )

        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story created",
            ledger_id=str(ledger.uid),
            world_id=world_id,
            title=story_graph.label,
            cursor_label=cursor_label,
            ledger=ledger,
            envelope=envelope.model_dump(mode="json"),
            init_report={
                "mode": init_result.report.mode.value,
                "materialized_counts": init_result.report.materialized_counts,
                "prelinked_counts": init_result.report.prelinked_counts,
                "unresolved_hard": len(init_result.report.unresolved_hard),
                "unresolved_soft": len(init_result.report.unresolved_soft),
                "warnings": init_result.report.warnings,
            },
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def resolve_choice(
        self,
        ledger: Ledger,
        choice_id: UUID,
        choice_payload: Any = None,
    ) -> RuntimeInfo:
        """Resolve one choice edge and return the latest runtime envelope."""
        before_step = ledger.step
        ledger.resolve_choice(choice_id, choice_payload=choice_payload)
        fragments = ledger.get_journal(since_step=max(before_step + 1, 0))
        envelope = self._runtime_envelope(ledger=ledger, fragments=fragments)
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story choice resolved",
            choice_id=str(choice_id),
            envelope=envelope.model_dump(mode="json"),
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_update(
        self,
        ledger: Ledger,
        *,
        since_step: int | None = None,
        limit: int = 0,
    ) -> RuntimeInfo:
        """Return ordered runtime fragments in an envelope."""
        effective_since = 0 if since_step is None else since_step
        fragments = ledger.get_journal(since_step=effective_since, limit=limit)
        envelope = self._runtime_envelope(ledger=ledger, fragments=fragments)
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story update",
            envelope=envelope.model_dump(mode="json"),
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_journal_entries(
        self,
        ledger: Ledger,
        limit: int = 0,
        *,
        current_only: bool = True,
        marker: str = "latest",
        marker_type: str = "entry",
        start_marker: str | None = None,
        end_marker: str | None = None,
    ) -> list[BaseFragment]:
        """Legacy endpoint shape that returns the latest runtime fragments as BaseFragment items."""
        _ = (marker, marker_type, start_marker, end_marker)
        if current_only:
            fragments = list(ledger.get_journal())
            from tangl.vm.replay import StepRecord

            choice_steps = [
                record.step
                for record in Selector(has_kind=StepRecord).filter(ledger.output_stream)
                if bool(getattr(record, "was_choice", False))
            ]
            if choice_steps:
                latest_choice_step = max(choice_steps)
                fragments = [
                    fragment
                    for fragment in fragments
                    if getattr(fragment, "step", -1) >= latest_choice_step
                    or getattr(fragment, "step", -1) < 0
                ]
            if limit > 0 and len(fragments) > limit:
                fragments = fragments[-limit:]
        else:
            fragments = list(ledger.get_journal(limit=limit))
        if not fragments:
            return self._synthetic_journal_from_cursor(ledger)
        world_id = self._resolve_world_id(ledger)
        story_id = str(ledger.uid)
        media_roots = self._resolve_media_roots(
            ledger=ledger,
            world_id=world_id,
            story_id=story_id,
        )
        render_profile = MediaRenderProfile(
            static_inventories=self._resolve_static_inventories(
                ledger=ledger,
                world_id=world_id,
            ),
        )
        return [
            compat
            for fragment in fragments
            if (
                compat := self._to_compat_fragment(
                    fragment,
                    render_profile=render_profile,
                    world_id=world_id,
                    story_id=story_id,
                    world_media_root=media_roots["world"],
                    story_media_root=media_roots["story"],
                    system_media_root=media_roots["sys"],
                )
            )
            is not None
        ]

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_info(self, ledger: Ledger) -> RuntimeInfo:
        """Return session summary with no legacy marker assumptions."""
        graph = getattr(ledger, "graph", None)
        cursor_node = (
            graph.get(ledger.cursor_id)
            if graph is not None and ledger.cursor_id is not None
            else None
        )
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story info",
            cursor_label=cursor_node.label if cursor_node is not None else None,
            turn=ledger.turn,
            choice_steps=ledger.choice_steps,
            cursor_steps=ledger.cursor_steps,
            journal_size=len(ledger.get_journal()),
            last_redirect=ledger.last_redirect,
            redirect_trace=ledger.redirect_trace,
        )

    @ApiEndpoint.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
    )
    def drop_story(
        self,
        user: User,
        ledger: Ledger | None = None,
        *,
        archive: bool = False,
    ) -> RuntimeInfo:
        """Clear the active story and optionally delete persisted ledger."""
        current_ledger_id = getattr(user, "current_ledger_id", None)
        if current_ledger_id is None:
            raise ValueError("User has no active story to drop")

        user.current_ledger_id = None
        details: dict[str, Any] = {
            "dropped_ledger_id": str(current_ledger_id),
            "archived": archive,
        }
        if not archive:
            details["story_media_deleted"] = remove_story_media(current_ledger_id)
            details["_delete_ledger_id"] = str(current_ledger_id)

        return RuntimeInfo.ok(
            cursor_id=getattr(ledger, "cursor_id", None),
            step=getattr(ledger, "step", None),
            message="Story dropped",
            **details,
        )


__all__ = ["RuntimeController"]
