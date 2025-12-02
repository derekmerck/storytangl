from __future__ import annotations

from tangl.story.fabula.script_manager import ScriptManager


class ScriptCompiler:
    """Compile script data into a :class:`ScriptManager`."""

    def compile(self, script_data: dict) -> ScriptManager:
        return ScriptManager.from_data(script_data)
