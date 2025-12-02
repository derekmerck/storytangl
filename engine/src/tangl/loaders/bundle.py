from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .manifest import WorldManifest


@dataclass
class WorldBundle:
    """Filesystem representation of a world bundle."""

    bundle_root: Path
    manifest: WorldManifest

    @property
    def media_dir(self) -> Path:
        return self.bundle_root / self.manifest.media_dir

    @property
    def domain_dir(self) -> Path | None:
        default_domain = self.bundle_root / "domain"
        return default_domain if default_domain.exists() else None

    def get_script_paths(self, story_key: str | None = None) -> list[Path]:
        scripts = self.manifest.scripts
        if scripts is not None:
            if isinstance(scripts, dict):
                script_list: list[str] | str = []
                if story_key:
                    script_list = scripts[story_key]
                else:
                    for value in scripts.values():
                        if isinstance(value, list):
                            script_list.extend(value)
                        else:
                            script_list.append(value)
            else:
                script_list = scripts

            if isinstance(script_list, str):
                script_list = [script_list]

            return [self.bundle_root / script for script in script_list]

        single_file = self.bundle_root / "script.yaml"
        if single_file.exists():
            return [single_file]

        scripts_dir = self.bundle_root / "scripts"
        if scripts_dir.exists():
            return sorted(scripts_dir.rglob("*.yaml"))

        msg = f"No scripts found in {self.bundle_root}"
        raise ValueError(msg)

    @property
    def script_paths(self) -> list[Path]:
        return self.get_script_paths()

    @classmethod
    def load(cls, bundle_root: Path) -> "WorldBundle":
        manifest_path = bundle_root / "world.yaml"
        if not manifest_path.exists():
            msg = f"No world.yaml at {bundle_root}"
            raise FileNotFoundError(msg)

        with open(manifest_path, encoding="utf-8") as manifest_file:
            manifest_data: Any = yaml.safe_load(manifest_file)

        manifest = WorldManifest.model_validate(manifest_data)

        if manifest.label != bundle_root.name:
            msg = (
                f"Manifest label '{manifest.label}' must match directory name "
                f"'{bundle_root.name}'"
            )
            raise ValueError(msg)

        return cls(bundle_root, manifest)
