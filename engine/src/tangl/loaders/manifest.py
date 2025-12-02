from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

UniqueLabel = str


class WorldManifest(BaseModel):
    """Schema for ``world.yaml`` files with convention-based defaults."""

    label: UniqueLabel = Field(
        ...,
        description="World label, must match directory name",
    )
    scripts: str | list[str] | dict[str, str | list[str]] | None = None
    media_dir: str = "media"
    media_organization: dict[str, dict] | None = Field(default=None)
    domain_module: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scripts", mode="before")
    @classmethod
    def normalize_scripts(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return value

    @property
    def is_anthology(self) -> bool:
        return isinstance(self.scripts, dict)

    def story_keys(self) -> list[str]:
        if self.is_anthology:
            return list(self.scripts.keys())
        return ["default"]
