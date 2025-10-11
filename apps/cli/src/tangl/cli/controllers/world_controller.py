from __future__ import annotations

import argparse
from pprint import pformat
from typing import TYPE_CHECKING

from cmd2 import CommandSet, with_argparser, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("World")
class WorldController(CommandSet):
    """World inspection commands powered by the orchestrator."""

    _cmd: StoryTanglCLI

    def do_worlds(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        worlds = self._cmd.call_endpoint("WorldController.list_worlds")
        self._cmd.poutput(pformat(worlds))

    world_parser = argparse.ArgumentParser()
    world_parser.add_argument("world", type=str, help="World identifier")

    @with_argparser(world_parser)
    def do_world_info(self, args: argparse.Namespace) -> None:
        info = self._cmd.call_endpoint("WorldController.get_world_info", world_id=args.world)
        self._cmd.poutput(pformat(info))
