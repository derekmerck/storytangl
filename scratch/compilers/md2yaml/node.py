from __future__ import annotations
from typing import *
from pprint import pformat
import yaml


class Node:
    # Base node class for tree data structure
    def __init__(self,
                 content: Any = None,
                 meta: dict[str, Any] = None,
                 children: list['Node'] = None,
                 parent: Node = None,
                 **kwargs):

        self.content = content
        self.meta = kwargs | (meta or {})

        children = children or []
        self.children = [ self.__class__(**child, parent=self) for child in children ]

        self.parent = parent

    @property
    def root(self):
        this = self
        while this.parent is not None:
            this = this.parent
        return this

    @property
    def depth(self):
        depth = 0
        this = self
        while this.parent is not None:
            depth += 1
            this = this.parent
        return depth

    def add_child(self, node):
        node.parent = self
        self.children.append( node )

    def add_content(self, el):
        self.content += el

    def render_content(self) -> str:
        # hook for subclasses
        return self.content

    def render_meta(self) -> dict[str, Any]:
        # hook for subclasses
        return self.meta

    def to_dict(self) -> dict:

        res = {'content': self.render_content(),
               'meta': self.render_meta(),
               'children': [c.to_dict() for c in self.children]}
        # remove null params
        res = { k: v for k, v in res.items() if v }
        return res

    def to_yaml(self) -> str:
        data = self.to_dict()
        res = yaml.dump(data, sort_keys=False)
        return res

    def __repr__(self):
        return pformat( self.to_dict(), sort_dicts=False, width=100 )
