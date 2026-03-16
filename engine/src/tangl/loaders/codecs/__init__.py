from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tangl.loaders.codec import CodecRegistry


def register_bundled_codecs(registry: "CodecRegistry") -> None:
    """Register bundled non-native story codecs."""
    from .twine import TwineCodec

    twine = TwineCodec()
    for alias in ("twine", "twee", "twee3", twine.codec_id):
        registry.register(alias, twine)
