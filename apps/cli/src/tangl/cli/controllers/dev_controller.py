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

    def _call_endpoint(self, endpoint: str, **params):
        return self._cmd.call_endpoint(endpoint, **params)

    def _print_runtime(self, result: object) -> None:
        if hasattr(result, "model_dump"):
            payload = result.model_dump()
        elif isinstance(result, dict):
            payload = result
        else:
            self._cmd.poutput(str(result))
            return
        for key, value in payload.items():
            self._cmd.poutput(f"{key}: {value}")

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
        result = self._call_endpoint("RuntimeController.jump_to_node", node_id=node_id)
        self._print_runtime(result)

    @with_argparser(node_parser)
    def do_inspect(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        try:
            node_id: UUID | str = UUID(args.node_id)
        except ValueError:
            node_id = args.node_id
        result = self._call_endpoint("RuntimeController.get_node_info", node_id=node_id)
        self._print_runtime(result)

    expr_parser = argparse.ArgumentParser()
    expr_parser.add_argument("expr", type=str, help="Expression to evaluate")

    @with_argparser(expr_parser)
    def do_check(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        result = self._call_endpoint("RuntimeController.check_expr", expr=args.expr)
        self._print_runtime(result)

    @with_argparser(expr_parser)
    def do_apply(self, args: argparse.Namespace) -> None:
        if self._cmd.ledger_id is None:
            self._cmd.poutput("No active ledger.")
            return
        result = self._call_endpoint("RuntimeController.apply_effect", expr=args.expr)
        self._print_runtime(result)
