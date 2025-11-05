import logging
from typing import Callable
import re
from collections import defaultdict

from pydantic import ConfigDict, BaseModel, SkipValidation

from lxml import etree
from lxml.etree import _ElementTree, _Element, ElementTree, Element
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class SvgSourceManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    """Knows how to read an svg file, find shape groups, and clone them"""
    path: Path = None
    data: SkipValidation[_ElementTree]

    @classmethod
    def _load_svg(cls, path):
        parser = etree.XMLParser(resolve_entities=False)
        return etree.parse(path, parser=parser)

    @classmethod
    def clean_label(cls, label: str) -> str:
        label = label.lower()
        # Clean AI junk from id keys
        label = re.sub(r"_\d+_", "", label)
        # Decode encoded characters
        label = re.sub(r"_x2b_", "+", label)
        label = re.sub(r"_x2c_", ",", label)
        label = re.sub(r"_x2e_", "", label)
        label = re.sub(r"_x23_", "#", label)
        # Carefully replace underscores with spaces and then restore underscores
        label = re.sub(r"_x5f_", "@@", label)
        label = re.sub(r"_", " ", label)
        label = re.sub(r"@@", "_", label)

        return label
    @classmethod
    def clean_labels(cls, svg_root: Element):
        for element in svg_root.iter():
            if 'id' in element.attrib:
                element.attrib['id'] = cls.clean_label(element.attrib['id'])

    @classmethod
    def from_file(cls, path: Path, pre_processor: Callable[[etree.Element], etree.Element] = None):
        data = cls._load_svg(path)
        # unfortunately, impossible to cache parsed xml files :(
        cls.clean_labels(data)
        if pre_processor:
            data = pre_processor(data)
        instance = cls(path=path, data=data)
        return instance

    @property
    def nsmap(self):
        return self.data.getroot().nsmap

    @property
    def attrib(self):
        return self.data.getroot().attrib

    def find(self, path):
        if path == "/":
            # sometimes you just want the root...
            return self.data.getroot()
        if path.find("/") > 0:
            parts = path.split("/")
            el = self.data.getroot()
            for part in parts:
                part = self.clean_label(part)
                el = el.find(f"./svg:*[@id='{part}']", {'svg': 'http://www.w3.org/2000/svg'})
                if el is None:
                    raise KeyError(f"Can't find {part} in {el} ({path})")
            return el
        path = self.clean_label(path)
        return self.data.getroot().find(f".//svg:g[@id='{path}']", {'svg': 'http://www.w3.org/2000/svg'})

    def get_svg_structure(self) -> dict[str, list]:
        root = self.data.getroot()  # type: etree.Element
        # Iterate through top-level groups
        res = defaultdict(list)
        for top_level_group in root.findall('./{http://www.w3.org/2000/svg}g'):
            top_group_id = top_level_group.get('id')
            # if show:
            #     print(f"GroupName: {top_group_id}")
            # Iterate through second-level groups within each top-level group
            for child_group in top_level_group.findall('{http://www.w3.org/2000/svg}g') + \
                               top_level_group.findall('{http://www.w3.org/2000/svg}rect'):
                child_group_id = child_group.get('id')
                # if show:
                #     print(f"    ItemName: {child_group_id}")
                res[top_group_id].append(child_group_id)
        return dict(res)

    def get_svg_group_paths(self):
        structured = self.get_svg_structure()
        res = [ f"{k}.{vv}" for k, v in structured.items() for vv in v ]
        return res
