"""Pillow-backed checkerboard generator for media pipeline tests."""

from __future__ import annotations

from PIL import Image, ImageColor, ImageDraw

from .checker_spec import CheckerSpec


def _parse_color(value: str) -> tuple[int, int, int]:
    """Coerce CSS-style or named colors into RGB tuples."""

    return ImageColor.getrgb(value.strip())


def make_checkerboard(
    color_a: str,
    color_b: str,
    *,
    tile_size: int,
    dims: tuple[int, int],
) -> Image.Image:
    """Return a raster checkerboard image with deterministic tile layout."""

    width, height = dims
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    color_one = _parse_color(color_a)
    color_two = _parse_color(color_b)
    cols = (width + tile_size - 1) // tile_size
    rows = (height + tile_size - 1) // tile_size

    for row in range(rows):
        for col in range(cols):
            fill = color_one if (row + col) % 2 == 0 else color_two
            x0 = col * tile_size
            y0 = row * tile_size
            x1 = min(x0 + tile_size, width)
            y1 = min(y0 + tile_size, height)
            draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=fill)

    return image


class CheckerForge:
    """Minimal sync creator that returns a PIL image plus the realized spec."""

    def create_media(self, spec: CheckerSpec) -> tuple[Image.Image, CheckerSpec]:
        image = make_checkerboard(
            spec.color_a,
            spec.color_b,
            tile_size=spec.tile_size,
            dims=spec.dims,
        )
        return image, spec
