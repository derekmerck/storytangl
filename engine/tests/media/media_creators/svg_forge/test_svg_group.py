
from tangl.media.media_creators.svg_forge.svg_group import SvgGroup, SvgTransform

from lxml import etree

def test_SvgGroup_to_el():
    group = SvgGroup(transform=SvgTransform().translate(10, 20))
    group.add(etree.Element('path'))
    el = group.to_el()
    assert el.tag == 'g'
    assert el.attrib['transform'] == "translate(10 20)"
    assert len(el) == 1  # one child
