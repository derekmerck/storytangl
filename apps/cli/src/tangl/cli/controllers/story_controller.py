from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Mapping
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category


if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("Story")
class StoryController(CommandSet):
    """Story commands backed by :class:`tangl.service.ServiceManager`."""

    _cmd: StoryTanglCLI

    def __init__(self) -> None:
        super().__init__()
        self._current_story_update: list[Any] = []
        self._current_choices: list[SimpleNamespace] = []
        self._current_metadata: dict[str, Any] = {}

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
                metadata=self._current_metadata,
            )
        )

    def _load_choices_from_fragments(self) -> list[SimpleNamespace]:
        """Extract choices from fragment stream (from blocks or loose)."""

        choices: list[SimpleNamespace] = []

        for fragment in self._current_story_update:
            ftype = getattr(fragment, "fragment_type", None)

            if ftype == "block":
                embedded = getattr(fragment, "choices", None) or []
                for choice_frag in embedded:
                    uid = (
                        getattr(choice_frag, "edge_id", None)
                        or getattr(choice_frag, "source_id", None)
                        or getattr(choice_frag, "uid", None)
                    )
                    label = (
                        getattr(choice_frag, "label", None)
                        or getattr(choice_frag, "content", "")
                        or getattr(choice_frag, "text", "")
                        or getattr(choice_frag, "source_label", "")
                    )
                    active = getattr(choice_frag, "active", True)
                    reason = getattr(choice_frag, "unavailable_reason", None)

                    if uid:
                        choices.append(
                            SimpleNamespace(
                                uid=UUID(str(uid)),
                                label=label.replace("_", " "),
                                active=active,
                                unavailable_reason=reason,
                            )
                        )

            elif ftype == "choice":
                uid = (
                    getattr(fragment, "edge_id", None)
                    or getattr(fragment, "source_id", None)
                    or getattr(fragment, "uid", None)
                )
                label = (
                    getattr(fragment, "label", None)
                    or getattr(fragment, "content", "")
                    or getattr(fragment, "text", "")
                    or getattr(fragment, "source_label", "")
                )
                active = getattr(fragment, "active", True)
                reason = getattr(fragment, "unavailable_reason", None)

                if uid:
                    choices.append(
                        SimpleNamespace(
                            uid=UUID(str(uid)),
                            label=label.replace("_", " "),
                            active=active,
                            unavailable_reason=reason,
                        )
                    )

        return choices

    def _call_service(self, method_name: str, **params: Any) -> Any:
        return self._cmd.call_service(method_name, **params)

    def _apply_runtime_envelope(self, envelope: Any) -> None:
        metadata = getattr(envelope, "metadata", None) or {}
        if not isinstance(metadata, Mapping):
            metadata = {}
        self._current_metadata = dict(metadata)
        ledger_id_value = metadata.get("ledger_id")
        if ledger_id_value is not None:
            self._cmd.set_ledger(UUID(str(ledger_id_value)))
        self._current_story_update = list(getattr(envelope, "fragments", []) or [])
        self._current_choices = self._load_choices_from_fragments()

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

        result = self._call_service("create_story", **kwargs)
        self._apply_runtime_envelope(result)

        title = args.world_id
        ledger_id = self._cmd.ledger_id

        self._cmd.emit_terminal(
            self._cmd.terminal_renderer.story_created(
                title=title,
                ledger_id=ledger_id,
                fragments=self._current_story_update,
                choices=self._current_choices,
                metadata=self._current_metadata,
            )
        )

    def do_story(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        result = self._call_service("get_story_update", limit=10)
        self._apply_runtime_envelope(result)
        self._render_current_story_update()

    choose_parser = argparse.ArgumentParser()
    choose_parser.add_argument("action", type=int, help="Choice number to execute")

    @with_argparser(choose_parser)
    def do_do(self, args: argparse.Namespace) -> None:
        if not self._require_story_context():
            return

        active_choices = [
            choice for choice in self._current_choices if getattr(choice, "active", True)
        ]
        if not active_choices:
            self._cmd.poutput("No cached choices. Run `story` to refresh choices first.")
            return

        index = args.action
        if index < 1 or index > len(active_choices):
            self._cmd.poutput("Choice out of range.")
            return

        choice = active_choices[index - 1]
        result = self._call_service(
            "resolve_choice",
            edge_id=choice.uid,
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
        self._current_metadata.clear()

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

        info = self._call_service("get_story_info")
        if hasattr(info, "model_dump"):
            payload = info.model_dump()
        elif isinstance(info, dict):
            payload = info
        else:
            payload = {"info": str(info)}

        self._cmd.emit_terminal(self._cmd.terminal_renderer.projected_state(payload))
