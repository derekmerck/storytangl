from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class WorldManifest(BaseModel):
    """Bundle metadata and resource locations."""

    uid: str
    label: str
    version: str = "1.0"
    scripts: str | list[str]
    media_dir: str = "media"
    python_packages: Optional[list[str]] = None
    plugins: Optional[dict] = None
    author: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_scripts(self) -> "WorldManifest":
        if isinstance(self.scripts, str):
            self.scripts = [self.scripts]
        return self

    @model_validator(mode="after")
    def validate_uid_is_filesystem_safe(self) -> "WorldManifest":
        sanitized = self.uid.replace("_", "").replace("-", "")
        if not sanitized.isalnum():
            msg = f"uid '{self.uid}' must be filesystem-safe"
            raise ValueError(msg)
        return self
