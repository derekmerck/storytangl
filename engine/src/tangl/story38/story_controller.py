"""Service38 runtime controller for story38/vm38 endpoints only."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from tangl.service.api_endpoint import HasApiEndpoints
from tangl.service.response import RuntimeEnvelope38
from tangl.service.user.user import User
from tangl.service38.api_endpoint import (
    AccessLevel,
    ApiEndpoint38,
    MethodType,
    ResourceBinding,
    ResponseType,
)
from tangl.service38.response import RuntimeInfo
from tangl.story38.fabula import InitMode
from tangl.story38.fabula.world_controller import resolve_world38
from tangl.vm38.runtime.ledger import Ledger as Ledger38


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

    @ApiEndpoint38.annotate(
        access_level=AccessLevel.PUBLIC,
        method_type=MethodType.CREATE,
        response_type=ResponseType.RUNTIME,
        binds=(ResourceBinding.USER,),
    )
    def create_story38(self, user: User, world_id: str, **kwargs: Any) -> RuntimeInfo:
        """Create a story38 graph and bootstrap a vm38 ledger for ``user``."""
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


__all__ = ["RuntimeController"]
