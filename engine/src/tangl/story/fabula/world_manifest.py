"""Bundle manifest model for on-disk story worlds."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from tangl.ir.core_ir.script_metadata_model import ScriptMetadata


class WorldManifest(BaseModel):
    """Bundle metadata and resource locations for a world on disk.

    The manifest describes:

    - Bundle identity and layout (uid, scripts, media_dir)
    - Optional story metadata (title, author, etc.)
    - Future extension points (plugins, packages)

    The manifest can embed a ScriptMetadata block, or rely on the
    script files to provide metadata. World construction reconciles
    both sources, with script metadata taking precedence.
    """

    # === Bundle Identity ===
    uid: str
    label: Optional[str] = None
    version: str = "1.0"

    # === Script Entrypoints ===
    scripts: str | list[str]

    # === Media Layout ===
    media_dir: str = "media"

    # === Story Metadata (Optional) ===
    metadata: Optional[ScriptMetadata] = None

    # === Launcher/UI Metadata ===
    tags: list[str] = Field(default_factory=list)

    # === Future Extension Points (Not Parsed in MVP) ===
    python_packages: Optional[list[str]] = None
    plugins: Optional[dict] = None

    # === Validators ===

    @model_validator(mode="after")
    def _normalize_scripts(self) -> "WorldManifest":
        """Convert single script string to list."""

        if isinstance(self.scripts, str):
            self.scripts = [self.scripts]
        return self

    @model_validator(mode="after")
    def _validate_uid_is_filesystem_safe(self) -> "WorldManifest":
        """Ensure uid contains only safe characters."""

        allowed = self.uid.replace("_", "").replace("-", "")
        if not allowed.isalnum():
            raise ValueError(
                f"uid '{self.uid}' must be filesystem-safe "
                f"(alphanumeric, underscore, hyphen only)"
            )
        return self

    # === Properties ===

    @property
    def script_paths_relative(self) -> list[str]:
        """Script paths as declared, relative to bundle root."""

        return list(self.scripts)

    @property
    def effective_label(self) -> str:
        """Label used by engine/launcher.

        Priority:

        1. Explicit label field
        2. Embedded metadata.title
        3. Fallback to uid
        """

        if self.label:
            return self.label
        if self.metadata and self.metadata.title:
            return self.metadata.title
        return self.uid
