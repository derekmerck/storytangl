from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tangl.compilers.world_loader import load_scripts, load_world_config
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.story.story_graph import StoryGraph

logger = logging.getLogger(__name__)


def _build_resource_manager(world_root: Path, media_roots: list[str] | None) -> ResourceManager | None:
    if not media_roots:
        return None

    resource_root = world_root / media_roots[0]
    resource_manager = ResourceManager(resource_path=resource_root)
    resource_manager.index_directory(".")
    return resource_manager


def build_world_from_bundle(world_pkg: str) -> tuple[World, dict[str, StoryGraph]]:
    cfg, world_root = load_world_config(world_pkg)
    scripts_ir = load_scripts(cfg, world_root)

    if not scripts_ir:
        msg = f"World '{world_pkg}' does not define any scripts"
        raise ValueError(msg)

    graphs: dict[str, StoryGraph] = {}
    managers: dict[str, ScriptManager] = {}
    for script_cfg in cfg.scripts:
        script_ir = scripts_ir.get(script_cfg.id)
        if script_ir is None:
            logger.warning("No script IR produced for %s", script_cfg.id)
            continue
        manager = ScriptManager.from_story_script(script_ir)
        managers[script_cfg.id] = manager

    if not managers:
        msg = f"World '{cfg.id}' could not be compiled into scripts"
        raise ValueError(msg)

    primary_id = cfg.scripts[0].id if cfg.scripts else next(iter(managers))
    primary_manager = managers[primary_id]

    resource_manager = _build_resource_manager(world_root, cfg.media.roots if cfg.media else None)
    world_label = cfg.title or primary_manager.master_script.label or cfg.id
    world = World(
        label=world_label,
        script_manager=primary_manager,
        resource_manager=resource_manager,
    )
    world.uid = cfg.id
    world.metadata.setdefault("world_id", cfg.id)
    world.media_registry = getattr(world.resource_manager, "registry", None)

    for script_id, manager in managers.items():
        if script_id == primary_id:
            target_world = world
        else:
            target_world = World(
                label=f"{cfg.id}__{script_id}",
                script_manager=manager,
                resource_manager=resource_manager,
            )
            target_world.uid = cfg.id
        script_label = manager.master_script.label or script_id
        graphs[script_id] = target_world.create_story(script_label)

    return world, graphs


class WorldLoader:
    """Backward-compatible wrapper for :func:`build_world_from_bundle`."""

    def __init__(self, world_pkg: str) -> None:
        self.world_pkg = world_pkg

    def load_world(self, world_id: str | None = None, **_: Any) -> World:
        world, _ = build_world_from_bundle(world_id or self.world_pkg)
        return world
