from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category


if TYPE_CHECKING:
    from ..app import StoryTanglCLI


def _fragment_text(fragment: Any) -> str:
    for attr in ("content", "text", "label"):
        value = getattr(fragment, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("_", " ")
    return str(fragment)


@with_default_category("Story")
class StoryController(CommandSet):
    """Story commands backed by :class:`tangl.service.controllers.RuntimeController`."""

    _cmd: StoryTanglCLI

    def __init__(self) -> None:
        super().__init__()
        self._current_story_update: list[Any] = []
        self._current_choices: list[SimpleNamespace] = []

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
        if not self._current_story_update:
            self._cmd.poutput("No journal entries available.")
            return

        self._cmd.poutput("Story Update:")
        self._cmd.poutput("-------------------------")
        for fragment in self._current_story_update:
            self._cmd.poutput(_fragment_text(fragment))

        if not self._current_choices:
            self._cmd.poutput("No available choices.")
            return

        self._cmd.poutput("Choices:")
        active_index = 1
        for choice in self._current_choices:
            label = choice.label or str(choice.uid)
            is_active = getattr(choice, "active", True)
            reason = getattr(choice, "unavailable_reason", None)
            if is_active:
                self._cmd.poutput(f"{active_index}. {label}")
                active_index += 1
                continue
            reason_text = f" [locked: {reason}]" if reason else " [locked]"
            self._cmd.poutput(f"x) {label}{reason_text}")

    def _load_choices_from_fragments(self) -> list[SimpleNamespace]:
        """Extract choices from fragment stream (from blocks or loose)."""

        choices: list[SimpleNamespace] = []

        for fragment in self._current_story_update:
            ftype = getattr(fragment, "fragment_type", None)

            if ftype == "block":
                embedded = getattr(fragment, "choices", None) or []
                for choice_frag in embedded:
                    uid = getattr(choice_frag, "source_id", None) or getattr(
                        choice_frag, "uid", None
                    )
                    label = (
                        getattr(choice_frag, "label", None)
                        or getattr(choice_frag, "content", "")
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
                uid = getattr(fragment, "source_id", None) or getattr(fragment, "uid", None)
                label = (
                    getattr(fragment, "label", None)
                    or getattr(fragment, "content", "")
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

        result = self._cmd.call_endpoint("RuntimeController.create_story", **kwargs)
        if getattr(result, "status", None) == "error":
            self._cmd.perror(result.message or "Failed to create story")
            return

        details = getattr(result, "details", None) or {}
        ledger_obj = details.get("ledger")
        ledger_id_value = details.get("ledger_id")
        ledger_id = UUID(ledger_id_value) if ledger_id_value is not None else None

        if ledger_obj is not None and self._cmd.persistence is not None:
            self._cmd.persistence.save(ledger_obj)

        if ledger_id is not None:
            self._cmd.set_ledger(ledger_id)

        title = details.get("title") or "<unknown>"
        cursor_label = details.get("cursor_label") or "<unknown>"

        self._cmd.poutput(f"\nCreated story: {title}")
        self._cmd.poutput(f"Starting at: {cursor_label}")
        if ledger_id is not None:
            self._cmd.poutput(f"Ledger ID: {ledger_id}\n")

        fragments = self._cmd.call_endpoint(
            "RuntimeController.get_journal_entries",
            limit=10,
        )
        self._current_story_update = list(fragments)

        if self._current_story_update:
            self._cmd.poutput("--- Story Begins ---")
            for fragment in self._current_story_update:
                self._cmd.poutput(_fragment_text(fragment))
            self._cmd.poutput()

        self._current_choices = self._load_choices_from_fragments()
        if self._current_choices:
            self._cmd.poutput("Choices:")
            active_index = 1
            for choice in self._current_choices:
                label = choice.label or str(choice.uid)
                if getattr(choice, "active", True):
                    self._cmd.poutput(f"{active_index}. {label}")
                    active_index += 1
                    continue
                reason = getattr(choice, "unavailable_reason", None)
                reason_text = f" [locked: {reason}]" if reason else " [locked]"
                self._cmd.poutput(f"x) {label}{reason_text}")
        else:
            self._cmd.poutput("(No choices available)")

        self._cmd.poutput("\nUse 'do <number>' to make a choice.")

    def do_story(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        fragments = self._cmd.call_endpoint(
            "RuntimeController.get_journal_entries",
            limit=10,
        )
        self._current_story_update = list(fragments)
        self._current_choices = self._load_choices_from_fragments()
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
        self._cmd.call_endpoint(
            "RuntimeController.resolve_choice",
            choice_id=choice.uid,
        )
        fragments = self._cmd.call_endpoint(
            "RuntimeController.get_journal_entries",
            limit=10,
        )
        self._current_story_update = list(fragments)
        self._current_choices = self._load_choices_from_fragments()
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
            result = self._cmd.call_endpoint(
                "RuntimeController.drop_story",
                archive=bool(args.archive),
            )
        except ValueError as exc:
            self._cmd.poutput(str(exc))
            return

        self._cmd.set_ledger(None)
        self._current_story_update.clear()
        self._current_choices.clear()

        if getattr(result, "status", None) == "error":
            self._cmd.perror(result.message or "Failed to drop story")
            return

        details = getattr(result, "details", None) or {}
        status = result.status if hasattr(result, "status") else "dropped"
        dropped_ledger_id = details.get("dropped_ledger_id")
        archived = bool(details.get("archived", False))
        persistence_deleted = details.get("persistence_deleted")

        self._cmd.poutput(f"Story {status}.")
        if dropped_ledger_id:
            self._cmd.poutput(f"Dropped ledger: {dropped_ledger_id}")
        self._cmd.poutput(f"Archived: {archived}")
        if persistence_deleted is not None:
            self._cmd.poutput(f"Persistence deleted: {bool(persistence_deleted)}")

    def do_status(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        info = self._cmd.call_endpoint("RuntimeController.get_story_info")
        if hasattr(info, "model_dump"):
            payload = info.model_dump()
        elif isinstance(info, dict):
            payload = info
        else:
            payload = {"info": str(info)}

        for key, value in payload.items():
            self._cmd.poutput(f"{key}: {value}")
