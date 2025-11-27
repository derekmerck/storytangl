"""Discovery and loading utilities for world bundles."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import yaml
from pydantic import BaseModel, ConfigDict, PrivateAttr

from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World

from .world_bundle import WorldBundle

logger = logging.getLogger(__name__)


class WorldLoader(BaseModel):
    """Discovers and loads world bundles from filesystem."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    world_dirs: list[Path]
    _bundles: dict[str, WorldBundle] = PrivateAttr(default_factory=dict)

    # === Discovery ===

    def discover_bundles(self) -> dict[str, WorldBundle]:
        """Scan world_dirs for bundles with world.yaml."""

        bundles: dict[str, WorldBundle] = {}

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
                except Exception as exc:  # pragma: no cover - defensive logging path
                    logger.error(
                        "Failed to load bundle at %s: %s", item, exc, exc_info=True
                    )
                    continue

                bundles[bundle.manifest.uid] = bundle
                logger.info("Discovered world '%s' at %s", bundle.manifest.uid, item)

        self._bundles = bundles
        return bundles

    # === Script Loading ===

    def _load_script_data(self, script_paths: Iterable[Path]) -> dict:
        """Load YAML script files into IR data dict."""

        script_paths = list(script_paths)

        if len(script_paths) != 1:
            raise NotImplementedError(
                f"Multi-file world scripts not yet supported (got {len(script_paths)} files)"
            )

        script_path = script_paths[0]

        if not script_path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")

        return yaml.safe_load(script_path.read_text())

    # === World Construction ===

    def load_world(self, world_id: str) -> World:
        """Compile world scripts into World with resources attached."""

        bundle = self._bundles.get(world_id)
        if not bundle:
            raise ValueError(
                f"Unknown world: {world_id} (discovered: {list(self._bundles.keys())})"
            )

        script_data = self._load_script_data(bundle.script_paths)
        script_manager = ScriptManager.from_data(script_data)
        resource_manager = ResourceManager(resource_path=bundle.media_dir)

        world = World(
            label=bundle.manifest.effective_label,
            script_manager=script_manager,
            resource_manager=resource_manager,
        )

        world.bundle = bundle

        logger.info(
            "Loaded world '%s' from %s with %d script(s)",
            world.name,
            bundle.bundle_root,
            len(bundle.script_paths),
        )

        return world
