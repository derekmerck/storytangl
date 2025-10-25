from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("User")
class UserController(CommandSet):
    """User management commands backed by the orchestrated service layer."""

    _cmd: StoryTanglCLI

    create_user_parser = argparse.ArgumentParser()
    create_user_parser.add_argument("secret", type=str, help="Secret used to seed the user key")

    @with_argparser(create_user_parser)
    def do_create_user(self, args: argparse.Namespace) -> None:
        user = self._cmd.call_endpoint("UserController.create_user", secret=args.secret)
        if hasattr(user, "uid"):
            self._cmd.set_user(user.uid)
        if self._cmd.persistence is not None:
            self._cmd.persistence.save(user)
        self._cmd.poutput(f"User created with secret '{args.secret}'.")
        if hasattr(user, "uid"):
            self._cmd.poutput(f"Active user id: {user.uid}")

    use_user_parser = argparse.ArgumentParser()
    use_user_parser.add_argument("user_id", type=str, help="Existing user identifier")

    @with_argparser(use_user_parser)
    def do_use_user(self, args: argparse.Namespace) -> None:
        try:
            user_id = UUID(args.user_id)
        except ValueError:
            self._cmd.poutput("Invalid user id.")
            return
        self._cmd.set_user(user_id)
        self._cmd.poutput(f"Active user set to {user_id}.")

    ledger_parser = argparse.ArgumentParser()
    ledger_parser.add_argument("ledger_id", type=str, help="Ledger identifier to bind")

    @with_argparser(ledger_parser)
    def do_set_ledger(self, args: argparse.Namespace) -> None:
        try:
            ledger_id = UUID(args.ledger_id)
        except ValueError:
            self._cmd.poutput("Invalid ledger id.")
            return
        self._cmd.set_ledger(ledger_id)
        self._cmd.poutput(f"Active ledger set to {ledger_id}.")

    secret_parser = argparse.ArgumentParser()
    secret_parser.add_argument("secret", type=str, help="New secret for the active user")

    @with_argparser(secret_parser)
    def do_change_secret(self, args: argparse.Namespace) -> None:
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user. Use `user use_user` first.")
            return
        info = self._cmd.call_endpoint("UserController.update_user", secret=args.secret)
        self._cmd.poutput(f"Secret updated. API key: {getattr(info, 'api_key', info)}")

    def do_user_info(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user.")
            return
        info = self._cmd.call_endpoint("UserController.get_user_info")
        self._render_info(info)

    key_parser = argparse.ArgumentParser()
    key_parser.add_argument("secret", type=str, help="Secret to encode as API key")

    @with_argparser(key_parser)
    def do_key(self, args: argparse.Namespace) -> None:
        info = self._cmd.call_endpoint("UserController.get_key_for_secret", secret=args.secret)
        api_key = getattr(info, "api_key", None) or info
        self._cmd.poutput(f"API key: {api_key}")

    def do_drop_user(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        if self._cmd.user_id is None:
            self._cmd.poutput("No active user.")
            return
        identifiers = self._cmd.call_endpoint("UserController.drop_user")
        if isinstance(identifiers, tuple):
            self._cmd.remove_resources(identifier for identifier in identifiers if isinstance(identifier, UUID))
        self._cmd.poutput("User removed. Active user cleared.")
        self._cmd.set_user(None)
        self._cmd.set_ledger(None)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _render_info(self, info: Any) -> None:
        if isinstance(info, dict):
            for key, value in info.items():
                self._cmd.poutput(f"{key}: {value}")
            return
        if hasattr(info, "model_dump"):
            for key, value in info.model_dump().items():
                self._cmd.poutput(f"{key}: {value}")
            return
        self._cmd.poutput(info)
