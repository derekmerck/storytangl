# test_svg_forge.py

import pytest
from media.creators.svg_forge import VectorForge as SvgForge

from lxml import etree

@pytest.mark.skip(reason="old code")
def test_forge(tempfile):
    svg = SvgForge.from_file( TEST_RESOURCES / "test.svg" )
    print(etree.tostring(svg.root))

    svg_copy = svg.clone( groups = {'group1-image1': 'top-over'},
                          class_styles={'primary': {'fill': 'green'}} )
    print(etree.tostring(svg_copy))

    with tempfile.NamedTemporaryFile() as f:
        svg.dump( svg_copy, f.name )

    png = SvgForge.to_png( svg_copy )
    with tempfile.TemporaryFile() as f:
        f.write( png )

    match_html_color( "ablue l3r5 left" )
    match_html_color( "light blue l3r5 left" )
    match_html_color( "dogs and cats #123456 " )

    el = svg.find( "group1-image1" )
    print( etree.tostring( el ) )

    el = svg.mk_defs_el()

    print( etree.tostring( el ))

    print( svg.keys() )
