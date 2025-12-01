from __future__ import annotations

from pathlib import Path

from tangl.compilers.world_config import FileSource, WorldConfig
from tangl.compilers.world_loader import load_world_config


class WorldBundle:
    """
    Locate resources for a loaded world bundle using compiler utilities.

    This class exists as a lightweight compatibility shim for legacy call
    sites. New code should prefer :func:`tangl.story.fabula.world_loader.build_world_from_bundle`
    to construct a :class:`~tangl.story.fabula.world.World` and story graphs
    directly from the compiler IR.
    """

    def __init__(self, bundle_root: Path, config: WorldConfig) -> None:
        self.bundle_root = bundle_root
        self.config = config

    @property
    def media_dir(self) -> Path | None:
        """Absolute path to the bundle's media directory if configured."""

        if not self.config.media or not self.config.media.roots:
            return None

        return self.bundle_root / self.config.media.roots[0]

    @property
    def script_paths(self) -> list[Path]:
        """Absolute paths to any file-based scripts declared in the manifest."""

        paths: list[Path] = []
        for script_cfg in self.config.scripts:
            source = script_cfg.source
            if isinstance(source, FileSource):
                paths.append(self.bundle_root / source.path)
        return paths

    @classmethod
    def load(cls, world_pkg: str) -> "WorldBundle":
        """Load a world bundle using compiler world configuration support."""

        config, bundle_root = load_world_config(world_pkg)
        return cls(bundle_root=bundle_root, config=config)
