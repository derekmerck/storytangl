from __future__ import annotations

import argparse
from pprint import pformat
from typing import TYPE_CHECKING
from pathlib import Path

from cmd2 import CommandSet, with_argparser, with_default_category
from tangl.service38 import ServiceOperation38
from tangl.service38.operations import endpoint_for_operation

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("World")
class WorldController(CommandSet):
    """World inspection commands powered by service38."""

    _cmd: StoryTanglCLI

    def _call_service(self, operation: ServiceOperation38, **params):
        call_operation = getattr(self._cmd, "call_operation", None)
        if callable(call_operation):
            return call_operation(operation, **params)
        return self._cmd.call_endpoint(endpoint_for_operation(operation), **params)

    def do_worlds(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        worlds = self._call_service(ServiceOperation38.WORLD_LIST)
        self._cmd.poutput(pformat(worlds))

    world_parser = argparse.ArgumentParser()
    world_parser.add_argument("world", type=str, help="World identifier")

    @with_argparser(world_parser)
    def do_world_info(self, args: argparse.Namespace) -> None:
        info = self._call_service(ServiceOperation38.WORLD_INFO, world_id=args.world)
        self._cmd.poutput(pformat(info))

    script_path_parser = argparse.ArgumentParser()
    script_path_parser.add_argument("script_path", type=Path, help="World path")

    @with_argparser(script_path_parser)
    def do_load_script(self, args: argparse.Namespace) -> None:
        import yaml
        script_data = yaml.safe_load(args.script_path.read_text())
        from tangl.story.fabula.world import World
        result = self._call_service(
            ServiceOperation38.WORLD_LOAD,
            script_data=script_data,
        )

        if getattr(result, "status", None) == "error":
            self._cmd.perror(result.message or "Failed to load world")
            return

        world_label = None
        if hasattr(result, "details") and result.details:
            world_label = result.details.get("world_label")
        world = World.get_instance(world_label) if world_label else None

        title = None
        if world is not None and world.script_manager is not None:
            title = world.script_manager.get_story_metadata().get("title")

        title_text = title or world_label or "<unknown>"
        out = f"Loaded world: {title_text}"
        self._cmd.poutput(pformat(out))

    create_story_parser = argparse.ArgumentParser()
    create_story_parser.add_argument("world_id", type=str, help="World id to create")

    # def do_create_story(self, world_id: str):
    #     result = self._cmd.call_endpoint("WorldController.create_story", world_id=world_id)
    #     self._cmd.poutput(pformat(result))
