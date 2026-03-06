from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from tangl.loaders import UniqueLabel, WorldBundle, WorldCompiler
from tangl.story38.fabula import World38

if TYPE_CHECKING:
    from tangl.story38.fabula import World38 as World

logger = logging.getLogger(__name__)


def _get_world_dirs() -> list[Path]:
    try:
        from tangl.service import world_registry as legacy_world_registry

        return list(legacy_world_registry.get_world_dirs())
    except Exception:
        from tangl.config import get_world_dirs

        return list(get_world_dirs())


class WorldRegistry:
    """Discover and lazily compile worlds from configured directories."""

    def __init__(self, world_dirs: list[Path] | None = None, compiler: WorldCompiler | None = None) -> None:
        self.compiler = compiler or WorldCompiler()
        self.bundles: dict[UniqueLabel, WorldBundle] = {}
        self.worlds38: dict[UniqueLabel, World38] = {}

        if world_dirs is None:
            world_dirs = _get_world_dirs()

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

    def get_world(self, label: UniqueLabel, *, runtime_version: str = "38") -> World:
        _ = runtime_version
        if label not in self.worlds38:
            bundle = self.bundles.get(label)
            if not bundle:
                msg = f"Unknown world: {label}"
                raise ValueError(msg)
            self.worlds38[label] = self.compiler.compile(bundle, runtime_version="38")
        return self.worlds38[label]

    def get_anthology(
        self,
        label: UniqueLabel,
        *,
        runtime_version: str = "38",
    ) -> dict[str, World]:
        bundle = self.bundles.get(label)
        if not bundle:
            msg = f"Unknown world: {label}"
            raise ValueError(msg)

        if not bundle.manifest.is_anthology:
            msg = f"World {label} is not an anthology"
            raise ValueError(msg)

        _ = runtime_version
        return self.compiler.compile_anthology(bundle, runtime_version="38")
