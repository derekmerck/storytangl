from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import yaml

if TYPE_CHECKING:
    from .bundle import WorldBundle


@dataclass(slots=True, frozen=True)
class SourceRef:
    """Reference to a source artifact used during codec decode."""

    path: str
    story_key: str | None = None
    note: str | None = None


class LossKind(str, Enum):
    """Classification for structured codec decode loss records."""

    UNSUPPORTED_FEATURE = "unsupported_feature"
    SOURCE_INTEGRITY = "source_integrity"
    AUTHORING_DEBT = "authoring_debt"


@dataclass(slots=True, frozen=True)
class LossRecord:
    """Structured description of source content a codec could not map cleanly."""

    kind: LossKind
    feature: str
    passage: str
    excerpt: str
    note: str | None = None


@dataclass(slots=True)
class DecodeResult:
    """Result from decoding story content into runtime-ready script data.

    Notes
    -----
    This shape intentionally keeps source provenance coarse for now. We record
    file-level references first, then refine to per-node/per-field spans in
    future codec revisions.
    """

    story_data: dict[str, Any]
    source_map: dict[str, list[SourceRef]] = field(default_factory=dict)
    codec_state: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    loss_records: list[LossRecord] = field(default_factory=list)


class StoryCodec(Protocol):
    """Protocol for world format codecs.

    A codec defines a serialization contract between on-disk source and
    runtime-ready story data.

    Decode and encode are related but not required to be symmetric. Some codecs
    intentionally support import-only workflows.
    """

    codec_id: str

    def decode(
        self,
        *,
        bundle: WorldBundle,
        script_paths: list[Path],
        story_key: str | None,
    ) -> DecodeResult:
        """Decode source files into runtime-ready story data."""

    def encode(
        self,
        *,
        bundle: WorldBundle,
        runtime_data: dict[str, Any],
        story_key: str | None,
        codec_state: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Encode runtime data back to on-disk representation.

        Returns
        -------
        dict[str, str]
            Mapping of relative paths to file content.
        """


class NearNativeYamlCodec:
    """Default codec for StoryTangl near-native YAML scripts.

    Why
    ---
    Near-native YAML is already very close to runtime schema, so this codec is
    intentionally minimal: it merges script files and carries file-level source
    references. This keeps the path easy to reason about while story contracts
    are still evolving.
    """

    codec_id = "near_native_yaml"

    def decode(
        self,
        *,
        bundle: WorldBundle,
        script_paths: list[Path],
        story_key: str | None,
    ) -> DecodeResult:
        merged: dict[str, Any] = {}
        refs: list[SourceRef] = []
        warnings: list[str] = []

        for script_path in script_paths:
            with open(script_path, encoding="utf-8") as file_obj:
                data = yaml.safe_load(file_obj) or {}
            if not isinstance(data, dict):
                msg = f"Script file {script_path} must decode to a mapping"
                raise ValueError(msg)
            collisions = sorted(set(merged.keys()) & set(data.keys()))
            if collisions:
                warnings.append(
                    "Codec merge overwrote top-level keys "
                    f"(story_key={story_key!r}, path={script_path}, keys={collisions})"
                )
            merged.update(data)
            refs.append(SourceRef(path=str(script_path), story_key=story_key))

        return DecodeResult(
            story_data=merged,
            source_map={"__source_files__": refs},
            codec_state={
                "codec_id": self.codec_id,
                "script_paths": [str(path) for path in script_paths],
                "story_key": story_key,
                "world_label": bundle.manifest.label,
            },
            warnings=warnings,
        )

    def encode(
        self,
        *,
        bundle: WorldBundle,
        runtime_data: dict[str, Any],
        story_key: str | None,
        codec_state: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        script_paths = (codec_state or {}).get("script_paths")
        if script_paths:
            target = Path(script_paths[0])
            try:
                rel_path = str(target.relative_to(bundle.bundle_root))
            except ValueError:
                rel_path = target.name or "script.yaml"
        else:
            rel_path = "script.yaml"
        content = yaml.safe_dump(runtime_data, sort_keys=False, allow_unicode=True)
        return {rel_path: content}


class CodecRegistry:
    """Registry for bundle codecs.

    Notes
    -----
    The first pass only ships a near-native YAML codec. External codecs can be
    registered by tooling or domain packages without changing loader internals.
    """

    def __init__(self) -> None:
        self._codecs: dict[str, StoryCodec] = {}
        default_codec = NearNativeYamlCodec()
        for alias in ("near_native", "near_native_yaml", "yaml"):
            self.register(alias, default_codec)
        from .codecs import register_bundled_codecs

        register_bundled_codecs(self)

    def register(self, key: str, codec: StoryCodec) -> None:
        self._codecs[str(key)] = codec

    def get(self, key: str) -> StoryCodec:
        codec = self._codecs.get(key)
        if codec is None:
            msg = f"Unknown story codec: {key}"
            raise ValueError(msg)
        return codec
