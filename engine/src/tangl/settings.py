"""Application settings powered by Pydantic."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project-wide configuration values."""

    WORLD_DIRS: list[Path] = Field(
        default_factory=lambda: [Path.cwd() / "worlds"],
        description="Directories to scan for world bundles",
    )

    @model_validator(mode="after")
    def _normalize_world_dirs(self) -> "Settings":
        """Expand and resolve world directory paths."""

        self.WORLD_DIRS = [Path(d).expanduser().resolve() for d in self.WORLD_DIRS]
        return self


settings = Settings()
