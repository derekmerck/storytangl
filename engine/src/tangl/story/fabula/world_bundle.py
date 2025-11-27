"""Filesystem bundle representation for story worlds."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from .world_manifest import WorldManifest

logger = logging.getLogger(__name__)


class WorldBundle(BaseModel):
    """Link a manifest to its on-disk bundle location."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bundle_root: Path
    manifest: WorldManifest

    # === Path Resolution ===

    @property
    def media_dir(self) -> Path:
        """Absolute path to media directory."""

        return self.bundle_root / self.manifest.media_dir

    @property
    def script_paths(self) -> list[Path]:
        """Absolute paths to all script files."""

        return [self.bundle_root / rel_path for rel_path in self.manifest.scripts]

    # === Loading ===

    @classmethod
    def load(cls, bundle_root: Path) -> "WorldBundle":
        """Load bundle from directory with world.yaml manifest."""

        resolved_root = Path(bundle_root).expanduser().resolve()
        manifest_path = resolved_root / "world.yaml"

        if not manifest_path.exists():
            raise FileNotFoundError(f"No world.yaml found at {resolved_root}")

        manifest_data = yaml.safe_load(manifest_path.read_text())
        manifest = WorldManifest.model_validate(manifest_data)

        if manifest.uid != resolved_root.name:
            raise ValueError(
                "Manifest uid '%s' must match directory name '%s' (MVP constraint)"
                % (manifest.uid, resolved_root.name)
            )

        return cls(bundle_root=resolved_root, manifest=manifest)
