import tempfile
import os
from pathlib import Path

import pytest
from lxml import etree

from media.creators.svg_forge.svg_source_manager import SvgSourceManager

def sample_svg_data() -> tuple[etree.Element, etree.Element]:
    root = etree.Element('svg', xmlns="http://www.w3.org/2000/svg")
    group = etree.SubElement(root, 'g', id='test_group')
    # Note this id is transformed using the label cleaner, so it's "test group" in src
    etree.SubElement(group, 'circle', cx='50', cy='50', r='10', fill='red')
    return root, group

@pytest.fixture
def sample_svg_fp() -> Path:
    root, group = sample_svg_data()
    # Create a simple svg file for testing
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as temp:
        res = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
        temp.write(res)
    yield temp.name
    os.remove(temp.name)
def tostring_without_ns(element):
    res = etree.tostring(element)
    res = res.replace(b'xmlns="http://www.w3.org/2000/svg" ', b'')
    res = res.replace(b"test_group", b"test group")
    return res
def test_svg_source_manager_from_file(sample_svg_fp):

    root, group = sample_svg_data()
    source_manager = SvgSourceManager.from_file(sample_svg_fp)

    # Test reading the created file
    assert source_manager.path == Path(sample_svg_fp)
    assert tostring_without_ns(source_manager.data) == tostring_without_ns(root)


def test_svg_source_manager_find1(sample_svg_fp):

    root, group = sample_svg_data()
    source_manager = SvgSourceManager.from_file(sample_svg_fp)

    # Test finding a group in the svg file
    found_group = source_manager.find('test_group')
    print(tostring_without_ns(found_group))
    print(tostring_without_ns(group))
    assert tostring_without_ns(found_group) == tostring_without_ns(group)

def test_svg_source_manager_find2():
    data = etree.ElementTree(etree.Element('svg'))
    sm = SvgSourceManager(path="dummy", data=data)
    assert sm.find("/") == data.getroot()
