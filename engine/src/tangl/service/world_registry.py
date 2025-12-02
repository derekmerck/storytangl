from __future__ import annotations

import logging
from pathlib import Path

from tangl.config import get_world_dirs
from tangl.story.fabula import World

from tangl.loaders import UniqueLabel, WorldBundle, WorldCompiler

logger = logging.getLogger(__name__)


class WorldRegistry:
    """Discover and lazily compile worlds from configured directories."""

    def __init__(self, world_dirs: list[Path] | None = None, compiler: WorldCompiler | None = None) -> None:
        self.compiler = compiler or WorldCompiler()
        self.bundles: dict[UniqueLabel, WorldBundle] = {}
        self.worlds: dict[UniqueLabel, World] = {}

        if world_dirs is None:
            world_dirs = get_world_dirs()

        self._discover(world_dirs)

    def _discover(self, world_dirs: list[Path]) -> None:
        for world_dir in world_dirs:
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
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Failed to load %s: %s", item, exc)
                    continue

                self.bundles[bundle.manifest.label] = bundle
                logger.info("Discovered world: %s", bundle.manifest.label)

    def list_worlds(self) -> list[dict]:
        return [
            {
                "label": bundle.manifest.label,
                "metadata": bundle.manifest.metadata,
                "is_anthology": bundle.manifest.is_anthology,
            }
            for bundle in self.bundles.values()
        ]

    def get_world(self, label: UniqueLabel) -> World:
        if label not in self.worlds:
            bundle = self.bundles.get(label)
            if not bundle:
                msg = f"Unknown world: {label}"
                raise ValueError(msg)

            self.worlds[label] = self.compiler.compile(bundle)
        return self.worlds[label]

    def get_anthology(self, label: UniqueLabel) -> dict[str, World]:
        bundle = self.bundles.get(label)
        if not bundle:
            msg = f"Unknown world: {label}"
            raise ValueError(msg)

        if not bundle.manifest.is_anthology:
            msg = f"World {label} is not an anthology"
            raise ValueError(msg)

        return self.compiler.compile_anthology(bundle)
