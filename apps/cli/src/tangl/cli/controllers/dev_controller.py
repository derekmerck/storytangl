from __future__ import annotations

import argparse
from typing import TYPE_CHECKING
from uuid import UUID

from cmd2 import CommandSet, with_argparser, with_default_category
from tangl.service38 import ServiceOperation38
from tangl.service38.operations import endpoint_for_operation

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("Restricted")
class DevController(CommandSet):
    """Development utilities that lean on runtime endpoints."""

    _cmd: StoryTanglCLI

    def _call_service(self, operation: ServiceOperation38, **params):
        call_operation = getattr(self._cmd, "call_operation", None)
        if callable(call_operation):
            return call_operation(operation, **params)
        return self._cmd.call_endpoint(endpoint_for_operation(operation), **params)

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
        result = self._call_service(ServiceOperation38.STORY_JUMP, node_id=node_id)
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
