"""DiceBear backend spec and the portrait-to-DiceBear adaptation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from dicebear import Style
from pydantic import Field

from tangl.core import Priority
from tangl.media.media_creators.media_spec import (
    MediaResolutionClass,
    MediaSpec,
    on_adapt_media_spec,
)
from tangl.media.media_data_type import MediaDataType
from tangl.media.media_creators.portrait_spec import PortraitSpec
from tangl.utils.hashing import hashing_func

if TYPE_CHECKING:
    from .dicebear_forge import DiceBearForge


DICEBEAR_STYLE_ID = "lorelei"
DICEBEAR_STYLE_VERSION = version("dicebear-styles")
DICEBEAR_ADAPTER_VERSION = "1"

LORELEI_TRAIT_OPTION_MAP: dict[str, dict[str, str]] = {
    "hair_color": {
        "blonde": "f5d76e",
        "brown": "6b3e26",
        "dark": "2f2320",
        "red": "c65d3b",
        "gray": "9aa0a6",
        "white": "f4f4f0",
        "auburn": "8c3b24",
    },
    "eye_color": {
        "blue": "4d8fc3",
        "brown": "6b4a36",
        "green": "5e8c5a",
        "gray": "89939e",
        "black": "202124",
    },
    "skin_tone": {
        "light": "f5d6c6",
        "tan": "d49a6a",
        "olive": "b78b5a",
        "dark": "6e4732",
        "asian": "e3b28d",
        "eurasian": "d5a37f",
        "latin": "c4875b",
        "semitic": "b97852",
        "amerind": "a86f4d",
    },
}

_LORELEI_OPTION_NAMES = {
    "hair_color": "hairColor",
    "eye_color": "eyesColor",
    "skin_tone": "skinColor",
}


def normalize_portrait_traits(traits: Mapping[str, Any]) -> dict[str, str]:
    """Return a stable, renderer-neutral representation of supplied traits."""
    normalized: dict[str, str] = {}
    for key, value in traits.items():
        if value is None:
            continue
        raw_value = getattr(value, "value", value)
        normalized_key = str(key).strip().casefold().replace(" ", "_")
        normalized_value = str(raw_value).strip().casefold().replace("_", " ")
        if normalized_key and normalized_value:
            normalized[normalized_key] = normalized_value
    return normalized


def map_lorelei_traits(traits: Mapping[str, str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Map supported traits to Lorelei options and retain the rest as provenance."""
    options: dict[str, list[str]] = {}
    ignored: dict[str, str] = {}
    for trait, value in traits.items():
        palette = LORELEI_TRAIT_OPTION_MAP.get(trait)
        color = palette.get(value) if palette is not None else None
        if color is None:
            ignored[trait] = value
            continue
        options[_LORELEI_OPTION_NAMES[trait]] = [color]
    return options, ignored


def derive_portrait_seed(
    *,
    identity_key: str,
    style_definition_hash: str,
    explicit_seed: str | int | None,
) -> str:
    """Return an explicit seed or a stable identity-and-style-derived seed."""
    if explicit_seed is not None:
        return str(explicit_seed)
    payload = {
        "identity_key": identity_key,
        "style_definition_hash": style_definition_hash,
        "adapter_version": DICEBEAR_ADAPTER_VERSION,
    }
    return hashing_func(payload).hex()


def style_definition_hash(definition_json: str) -> str:
    """Return a content hash for one exact DiceBear style definition."""
    return sha256(definition_json.encode("utf-8")).hexdigest()


@cache
def lorelei_definition_json() -> str:
    """Load the installed official CC0 Lorelei definition without HTTP."""
    return files("dicebear_styles").joinpath("lorelei.json").read_text(encoding="utf-8")


@cache
def lorelei_style() -> Style:
    """Return a validated DiceBear style object for the installed Lorelei data."""
    return Style(json.loads(lorelei_definition_json()))


class DiceBearSpec(MediaSpec):
    """Complete local DiceBear request and execution provenance for Lorelei."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    style_id: str = DICEBEAR_STYLE_ID
    style_definition_version: str = DICEBEAR_STYLE_VERSION
    style_definition_hash: str
    seed: str
    options: dict[str, Any]
    adapter_version: str = DICEBEAR_ADAPTER_VERSION
    ignored_traits: dict[str, str] = Field(default_factory=dict)
    renderer_name: str | None = None
    renderer_version: str | None = None
    resolved_options: dict[str, Any] | None = None

    @classmethod
    def get_creation_service(cls) -> DiceBearForge:
        from .dicebear_forge import DiceBearForge

        return DiceBearForge()

    def fingerprint_payload(self) -> dict[str, Any]:
        """Exclude ignored source traits from rendering identity only."""
        return self.normalized_spec_payload(exclude={"ignored_traits"})


@on_adapt_media_spec.register(priority=Priority.NORMAL)
def adapt_portrait_spec(spec: PortraitSpec, ctx: dict[str, Any] | None = None) -> DiceBearSpec:
    """Compile one renderer-neutral portrait request into a local Lorelei request."""
    if spec.style_profile not in (None, "default"):
        raise ValueError(f"Unsupported portrait style profile {spec.style_profile!r}")

    definition_json = lorelei_definition_json()
    definition_hash = style_definition_hash(definition_json)
    traits = normalize_portrait_traits(spec.traits)
    options, ignored = map_lorelei_traits(traits)
    seed = derive_portrait_seed(
        identity_key=spec.identity_key,
        style_definition_hash=definition_hash,
        explicit_seed=spec.explicit_seed,
    )
    return DiceBearSpec(
        label=spec.label,
        style_definition_hash=definition_hash,
        seed=seed,
        options={"seed": seed, "size": 128, **options},
        ignored_traits=ignored,
    )


adapt_portrait_spec._behavior.wants_caller_kind = PortraitSpec
