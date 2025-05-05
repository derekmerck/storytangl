from __future__ import annotations
import dataclasses
from typing import Optional

from .svg_transform import SvgTransform
from lxml import etree

@dataclasses.dataclass
class LayeredElement:
    layer: int = 0
    data: etree._Element = None

@dataclasses.dataclass
class SvgGroup:
    id: str = None
    layer: int = 0
    transform: Optional[SvgTransform] = None

    els: list[ LayeredElement ] = dataclasses.field(default_factory=list)

    def add(self, el: etree._Element ):
        self.els.append( LayeredElement(data=el) )

    def to_el(self):
        root = etree.Element('g', transform=str(self.transform)) if self.transform else etree.Element('g')
        self.els.sort(key=lambda g: g.layer)
        for el in self.els:
            root.append(el.data)
        return root

# class SvgDesc:
#     #: [group1, group2-image1, ...] or {'group1': 'renamed_group', ...}
#     groups: list | dict = attr.ib(default=None)
#     #: { primary: {fill: blue}, ...}
#     class_styles: dict = attr.ib(factory=dict)
#     #: shapes to _hide_ initially (use shape original name)
#     hidden: list = attr.ib(factory=list)
#     #: _relative_ object scale, mostly for multi-desc renderings
#     scale: float = attr.ib(default=1.0)
#     #: override bg color if managing root
#     bgcolor: str = None

