from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category

from tangl.service.response import (
    CommandEdgeQuery,
    DirectEdgeRequest,
    FindEdgeRequest,
    ProjectedState,
    RuntimeEnvelope,
)


if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@dataclass(frozen=True)
class _CachedChoice:
    edge_id: UUID
    label: str
    available: bool
    unavailable_reason: str | None
    accepts: dict[str, Any] | None


@with_default_category("Story")
class StoryController(CommandSet):
    """Story commands backed by :class:`tangl.service.ServiceManager`."""

    _cmd: StoryTanglCLI

    def __init__(self) -> None:
        super().__init__()
        self._current_story_update: list[dict[str, Any]] = []
        self._current_choices: list[_CachedChoice] = []
        self._current_ux_events: list[dict[str, Any]] = []
        self._current_metadata: dict[str, Any] = {}
        self._current_cursor_id: str | None = None
        self._current_step: int | None = None

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _require_story_context(self) -> bool:
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user. Create or select a user first.")
            return False
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger. Set a ledger with `user set_ledger <uuid>`.")
            return False
        return True

    def _render_current_story_update(self) -> None:
        self._cmd.emit_terminal(
            self._cmd.terminal_renderer.story_update(
                fragments=self._current_story_update,
                choices=self._current_choices,
                ux_events=self._current_ux_events,
                metadata=self._current_metadata,
            )
        )

    def _load_choices_from_fragments(self) -> list[_CachedChoice]:
        """Extract actionable choices from the canonical fragment DTO stream."""

        choices: list[_CachedChoice] = []
        for index, fragment in enumerate(self._current_story_update):
            if fragment.get("fragment_type") != "choice":
                continue

            edge_id = fragment.get("edge_id")
            if edge_id is None:
                raise ValueError(
                    f"Choice fragment at index {index} is missing required edge_id: {fragment!r}"
                )

            accepts = fragment.get("accepts")
            choices.append(
                _CachedChoice(
                    edge_id=UUID(str(edge_id)),
                    label=str(fragment.get("text") or "choice"),
                    available=bool(fragment.get("available", True)),
                    unavailable_reason=fragment.get("unavailable_reason"),
                    accepts=dict(accepts) if isinstance(accepts, dict) else None,
                )
            )

        return choices

    def _call_service(self, method_name: str, **params: Any) -> Any:
        return self._cmd.call_service(method_name, **params)

    def _apply_runtime_envelope(self, envelope: RuntimeEnvelope) -> None:
        payload = envelope.to_dto()
        cursor_id = payload.get("cursor_id")
        step = payload.get("step")
        fragments = payload["fragments"]
        ux_events = payload.get("ux_events", [])
        guidance_only = (
            not fragments
            and bool(ux_events)
            and bool(self._current_story_update)
            and cursor_id == self._current_cursor_id
            and step == self._current_step
        )

        self._current_metadata = payload.get("metadata", {})
        self._current_ux_events = ux_events
        self._current_cursor_id = cursor_id
        self._current_step = step
        ledger_id_value = self._current_metadata.get("ledger_id")
        if ledger_id_value is not None:
            self._cmd.set_ledger(UUID(str(ledger_id_value)))
        if not guidance_only:
            self._current_story_update = fragments
            self._current_choices = self._load_choices_from_fragments()

    @staticmethod
    def _choice_payload(
        choice: _CachedChoice,
        values: list[str],
        raw_payload: str | None,
    ) -> dict[str, Any] | None:
        """Build one documented choice payload from CLI input."""

        if raw_payload is not None:
            if values:
                raise ValueError("Use positional values or --payload, not both.")
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON payload: {exc.msg}") from exc
            if not isinstance(payload, dict):
                raise ValueError("--payload must decode to a JSON object.")
            return payload

        accepts = choice.accepts
        kind = accepts.get("kind", "pick") if accepts is not None else "pick"
        if kind == "pick":
            if values:
                raise ValueError("This choice does not accept an input value.")
            return {}

        if kind == "text":
            text = " ".join(values).strip()
            required = bool(accepts.get("required", True))
            if required and not text:
                raise ValueError("This choice requires text input.")
            return {"text": text}

        if kind == "quantity":
            if len(values) != 1:
                raise ValueError("This choice requires one integer quantity.")
            try:
                quantity = int(values[0])
            except ValueError as exc:
                raise ValueError("Quantity must be an integer.") from exc

            minimum = accepts.get("min")
            maximum = accepts.get("max")
            step = accepts.get("step", 1)
            if isinstance(minimum, int) and quantity < minimum:
                raise ValueError(f"Quantity must be at least {minimum}.")
            if isinstance(maximum, int) and quantity > maximum:
                raise ValueError(f"Quantity must be at most {maximum}.")
            if isinstance(step, int) and step > 1:
                origin = minimum if isinstance(minimum, int) else 0
                if (quantity - origin) % step:
                    raise ValueError(f"Quantity must advance in steps of {step}.")
            return {"quantity": quantity}

        if kind == "pieces":
            minimum = accepts.get("min", 1)
            maximum = accepts.get("max", 1)
            if isinstance(minimum, int) and len(values) < minimum:
                raise ValueError(f"Select at least {minimum} piece(s).")
            if isinstance(maximum, int) and len(values) > maximum:
                raise ValueError(f"Select at most {maximum} piece(s).")
            return {"piece_ids": values}

        raise ValueError(
            f"{kind} input requires an explicit JSON object via --payload."
        )

    # ------------------------------------------------------------------
    # commands
    # ------------------------------------------------------------------
    create_story_parser = argparse.ArgumentParser()
    create_story_parser.add_argument("world_id", help="World to instantiate")
    create_story_parser.add_argument("--label", help="Story label", default=None)

    @with_argparser(create_story_parser)
    def do_create_story(self, args: argparse.Namespace) -> None:
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user. Create a user first with 'create_user'.")
            return

        kwargs = {"world_id": args.world_id}
        if args.label:
            kwargs["story_label"] = args.label

        result = cast(RuntimeEnvelope, self._call_service("create_story", **kwargs))
        self._apply_runtime_envelope(result)

        title = args.world_id
        ledger_id = self._cmd.ledger_id

        self._cmd.emit_terminal(
            self._cmd.terminal_renderer.story_created(
                title=title,
                ledger_id=ledger_id,
                fragments=self._current_story_update,
                choices=self._current_choices,
                ux_events=self._current_ux_events,
                metadata=self._current_metadata,
            )
        )

    def do_story(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        result = cast(RuntimeEnvelope, self._call_service("get_story_update", limit=10))
        self._apply_runtime_envelope(result)
        self._render_current_story_update()

    choose_parser = argparse.ArgumentParser()
    choose_parser.add_argument("action", type=int, help="Choice number to execute")
    choose_parser.add_argument(
        "values",
        nargs="*",
        help="Text, quantity, or piece identifiers required by the choice",
    )
    choose_parser.add_argument(
        "--payload",
        help="Explicit JSON object for place, compose, or extension choices",
    )

    @with_argparser(choose_parser)
    def do_do(self, args: argparse.Namespace) -> None:
        if not self._require_story_context():
            return

        active_choices = [choice for choice in self._current_choices if choice.available]
        if not active_choices:
            self._cmd.poutput("No cached choices. Run `story` to refresh choices first.")
            return

        index = args.action
        if index < 1 or index > len(active_choices):
            self._cmd.poutput("Choice out of range.")
            return

        choice = active_choices[index - 1]
        try:
            choice_payload = self._choice_payload(choice, args.values, args.payload)
        except ValueError as exc:
            self._cmd.poutput(str(exc))
            return

        result = cast(
            RuntimeEnvelope,
            self._call_service(
                "resolve_choice",
                request=DirectEdgeRequest(
                    edge_id=choice.edge_id,
                    payload=choice_payload,
                ),
            ),
        )
        self._apply_runtime_envelope(result)
        self._render_current_story_update()

    command_parser = argparse.ArgumentParser()
    command_parser.add_argument("text", nargs="+", help="Natural-language story command")

    @with_argparser(command_parser)
    def do_command(self, args: argparse.Namespace) -> None:
        """Find and resolve a story action from command text."""
        if not self._require_story_context():
            return

        result = cast(
            RuntimeEnvelope,
            self._call_service(
                "resolve_choice",
                request=FindEdgeRequest(
                    find_edge=CommandEdgeQuery(command=" ".join(args.text)),
                ),
            ),
        )
        self._apply_runtime_envelope(result)
        self._render_current_story_update()

    drop_story_parser = argparse.ArgumentParser()
    drop_story_parser.add_argument(
        "--archive",
        action="store_true",
        help="Keep the dropped ledger in persistence for later inspection.",
    )

    @with_argparser(drop_story_parser)
    def do_drop_story(self, args: argparse.Namespace) -> None:
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user. Create a user first with 'create_user'.")
            return

        try:
            result = self._call_service(
                "drop_story",
                archive=bool(args.archive),
            )
        except ValueError as exc:
            self._cmd.poutput(str(exc))
            return

        self._cmd.set_ledger(None)
        self._current_story_update.clear()
        self._current_choices.clear()
        self._current_ux_events.clear()
        self._current_metadata.clear()
        self._current_cursor_id = None
        self._current_step = None

        if getattr(result, "status", None) == "error":
            self._cmd.perror(result.message or "Failed to drop story")
            return

        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        elif isinstance(result, dict):
            payload = dict(result)
        else:
            payload = {}

        details = payload.get("details") or {}
        status = payload.get("status") or getattr(result, "status", "dropped")
        dropped_ledger_id = (
            payload.get("dropped_ledger_id")
            or details.get("dropped_ledger_id")
            or details.get("ledger_id")
        )
        archived = bool(payload.get("archived", details.get("archived", False)))
        persistence_deleted = payload.get(
            "persistence_deleted", details.get("persistence_deleted")
        )

        self._cmd.poutput(f"Story {status}.")
        if dropped_ledger_id:
            self._cmd.poutput(f"Dropped ledger: {dropped_ledger_id}")
        self._cmd.poutput(f"Archived: {archived}")
        if persistence_deleted is not None:
            self._cmd.poutput(f"Persistence deleted: {bool(persistence_deleted)}")

    def do_status(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        info = cast(ProjectedState, self._call_service("get_story_info"))
        self._cmd.emit_terminal(self._cmd.terminal_renderer.projected_state(info.to_dto()))
