from __future__ import annotations

from importlib import import_module, resources
from pathlib import Path

import tangl.compilers.loaders  # noqa: F401
from tangl.compilers.loaders.registry import get_loader
from tangl.compilers.world_config import WorldConfig
from tangl.story.ir import StoryScript


def load_world_config(world_pkg: str) -> tuple[WorldConfig, Path]:
    pkg = import_module(world_pkg)
    root = Path(resources.files(pkg))
    yaml_path = root / "world.yaml"
    cfg = WorldConfig.model_validate_yaml(yaml_path)
    return cfg, root


def load_scripts(cfg: WorldConfig, world_root: Path) -> dict[str, StoryScript]:
    scripts: dict[str, StoryScript] = {}
    for script_cfg in cfg.scripts:
        loader = get_loader(script_cfg.loader)
        scripts[script_cfg.id] = loader.load(world_root, cfg, script_cfg)
    return scripts
