from __future__ import annotations

from pathlib import Path

import yaml

from tangl.compilers.loaders.base import ScriptLoader
from tangl.compilers.loaders.registry import register_loader
from tangl.compilers.world_config import FileSource, ScriptConfig, WorldConfig
from tangl.story.ir import StoryMetadata, StoryScript


@register_loader("simple_single_file")
class SimpleSingleFileLoader:
    """Load a single YAML file into a :class:`StoryScript`."""

    def load(
        self,
        world_root: Path,
        world_cfg: WorldConfig,
        script_cfg: ScriptConfig,
    ) -> StoryScript:
        assert isinstance(script_cfg.source, FileSource)

        source = script_cfg.source
        script_path = world_root / source.path

        data = yaml.safe_load(script_path.read_text(encoding="utf-8")) or {}

        metadata = StoryMetadata(
            id=script_cfg.id,
            label=script_cfg.label,
            world_id=world_cfg.id,
            entry_label=source.entry_label or data.get("entry", "start"),
        )

        reserved_keys = {"id", "title", "actors", "locations", "blocks", "resources", "entry"}

        return StoryScript(
            metadata=metadata,
            blocks=data.get("blocks", {}),
            actors=data.get("actors", {}),
            locations=data.get("locations", {}),
            resources=data.get("resources", {}),
            extra={k: v for k, v in data.items() if k not in reserved_keys},
        )
