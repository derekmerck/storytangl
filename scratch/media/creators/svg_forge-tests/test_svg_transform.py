import pytest
from media.creators.svg_forge.svg_transform import SvgTransform

def test_translate():
    svg_transform = SvgTransform().translate(10, 20)
    assert str(svg_transform) == "translate(10 20)"


def test_scale():
    svg_transform = SvgTransform().scale(2)
    assert str(svg_transform) == "scale(2 2)"

    svg_transform = SvgTransform().scale(2, 3)
    assert str(svg_transform) == "scale(2 3)"

def test_chain():
    svg_transform = SvgTransform().translate(10, 20).scale(2)
    assert str(svg_transform) == "translate(10 20) scale(2 2)"
