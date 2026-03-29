from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ItemsView

from tangl.loaders import UniqueLabel, WorldBundle, WorldCompiler
from tangl.story.fabula import World
from tangl.utils.sanitize_str import sanitize_str

logger = logging.getLogger(__name__)


_MANUAL_WORLDS: dict[str, World] = {}


def _get_world_dirs() -> list[Path]:
    return list(get_world_dirs())


def get_world_dirs() -> list[Path]:
    """Compatibility helper retained for existing tests and monkeypatch hooks."""
    from tangl.config import get_world_dirs as _config_get_world_dirs

    return list(_config_get_world_dirs())


def legacy_world_label(script_data: dict[str, Any]) -> str | None:
    """Derive a stable legacy label from raw script payload."""

    metadata = script_data.get("metadata")
    if isinstance(metadata, dict):
        title = metadata.get("title")
        if isinstance(title, str) and title.strip():
            return sanitize_str(title).lower()

    raw_label = script_data.get("label")
    if isinstance(raw_label, str) and raw_label.strip():
        return sanitize_str(raw_label).lower()
    return None


def register_manual_world(world: World) -> None:
    """Register one process-local manual world."""

    _MANUAL_WORLDS[world.label] = world


def pop_manual_world(world_id: str) -> World | None:
    """Remove one process-local manual world by label."""

    return _MANUAL_WORLDS.pop(world_id, None)


def iter_manual_worlds() -> ItemsView[str, World]:
    """Return the process-local manual worlds."""

    return _MANUAL_WORLDS.items()


def clear_manual_worlds() -> None:
    """Clear process-local manual worlds."""

    _MANUAL_WORLDS.clear()


def resolve_world(world_id: str) -> World:
    """Resolve a world from manual overrides or configured registries."""

    if world_id in _MANUAL_WORLDS:
        return _MANUAL_WORLDS[world_id]

    registry = WorldRegistry()
    world = registry.get_world(world_id)
    if not isinstance(world, World):
        raise TypeError(f"Expected Story world for '{world_id}', got {type(world)!r}")
    return world


class WorldRegistry:
    """Discover and lazily compile worlds from configured directories."""

    def __init__(self, world_dirs: list[Path] | None = None, compiler: WorldCompiler | None = None) -> None:
        self.compiler = compiler or WorldCompiler()
        self.bundles: dict[UniqueLabel, WorldBundle] = {}
        self.worlds: dict[UniqueLabel, World] = {}

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

    def get_world(self, label: UniqueLabel) -> World:
        if label not in self.worlds:
            bundle = self.bundles.get(label)
            if not bundle:
                msg = f"Unknown world: {label}"
                raise ValueError(msg)
            self.worlds[label] = self.compiler.compile(bundle)
        return self.worlds[label]

    def get_anthology(
        self,
        label: UniqueLabel,
    ) -> dict[str, World]:
        bundle = self.bundles.get(label)
        if not bundle:
            msg = f"Unknown world: {label}"
            raise ValueError(msg)

        if not bundle.manifest.is_anthology:
            msg = f"World {label} is not an anthology"
            raise ValueError(msg)

        return self.compiler.compile_anthology(bundle)
