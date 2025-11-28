from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .world_manifest import WorldManifest


class WorldBundle:
    """Locate resources for a loaded world bundle."""

    def __init__(self, bundle_root: Path, manifest: WorldManifest) -> None:
        self.bundle_root = bundle_root
        self.manifest = manifest

    @property
    def media_dir(self) -> Path:
        """Absolute path to the bundle's media directory."""

        return self.bundle_root / self.manifest.media_dir

    @property
    def script_paths(self) -> list[Path]:
        """Absolute paths to all script files declared in the manifest."""

        return [self.bundle_root / script for script in self.manifest.scripts]

    @classmethod
    def load(cls, bundle_root: Path) -> "WorldBundle":
        """Load a world bundle from ``bundle_root`` containing ``world.yaml``."""

        manifest_path = bundle_root / "world.yaml"
        if not manifest_path.exists():
            msg = f"No world.yaml at {bundle_root}"
            raise FileNotFoundError(msg)

        with open(manifest_path, encoding="utf-8") as manifest_file:
            manifest_data: Any = yaml.safe_load(manifest_file)

        manifest = WorldManifest.model_validate(manifest_data)

        if manifest.uid != bundle_root.name:
            msg = (
                f"Manifest uid '{manifest.uid}' must match directory name "
                f"'{bundle_root.name}'"
            )
            raise ValueError(msg)

        return cls(bundle_root, manifest)
