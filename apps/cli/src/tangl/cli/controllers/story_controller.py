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
        for index, choice in enumerate(self._current_choices, start=1):
            label = choice.label or str(choice.uid)
            self._cmd.poutput(f"{index}. {label} ({str(choice.uid)[:6]})")

    def _load_choices(self) -> list[SimpleNamespace]:
        choices = self._cmd.call_endpoint("RuntimeController.get_available_choices")
        parsed: list[SimpleNamespace] = []
        for choice in choices:
            if isinstance(choice, dict):
                uid = choice.get("uid") or choice.get("id")
                label = choice.get("label") or choice.get("text") or ""
            else:
                uid = getattr(choice, "uid", None)
                label = getattr(choice, "label", "") or getattr(choice, "text", "")
            if uid is None:
                continue
            parsed.append(SimpleNamespace(uid=UUID(str(uid)), label=label.replace("_", " ")))
        return parsed

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

        ledger_obj = result.get("ledger")
        if ledger_obj is not None and self._cmd.persistence is not None:
            self._cmd.persistence.save(ledger_obj)

        ledger_id = UUID(result["ledger_id"])
        self._cmd.set_ledger(ledger_id)

        self._cmd.poutput(f"\nCreated story: {result['title']}")
        self._cmd.poutput(f"Starting at: {result['cursor_label']}")
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

        self._current_choices = self._load_choices()
        if self._current_choices:
            self._cmd.poutput("Choices:")
            for idx, choice in enumerate(self._current_choices, start=1):
                label = choice.label or str(choice.uid)
                self._cmd.poutput(f"{idx}. {label}")
        else:
            self._cmd.poutput("(No choices available)")

        self._cmd.poutput("\nUse 'do <number>' to make a choice.")

    def do_story(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        fragments = self._cmd.call_endpoint("RuntimeController.get_journal_entries", limit=10)
        self._current_story_update = list(fragments)
        self._current_choices = self._load_choices()
        self._render_current_story_update()

    choose_parser = argparse.ArgumentParser()
    choose_parser.add_argument("action", type=int, help="Choice number to execute")

    @with_argparser(choose_parser)
    def do_do(self, args: argparse.Namespace) -> None:
        if not self._require_story_context():
            return

        if not self._current_choices:
            self._cmd.poutput("No cached choices. Run `story` to refresh choices first.")
            return

        index = args.action
        if index < 1 or index > len(self._current_choices):
            self._cmd.poutput("Choice out of range.")
            return

        choice = self._current_choices[index - 1]
        self._cmd.call_endpoint(
            "RuntimeController.resolve_choice",
            choice_id=choice.uid,
        )
        fragments = self._cmd.call_endpoint(
            "RuntimeController.get_journal_entries",
            limit=10,
        )
        self._current_story_update = list(fragments)
        self._current_choices = self._load_choices()
        self._render_current_story_update()

    def do_status(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if not self._require_story_context():
            return

        info = self._cmd.call_endpoint("RuntimeController.get_story_info")
        if isinstance(info, dict):
            for key, value in info.items():
                self._cmd.poutput(f"{key}: {value}")
            return
        self._cmd.poutput(info)
