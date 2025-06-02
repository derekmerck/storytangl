import cairosvg
# may require patch surfaces.py:662 ->  except (SystemError, MemoryError):  # noqa

from .svg_viewbox_size import svg_viewbox_size

def render_svg(svg: str, dims: tuple[int, int] = None) -> bytes:

    if dims:
        png = cairosvg.svg2png(svg, output_width=dims[0], output_height=dims[1])
    else:
        png = cairosvg.svg2png( svg )

    return png
