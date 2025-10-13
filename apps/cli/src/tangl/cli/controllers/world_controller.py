from __future__ import annotations

import argparse
from pprint import pformat
from typing import TYPE_CHECKING
from pathlib import Path

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

    script_path_parser = argparse.ArgumentParser()
    script_path_parser.add_argument("script_path", type=Path, help="World path")

    @with_argparser(script_path_parser)
    def do_load_script(self, args: argparse.Namespace) -> None:
        import yaml
        script_data = yaml.safe_load(args.script_path.read_text())
        from tangl.story.story_domain.world import World
        world: World = self._cmd.call_endpoint("WorldController.load_world", script_data=script_data)
        out = f"Loaded world: {world.script_manager.get_story_metadata().get('title')}"
        self._cmd.poutput(pformat(out))

    create_story_parser = argparse.ArgumentParser()
    create_story_parser.add_argument("world_id", type=str, help="World id to create")

    # def do_create_story(self, world_id: str):
    #     result = self._cmd.call_endpoint("WorldController.create_story", world_id=world_id)
    #     self._cmd.poutput(pformat(result))
