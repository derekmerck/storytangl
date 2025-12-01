from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tangl.compilers.world_config import ScriptConfig, WorldConfig
from tangl.story.ir import StoryScript


class ScriptLoader(Protocol):
    def load(
        self,
        world_root: Path,
        world_cfg: WorldConfig,
        script_cfg: ScriptConfig,
    ) -> StoryScript:
        """Load a story script from a world bundle into the StoryScript IR."""

