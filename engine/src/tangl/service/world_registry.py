from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, ItemsView

from tangl.loaders import UniqueLabel, WorldBundle, WorldCompiler
from tangl.story.fabula import World
from tangl.utils.sanitize_str import sanitize_str

logger = logging.getLogger(__name__)


_MANUAL_WORLDS: dict[str, World] = {}
_DISCOVERED_REGISTRIES: dict[tuple[Path, ...], "WorldRegistry"] = {}


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


def clear_discovered_world_registries() -> None:
    """Clear cached discovered registries between isolated service runs."""

    _DISCOVERED_REGISTRIES.clear()


def resolve_world(world_id: str) -> World:
    """Resolve a world from manual overrides or configured registries."""

    if world_id in _MANUAL_WORLDS:
        return _MANUAL_WORLDS[world_id]

    world_dirs = tuple(_get_world_dirs())
    registry = _DISCOVERED_REGISTRIES.get(world_dirs)
    if registry is None:
        registry = WorldRegistry(list(world_dirs))
        _DISCOVERED_REGISTRIES[world_dirs] = registry
    world = registry.get_world(world_id)
    if not isinstance(world, World):
        raise TypeError(f"Expected Story world for '{world_id}', got {type(world)!r}")
    return world


class WorldRegistry:
    """Discover and lazily compile worlds from configured directories.

    Every world a client can open has its own id. A single-story bundle is one
    world, named by its label. An anthology is not itself a world: each of its
    books is, named by the manifest's ``story_label(key)`` (``carwars_cw1``), and
    the anthology's own label names only the collection.
    """

    def __init__(self, world_dirs: list[Path] | None = None, compiler: WorldCompiler | None = None) -> None:
        self.compiler = compiler or WorldCompiler()
        self.bundles: dict[UniqueLabel, WorldBundle] = {}
        # Every world id a client can open -> its bundle, and its story key if a book.
        self.openable: dict[UniqueLabel, tuple[WorldBundle, str | None]] = {}
        self.worlds: dict[UniqueLabel, World] = {}

        if world_dirs is None:
            world_dirs = _get_world_dirs()

        self._discover(world_dirs)
        self._index_openable()

    def _discover(self, world_dirs: list[Path]) -> None:
        """Scan every configured search root for world bundles.

        ``world_dirs`` is a search path: a root that is absent is normal, since
        one configuration is expected to name roots that only exist in some
        deployments. What is worth reporting is having nothing to scan at all,
        which is the case that actually leaves the service with no worlds.
        """

        scanned = 0
        for world_dir in world_dirs:
            if not world_dir.exists():
                logger.debug("World search root %s is absent, skipping", world_dir)
                continue
            scanned += 1

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

        if not scanned:
            logger.warning(
                "No world search root exists; no worlds will be available. Searched: %s",
                ", ".join(str(world_dir) for world_dir in world_dirs) or "(nothing configured)",
            )

    def _index_openable(self) -> None:
        """Index the world ids of the bundles discovery kept.

        Indexed only once discovery is done, so a bundle that a later search root
        replaced contributes none of its books.
        """
        for bundle in self.bundles.values():
            manifest = bundle.manifest
            if not manifest.is_anthology:
                self.openable[manifest.label] = (bundle, None)
                continue
            for story_key in manifest.story_keys():
                book_id = manifest.story_label(story_key)
                if book_id in self.bundles:
                    logger.error(
                        "Book %s of anthology %s has the same id as a world; the world wins",
                        book_id,
                        manifest.label,
                    )
                    continue
                self.openable[book_id] = (bundle, story_key)

    def list_worlds(self) -> list[dict]:
        """Every world a client can open: single worlds, and each anthology's books.

        Listing compiles nothing; each world is listed with the metadata its
        manifest gives it (see :meth:`WorldManifest.story_metadata`).
        """
        return [
            {
                "label": world_id,
                "metadata": bundle.manifest.story_metadata(story_key),
                "anthology": bundle.manifest.label if story_key is not None else None,
            }
            for world_id, (bundle, story_key) in self.openable.items()
        ]

    def get_world(self, label: UniqueLabel) -> World:
        if label not in self.worlds:
            self.worlds[label] = self.compile_world(label)
        return self.worlds[label]

    def compile_world(self, label: UniqueLabel) -> World:
        """Compile one world afresh, bypassing the cache."""
        if label not in self.openable:
            if label in self.bundles:
                books = ", ".join(
                    world_id
                    for world_id, (bundle, _story_key) in self.openable.items()
                    if bundle.manifest.label == label
                )
                msg = f"{label} is an anthology; open one of its books: {books}"
                raise ValueError(msg)
            msg = f"Unknown world: {label}"
            raise ValueError(msg)
        bundle, story_key = self.openable[label]
        return self.compiler.compile(bundle, story_key=story_key)

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
