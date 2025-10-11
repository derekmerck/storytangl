from __future__ import annotations

import argparse
from typing import TYPE_CHECKING
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("Restricted")
class DevController(CommandSet):
    """Development utilities that lean on runtime endpoints."""

    _cmd: StoryTanglCLI

    node_parser = argparse.ArgumentParser()
    node_parser.add_argument("node_id", type=str, help="Node identifier")

    @with_argparser(node_parser)
    def do_goto_node(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        try:
            node_id = UUID(args.node_id)
        except ValueError:
            self._cmd.poutput("Invalid node id.")
            return
        result = self._cmd.call_endpoint("RuntimeController.jump_to_node", node_id=node_id)
        fragments = result.get("fragments", []) if isinstance(result, dict) else result
        for fragment in fragments:
            self._cmd.poutput(getattr(fragment, "content", fragment))

    @with_argparser(node_parser)
    def do_inspect(self, _: argparse.Namespace) -> None:
        self._cmd.poutput("Node inspection not yet supported in the orchestrated CLI.")

    expr_parser = argparse.ArgumentParser()
    expr_parser.add_argument("expr", type=str, help="Expression to evaluate")

    @with_argparser(expr_parser)
    def do_check(self, _: argparse.Namespace) -> None:
        self._cmd.poutput("Expression checks are not yet supported.")

    @with_argparser(expr_parser)
    def do_apply(self, _: argparse.Namespace) -> None:
        self._cmd.poutput("Expression effects are not yet supported.")
