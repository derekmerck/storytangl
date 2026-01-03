from __future__ import annotations

from typing import Any

from tangl.ir.story_ir.story_script_models import StoryScript
from tangl.story.fabula.script_manager import ScriptManager


class ScriptCompiler:
    """Compile script data into a :class:`ScriptManager`."""

    def compile(self, script_data: dict) -> ScriptManager:
        script = StoryScript.model_validate(script_data)
        _mark_declared_instances(script)
        return ScriptManager.from_master_script(script)


def _iter_script_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, dict):
        return value.values()
    return value


def _mark_declared_instances(script: StoryScript) -> None:
    """Mark declared instances in the script hierarchy."""

    scenes = getattr(script, "scenes", None)
    if scenes:
        for scene in _iter_script_items(scenes):
            if getattr(scene, "declares_instance", False) is False:
                scene.update_attrs(declares_instance=True, force=True)
            blocks = getattr(scene, "blocks", None)
            if blocks:
                for block in _iter_script_items(blocks):
                    if getattr(block, "declares_instance", False) is False:
                        block.update_attrs(declares_instance=True, force=True)

    passages = getattr(script, "passages", None)
    if passages:
        for passage in _iter_script_items(passages):
            if getattr(passage, "declares_instance", False) is False:
                passage.update_attrs(declares_instance=True, force=True)
