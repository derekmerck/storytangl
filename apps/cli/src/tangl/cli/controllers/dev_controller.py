from __future__ import annotations

import argparse
from typing import TYPE_CHECKING
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("Restricted")
class DevController(CommandSet):
    """Deferred development utilities outside the manager-first CLI nucleus."""

    _cmd: StoryTanglCLI

    def _not_implemented(self) -> None:
        self._cmd.poutput("Restricted runtime debug commands are not implemented in the manager-first CLI.")

    node_parser = argparse.ArgumentParser()
    node_parser.add_argument("node_id", type=str, help="Node identifier")

    @with_argparser(node_parser)
    def do_goto_node(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        try:
            UUID(args.node_id)
        except ValueError:
            self._cmd.poutput("Invalid node id.")
            return
        self._not_implemented()

    @with_argparser(node_parser)
    def do_inspect(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        try:
            UUID(args.node_id)
        except ValueError:
            pass
        self._not_implemented()

    expr_parser = argparse.ArgumentParser()
    expr_parser.add_argument("expr", type=str, help="Expression to evaluate")

    @with_argparser(expr_parser)
    def do_check(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        self._not_implemented()

    @with_argparser(expr_parser)
    def do_apply(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        self._not_implemented()
