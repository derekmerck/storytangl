from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

UniqueLabel = str


class StorySourceSpec(BaseModel):
    """Per-story source declaration for multi-story bundles.

    Notes
    -----
    `StorySourceSpec` is intentionally small in MVP. It captures which files
    feed a story and optionally which codec should decode them. Deeper domain
    layering and fine-grained source discovery can be added without changing the
    base world contract.
    """

    scripts: str | list[str] | None = None
    codec: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scripts", mode="before")
    @classmethod
    def normalize_scripts(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return value


class WorldManifest(BaseModel):
    """Schema for ``world.yaml`` files with convention-based defaults.

    Notes
    -----
    Worlds may declare either:
    - legacy top-level `scripts`, or
    - explicit `stories` mapping.
    Both shapes are supported during migration. The `stories` form is preferred
    because it expresses anthology structure directly and allows per-story codec
    selection.
    """

    label: UniqueLabel = Field(
        ...,
        description="World label, must match directory name",
    )
    scripts: str | list[str] | dict[str, str | list[str]] | None = None
    stories: dict[str, StorySourceSpec] | None = None
    codec: str = "near_native"
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
        return self.stories is not None or isinstance(self.scripts, dict)

    def story_keys(self) -> list[str]:
        if self.stories is not None:
            return list(self.stories.keys())
        if self.is_anthology:
            return list(self.scripts.keys())
        return ["default"]

    def get_story_codec(self, story_key: str | None = None) -> str:
        if story_key and self.stories and story_key in self.stories:
            story_codec = self.stories[story_key].codec
            if story_codec:
                return story_codec
        return self.codec

    def get_story_scripts(self, story_key: str | None = None) -> list[str] | None:
        if self.stories is not None:
            if story_key is None:
                scripts: list[str] = []
                for spec in self.stories.values():
                    if spec.scripts:
                        scripts.extend(spec.scripts)
                return scripts or None
            spec = self.stories.get(story_key)
            if spec is None:
                msg = f"Unknown story key: {story_key}"
                raise KeyError(msg)
            return spec.scripts

        if self.scripts is None:
            return None
        if isinstance(self.scripts, dict):
            script_value = self.scripts[story_key] if story_key else self.scripts
            if isinstance(script_value, dict):
                scripts: list[str] = []
                for value in script_value.values():
                    if isinstance(value, list):
                        scripts.extend(value)
                    else:
                        scripts.append(value)
                return scripts
            if isinstance(script_value, str):
                return [script_value]
            return list(script_value)
        if isinstance(self.scripts, str):
            return [self.scripts]
        return list(self.scripts)
