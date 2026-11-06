"""Registered region masks and opaque foreground coverage."""
from io import BytesIO
import os

from lxml import etree
from PIL import Image
import pytest

from tangl.media.media_creators.svg_forge.region_mask import region_mask_svg
from tangl.media.media_creators.svg_forge.render_playwright import render_svg


SOURCE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <defs><clipPath id="clip"><rect width="10" height="10"/></clipPath></defs>
  <g id="rear" transform="translate(1 0)" clip-path="url(#clip)"><rect width="8" height="10" fill="red"/></g>
  <g id="front"><rect x="4" width="4" height="10" fill="blue"/></g>
  <g id="occluder"><rect x="3" width="1" height="10" fill="green"/>
    <g fill="none"><rect id="unpainted" x="2" width="1" height="10"/></g></g>
</svg>'''
REGIONS = {"back": ("rear",), "front": ("front",)}


def test_explicit_targets_keep_order_registration_and_transforms() -> None:
    result = region_mask_svg(SOURCE, regions=REGIONS, occluders=("occluder",), region="back")
    root = etree.fromstring(result.encode())
    assert root.get("viewBox") == "0 0 10 10"
    assert [x.get("id") for x in root if x.get("id")] == ["rear", "front", "occluder"]
    assert root.xpath("//*[@id='rear']")[0].get("transform") == "translate(1 0)"
    assert root.xpath("//*[@id='rear']")[0].get("clip-path") == "url(#clip)"
    assert root.xpath("//*[@id='clip']")
    assert "fill:white" in root.xpath("//*[@id='rear']/*")[0].get("style")
    assert "fill:black" in root.xpath("//*[@id='occluder']/*")[0].get("style")
    assert root.xpath("//*[@id='unpainted']")[0].get("style") == "display:none"
    with pytest.raises(ValueError, match="Missing region coverage"):
        region_mask_svg(SOURCE, regions={"missing": ()}, occluders=(), region="missing")
    with pytest.raises(ValueError, match="must be distinct"):
        region_mask_svg(SOURCE, regions=REGIONS, occluders=("rear",), region="back")


@pytest.mark.skipif(os.environ.get("STORYTANGL_TEST_SVG_BROWSER") != "1",
                    reason="optional Chromium region witness")
def test_real_overlap_and_palette_independence() -> None:
    def mask(source, regions=REGIONS):
        value = region_mask_svg(source, regions=regions, occluders=("occluder",), region="back")
        return Image.open(BytesIO(render_svg(value, (20, 10)))).convert("RGBA")
    image = mask(SOURCE)
    assert image.getpixel((0, 5))[3] == 0
    assert image.getpixel((7, 5)) == (255, 255, 255, 255)
    assert image.getpixel((8, 5)) == (0, 0, 0, 255)
    assert image.getpixel((10, 5)) == (0, 0, 0, 255)
    assert list(image.getdata()) == list(mask(SOURCE.replace("red", "yellow").replace("blue", "pink")).getdata())
    assert list(image.getdata()) != list(mask(SOURCE.replace('x="4"', 'x="3"')).getdata())
    assert list(image.getdata()) != list(mask(SOURCE, {"back": ("front",), "front": ("rear",)}).getdata())
