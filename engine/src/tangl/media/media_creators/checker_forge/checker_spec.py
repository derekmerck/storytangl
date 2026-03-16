"""Typed spec for the deterministic checkerboard media harness."""

from __future__ import annotations

from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType


class CheckerSpec(MediaSpec):
    """Small raster spec used to exercise sync and async media generation."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.IMAGE

    color_a: str = "#000000"
    color_b: str = "#ffffff"
    tile_size: int = 32
    dims: tuple[int, int] = (256, 256)

    @classmethod
    def get_creation_service(cls) -> "CheckerForge":
        from .checker_forge import CheckerForge

        return CheckerForge()
