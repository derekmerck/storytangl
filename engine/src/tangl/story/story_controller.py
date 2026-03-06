"""Service38 runtime controller for story38/vm38 endpoints only."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from tangl import core as tangl_core
from tangl.core import Selector
from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint38,
    HasApiEndpoints,
    MethodType,
    ResourceBinding,
    ResponseType,
)
from tangl.service.response import RuntimeEnvelope38, RuntimeInfo
from tangl.service.user import User
from tangl.story.fabula import InitMode
from tangl.story.fabula.world_controller import resolve_world38
from tangl.vm.runtime.ledger import Ledger as Ledger38

BaseFragment = tangl_core.BaseFragment


class RuntimeController(HasApiEndpoints):
    """Runtime endpoints for story38 sessions."""

    @staticmethod
    def _serialize_vm38_fragment(fragment: Any) -> dict[str, Any]:
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
    def _to_compat_fragment(fragment: Any) -> BaseFragment:
        """Convert vm38 journal records into legacy-compatible BaseFragment payloads."""
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
        """Legacy compatibility helper: convert MediaRIT-backed fragments to API payloads."""
        from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT

        rit = getattr(fragment, "content", None)
        if not isinstance(rit, MediaRIT):
            raise TypeError(f"Expected MediaRIT in MediaFragment.content, got {type(rit)}")

        filename: str | None = None
        path_value = getattr(rit, "path", None)
        if isinstance(path_value, Path):
            filename = path_value.name
        elif getattr(rit, "label", None):
            filename = rit.label

        if not filename:
            raise ValueError(f"Cannot determine filename for MediaRIT {rit!r}")

        scope = getattr(fragment, "scope", None) or "world"
        if scope == "sys":
            url_prefix = "/media/sys"
        else:
            url_prefix = f"/media/world/{world_id}"

        source_id = getattr(fragment, "source_id", None)
        content_type = getattr(rit, "data_type", None)

        return {
            "fragment_type": "media",
            "media_role": getattr(fragment, "media_role", None),
            "url": f"{url_prefix}/{filename}",
            "media_type": content_type.value if content_type is not None else None,
            "text": getattr(fragment, "text", None),
            "source_id": str(source_id) if source_id is not None else None,
            "scope": scope,
        }

    @staticmethod
    def _synthetic_journal_from_cursor(ledger: Ledger38) -> list[BaseFragment]:
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

    def _runtime38_envelope(
        self,
        *,
        ledger: Ledger38,
        fragments: list[Any],
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEnvelope38:
        serialized_fragments = [
            self._serialize_vm38_fragment(fragment) for fragment in fragments
        ]
        merged_metadata = dict(metadata or {})
        blockers = self._collect_blocker_diagnostics(serialized_fragments)
        if blockers:
            merged_metadata["blockers"] = blockers

        return RuntimeEnvelope38(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            fragments=serialized_fragments,
            last_redirect=ledger.last_redirect,
            redirect_trace=ledger.redirect_trace,
            metadata=merged_metadata,
        )

    @staticmethod
    def _prime_initial_update(ledger: Ledger38) -> None:
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

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def create_story38(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        """Create a story38 graph and bootstrap a vm38 ledger for ``user``."""
        import tangl.story  # noqa: F401  # ensure story-level vm38 hooks are registered

        world = kwargs.pop("world", None)
        if world is None:
            world = resolve_world38(world_id)

        story_label = kwargs.get("story_label") or f"story_{user.uid}"
        mode_raw = kwargs.get("init_mode") or kwargs.get("mode") or InitMode.EAGER.value
        if isinstance(mode_raw, str):
            mode = InitMode(mode_raw.lower())
        else:
            mode = InitMode(mode_raw)

        init_result = world.create_story(story_label, init_mode=mode)
        story_graph = init_result.graph
        if story_graph.initial_cursor_id is None:
            raise RuntimeError("Story38 graph did not define an initial cursor")

        ledger = Ledger38.from_graph(graph=story_graph, entry_id=story_graph.initial_cursor_id)
        ledger.user = user
        ledger.user_id = user.uid
        self._prime_initial_update(ledger)
        user.current_ledger_id = ledger.uid  # type: ignore[attr-defined]

        cursor_node = story_graph.get(ledger.cursor_id)
        cursor_label = cursor_node.label if cursor_node is not None else "unknown"
        envelope = self._runtime38_envelope(
            ledger=ledger,
            fragments=ledger.get_journal(),
            metadata={"world_id": world_id, "ledger_id": str(ledger.uid)},
        )

        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story38 created",
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

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def create_story(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        """Legacy alias for ``create_story38`` using story38/vm38 mechanics."""
        return self.create_story38(user=user, world_id=world_id, **kwargs)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def resolve_choice38(
        self,
        ledger: Ledger38,
        choice_id: UUID,
        choice_payload: Any = None,
    ) -> RuntimeInfo:
        """Resolve one vm38 choice edge and return the latest runtime envelope."""
        before_step = ledger.step
        ledger.resolve_choice(choice_id, choice_payload=choice_payload)
        fragments = ledger.get_journal(since_step=max(before_step + 1, 0))
        envelope = self._runtime38_envelope(ledger=ledger, fragments=fragments)
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story38 choice resolved",
            choice_id=str(choice_id),
            envelope=envelope.model_dump(mode="json"),
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.UPDATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def resolve_choice(
        self,
        ledger: Ledger38,
        choice_id: UUID,
        choice_payload: Any = None,
    ) -> RuntimeInfo:
        """Legacy alias for ``resolve_choice38``."""
        return self.resolve_choice38(
            ledger=ledger,
            choice_id=choice_id,
            choice_payload=choice_payload,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_update38(
        self,
        ledger: Ledger38,
        *,
        since_step: int | None = None,
        limit: int = 0,
    ) -> RuntimeInfo:
        """Return vm38 ordered fragments in an envelope."""
        effective_since = 0 if since_step is None else since_step
        fragments = ledger.get_journal(since_step=effective_since, limit=limit)
        envelope = self._runtime38_envelope(ledger=ledger, fragments=fragments)
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story38 update",
            envelope=envelope.model_dump(mode="json"),
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.CONTENT,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_journal_entries(
        self,
        ledger: Ledger38,
        limit: int = 0,
        *,
        current_only: bool = True,
        marker: str = "latest",
        marker_type: str = "entry",
        start_marker: str | None = None,
        end_marker: str | None = None,
    ) -> list[BaseFragment]:
        """Legacy endpoint shape that returns the latest vm38 fragments as BaseFragment items."""
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
        return [self._to_compat_fragment(fragment) for fragment in fragments]

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_info38(self, ledger: Ledger38) -> RuntimeInfo:
        """Return vm38 session summary with no legacy marker assumptions."""
        cursor_node = ledger.graph.get(ledger.cursor_id)
        return RuntimeInfo.ok(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            message="Story38 info",
            cursor_label=cursor_node.label if cursor_node is not None else None,
            turn=ledger.turn,
            choice_steps=ledger.choice_steps,
            cursor_steps=ledger.cursor_steps,
            journal_size=len(ledger.get_journal()),
            last_redirect=ledger.last_redirect,
            redirect_trace=ledger.redirect_trace,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.READ,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.LEDGER,),
    )
    def get_story_info(self, ledger: Ledger38) -> RuntimeInfo:
        """Legacy alias for ``get_story_info38``."""
        return self.get_story_info38(ledger=ledger)

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
    )
    def drop_story38(
        self,
        user: User,
        ledger: Ledger38 | None = None,
        *,
        archive: bool = False,
    ) -> RuntimeInfo:
        """Clear the active vm38 story and optionally delete persisted ledger."""
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
            message="Story38 dropped",
            **details,
        )

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.DELETE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER, ResourceBinding.LEDGER),
    )
    def drop_story(
        self,
        user: User,
        ledger: Ledger38 | None = None,
        *,
        archive: bool = False,
    ) -> RuntimeInfo:
        """Legacy alias for ``drop_story38``."""
        return self.drop_story38(
            user=user,
            ledger=ledger,
            archive=archive,
        )


__all__ = ["RuntimeController"]
