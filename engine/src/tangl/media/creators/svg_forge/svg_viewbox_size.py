import re

Svg = str

def svg_viewbox_size(svg: Svg, scale: float = 2.0) -> tuple[int, int]:
    # Infer dimensions from the viewBox attribute
    viewBox_match = re.search(r'viewBox="(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"', svg)
    if viewBox_match:
        _, _, width, height = map(int, viewBox_match.groups())
        width *= scale
        height *= scale
        return (width, height)
