from __future__ import annotations

from pathlib import Path
from typing import IO, Any, Literal

import yaml
from pydantic import BaseModel, Field


class DomainConfig(BaseModel):
    module: str
    setup: str | None = None


class MediaConfig(BaseModel):
    roots: list[str] = Field(default_factory=list)
    registry: str | None = None


class TemplatesConfig(BaseModel):
    registry: str


class AssetsConfig(BaseModel):
    registry: str


class FileSource(BaseModel):
    type: Literal["file"]
    path: str
    format: str = "single_file"
    entry_label: str | None = None


class TreeConventions(BaseModel):
    obj_cls: str
    glob: str = "*.yaml"
    scope: str | None = None


class TreeSource(BaseModel):
    type: Literal["tree"]
    root: str
    entry: dict[str, str] | None = None
    conventions: dict[str, TreeConventions] = Field(default_factory=dict)
    nested: dict[str, TreeConventions] = Field(default_factory=dict)


ScriptSource = FileSource | TreeSource


class ScriptConfig(BaseModel):
    id: str
    label: str
    loader: str
    source: ScriptSource


class WorldConfig(BaseModel):
    id: str
    title: str
    kind: str | None = None

    domain: DomainConfig
    media: MediaConfig | None = None
    templates: TemplatesConfig | None = None
    assets: AssetsConfig | None = None

    scripts: list[ScriptConfig] = Field(default_factory=list)

    @classmethod
    def model_validate_yaml(
        cls, data: str | bytes | Path | IO[str] | IO[bytes]
    ) -> "WorldConfig":
        """Parse a YAML payload or path into a WorldConfig."""

        loaded = cls._load_yaml(data)
        return cls.model_validate(loaded)

    @staticmethod
    def _load_yaml(data: str | bytes | Path | IO[str] | IO[bytes]) -> Any:
        if isinstance(data, Path):
            text = data.read_text()
            return yaml.safe_load(text)

        if isinstance(data, (str, bytes)):
            candidate_path = Path(data)
            if candidate_path.exists():
                text = candidate_path.read_text()
                return yaml.safe_load(text)

        return yaml.safe_load(data)
