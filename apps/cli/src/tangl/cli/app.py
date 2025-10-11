"""Interactive shell for StoryTangl demo stories."""

# todo: Note this currently bypasses the entire 'controller' layer and accesses the graph directly

from __future__ import annotations

from pathlib import Path
import uuid
from typing import Optional

import cmd2
import yaml

from tangl.compiler.script_manager import ScriptManager
from tangl.core.graph.edge import Edge
from tangl.core.graph.graph import Graph
from tangl.core.graph.node import Node
from tangl.info import __version__
from tangl.story.fabula.actor.actor import Actor
from tangl.story.story_domain.world import World
from tangl.vm.frame import Frame

banner = f"t4⅁gL-cl1 v{__version__}"


class NarrativeBlock(Node):
    """CLI-friendly block node that preserves inline ``content``."""

    content: str | None = None


class NarrativeAction(Edge):
    """CLI-friendly edge storing ``text`` for presentation."""

    text: str | None = None


NarrativeBlock.model_rebuild()
NarrativeAction.model_rebuild()


class TanglShell(cmd2.Cmd):
    """Minimal interactive shell that loads scripts and plays stories."""

    prompt = "⅁$ "

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_story: Optional[Graph] = None
        self.current_frame: Optional[Frame] = None
        self._current_actions: list[Edge] = []

    def _require_story(self) -> bool:
        if self.current_frame is None or self.current_story is None:
            self.poutput("No active story. Load a script first.")
            return False
        return True

    def _render_story(self) -> None:
        if not self._require_story():
            return

        block = self.current_frame.cursor
        self.poutput(f"Story: {self.current_story.label}")
        self.poutput(f"# {block.label}\n")

        text = getattr(block, "content", None) or getattr(block, "text", None)
        if text:
            self.poutput(text.strip())
            self.poutput("")

        actions = [
            edge
            for edge in self.current_story.find_edges(source_id=self.current_frame.cursor_id)
            if getattr(edge, "trigger_phase", None) is None
        ]
        self._current_actions = actions

        if not actions:
            self.poutput("No available actions.")
            return

        self.poutput("Choices:")
        for index, edge in enumerate(actions, start=1):
            label = getattr(edge, "text", None)
            if label is None:
                label = edge.label.replace("_", " ") if edge.label else f"Choice {index}"
            self.poutput(f"{index}. {label}")

    def do_load_script(self, arg: str) -> None:
        """Load a story script from YAML and instantiate its world."""

        if not arg:
            self.poutput("Usage: load_script <path_to_yaml>")
            return

        script_path = Path(arg).expanduser()
        if not script_path.exists():
            self.poutput(f"File not found: {script_path}")
            return

        with script_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        self._ensure_cli_classes(data)

        script_manager = ScriptManager.from_data(data)
        world_label = data.get("label", "default_world")

        Actor.model_rebuild()
        World.clear_instances()
        world = World(label=world_label, script_manager=script_manager)
        world.domain_manager.register_class("NarrativeBlock", NarrativeBlock)
        world.domain_manager.register_class("NarrativeAction", NarrativeAction)

        self.poutput(f"Loaded world: {world_label}")
        title = script_manager.master_script.metadata.title
        if title:
            self.poutput(f"Title: {title}")

        self.do_create_story(world_label)

    def do_create_story(self, arg: str) -> None:
        """Create a story instance for the given world label."""

        world_label = arg.strip() or "default_world"
        world = World.find_instance(label=world_label)
        if world is None:
            self.poutput(f"World '{world_label}' not found. Load a script first.")
            return

        story_label = f"story_{uuid.uuid4().hex[:8]}"
        story = world.create_story(story_label)

        self.current_story = story
        self.current_frame = story.cursor
        self._current_actions = []

        self.poutput(f"Created story: {story_label}")
        self._render_story()

    def do_story(self, arg: str) -> None:  # noqa: ARG002 - cmd2 signature
        """Display the current narrative block and available actions."""

        self._render_story()

    def do_choose(self, arg: str) -> None:
        """Select an action by its list index."""

        if not self._require_story():
            return

        choice_str = arg.strip()
        if not choice_str:
            self.poutput("Usage: choose <number>")
            return

        try:
            index = int(choice_str)
        except ValueError:
            self.poutput("Choice must be a number.")
            return

        if index < 1 or index > len(self._current_actions):
            self.poutput("Choice out of range.")
            return

        edge = self._current_actions[index - 1]
        next_edge = self.current_frame.follow_edge(edge)
        while isinstance(next_edge, Edge):
            next_edge = self.current_frame.follow_edge(next_edge)

        self._render_story()

    def do_do(self, arg: str) -> None:
        """Alias for :cmd:`choose`."""

        self.do_choose(arg)

    def _ensure_cli_classes(self, data: dict) -> None:
        scenes = data.get("scenes")
        if not scenes:
            return

        if isinstance(scenes, dict):
            scene_iter = scenes.values()
        else:
            scene_iter = scenes

        for scene in scene_iter:
            blocks = scene.get("blocks")
            if not blocks:
                continue

            if isinstance(blocks, dict):
                block_iter = blocks.values()
            else:
                block_iter = blocks

            for block in block_iter:
                block.setdefault("block_cls", "NarrativeBlock")
                for key in ("actions", "continues", "redirects"):
                    for action in block.get(key, []):
                        action.setdefault("obj_cls", "NarrativeAction")


app = TanglShell()
