from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from tangl.config import get_world_dirs
from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.media.system_media import get_system_resource_manager

from .script_manager import ScriptManager
from .world import World
from .world_bundle import WorldBundle

logger = logging.getLogger(__name__)


class WorldLoader:
    """Discover and load world bundles from configured directories."""

    def __init__(self, world_dirs: list[Path] | None = None) -> None:
        # Use configured dirs by default, but allow tests to override
        self.world_dirs = world_dirs or get_world_dirs()
        self._bundles: dict[str, WorldBundle] = {}

    def discover_bundles(self) -> dict[str, WorldBundle]:
        """Scan ``world_dirs`` for bundles that contain ``world.yaml``."""

        for world_dir in self.world_dirs:
            if not world_dir.exists():
                logger.warning("World directory %s does not exist", world_dir)
                continue

            for item in world_dir.iterdir():
                if not item.is_dir():
                    continue

                manifest_path = item / "world.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    bundle = WorldBundle.load(item)
                    self._bundles[bundle.manifest.uid] = bundle
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to load bundle at %s: %s", item, exc)

        return self._bundles

    def _load_scripts(self, bundle: WorldBundle) -> dict[str, Any]:
        """Load and merge script YAML documents from the bundle."""

        script_data: dict[str, Any] = {}
        for script_path in bundle.script_paths:
            with open(script_path, encoding="utf-8") as script_file:
                data = yaml.safe_load(script_file) or {}

            if not isinstance(data, dict):
                msg = f"Script payload at {script_path} must be a mapping"
                raise ValueError(msg)

            script_data |= data

        return script_data

    def load_world(self, world_id: str, **kwargs: Any) -> World:
        """Compile scripts into a :class:`World` with bundle metadata attached."""

        bundle = self._bundles.get(world_id)
        if not bundle:
            msg = f"Unknown world: {world_id}"
            raise ValueError(msg)

        script_data = self._load_scripts(bundle)
        script_manager = ScriptManager.from_data(script_data)

        resource_manager = ResourceManager(resource_path=bundle.media_dir)
        resource_manager.index_directory(".")

        world = World(
            label=bundle.manifest.label,
            script_manager=script_manager,
            resource_manager=resource_manager,
            **kwargs,
        )
        world.uid = bundle.manifest.uid
        world._bundle = bundle  # noqa: SLF001 - temporary private slot for bundle access
        world.media_registry = resource_manager.registry
        world.system_resource_manager = get_system_resource_manager()

        return world
