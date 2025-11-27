from __future__ import annotations

from pathlib import Path

from pydantic import BaseSettings, Field, model_validator


class Settings(BaseSettings):
    """Application settings used across the Tangl engine."""

    WORLD_DIRS: list[Path] = Field(
        default_factory=lambda: [
            Path.cwd() / "worlds",
            Path(__file__).parent.parent.parent
            / "tests"
            / "resources"
            / "worlds",
        ]
    )

    @model_validator(mode="after")
    def expand_world_dirs(self) -> "Settings":
        """Resolve configured world directories to absolute paths."""

        self.WORLD_DIRS = [Path(directory).expanduser().resolve() for directory in self.WORLD_DIRS]
        return self
