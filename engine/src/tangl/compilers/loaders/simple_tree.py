from __future__ import annotations

from pathlib import Path

import yaml

from tangl.compilers.loaders.base import ScriptLoader
from tangl.compilers.loaders.registry import register_loader
from tangl.compilers.world_config import ScriptConfig, TreeSource, WorldConfig
from tangl.story.ir import StoryMetadata, StoryScript


def _load_convention_dir(directory: Path, glob_pattern: str) -> dict[str, object]:
    entries: dict[str, object] = {}
    if not directory.exists():
        return entries

    for path in sorted(directory.glob(glob_pattern)):
        if path.is_file():
            entries[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    return entries


def _assign_category(name: str, store: dict[str, dict[str, object]], data: dict[str, object]) -> None:
    if not data:
        return

    if name not in store:
        store[name] = {}

    store[name].update(data)


@register_loader("simple_tree")
class SimpleTreeLoader:
    """Load a tree of YAML files into :class:`StoryScript` buckets."""

    def load(
        self,
        world_root: Path,
        world_cfg: WorldConfig,
        script_cfg: ScriptConfig,
    ) -> StoryScript:
        assert isinstance(script_cfg.source, TreeSource)

        source = script_cfg.source
        root_path = world_root / source.root

        buckets: dict[str, dict[str, object]] = {
            "blocks": {},
            "actors": {},
            "locations": {},
            "resources": {},
            "extra": {},
        }

        for name, convention in source.conventions.items():
            directory = root_path / name
            data = _load_convention_dir(directory, convention.glob)
            _assign_category(name, buckets, data)

        for name, convention in source.nested.items():
            for directory in root_path.rglob(name):
                if directory.is_dir():
                    data = _load_convention_dir(directory, convention.glob)
                    _assign_category(name, buckets, data)

        metadata = StoryMetadata(
            id=script_cfg.id,
            label=script_cfg.label,
            world_id=world_cfg.id,
            entry_label=(source.entry or {}).get("block_label", "start"),
        )

        return StoryScript(
            metadata=metadata,
            blocks=buckets.get("blocks", {}),
            actors=buckets.get("actors", {}),
            locations=buckets.get("locations", {}),
            resources=buckets.get("resources", {}),
            extra={k: v for k, v in buckets.items() if k not in {"blocks", "actors", "locations", "resources"}},
        )
