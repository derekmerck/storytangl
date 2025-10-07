from panflute import *
import re

from .node import Node
from .ast_utils import ast2md, stringify

USE_STRINGIFY = False
# stringify is only useful for quick previews, it does not preserve any formatting


class AstNode(Node):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.content is None:
            self.content = []

    def add_content(self, el: Element | list[Element] ):
        if isinstance(el, (list, ListContainer)):
            self.content.extend(el)
        elif el:
            self.content.append(el)

    @classmethod
    def _render_ast(cls, elems, newlines=True):
        if not elems:
            return
        if USE_STRINGIFY:
            res = ""
            for el in elems:
                res += stringify(el, newlines=newlines)
        else:
            res = ast2md(*elems)
        res = re.sub(r"\\([<>$.])", r"\1", res)
        return res

    def render_content(self) -> str:
        if self.content:
            return self._render_ast(self.content)

    def render_meta(self) -> dict[str, str]:

        def recursive_render_item(item, keep_no_val: bool = False):

            def is_ast(value):
                return isinstance(value, (list, ListContainer)) and \
                    len(value) and \
                    isinstance(value[0], (Element, Block, ListContainer))

            if is_ast(item):
                wrapped = ListContainer( *item )
                item = self._render_ast(wrapped, newlines=False)

            elif isinstance(item, list | tuple ):
                item_ = [ recursive_render_item(v, keep_no_val) for v in item if v or keep_no_val]
                if isinstance(item, tuple):
                    item = tuple(item_)
                else:
                    item = item_

            elif isinstance(item, dict):
                # This discards any None or 0 value data, which we _want_ for locals
                # item = { k: recursive_render_item(v) for k, v in item.items() if v }
                # Want to keep vals if we are recursing in "locals" (or anywhere that
                # respects explicit fields) b/c need to initialize val=0 for eval.
                item = { k: recursive_render_item(v, keep_no_val or k == "locals") for k, v in item.items() if v or keep_no_val }
            try:
                item = item.strip()  # remove trailing \n's in meta values
            except AttributeError:
                pass
            return item

        meta = recursive_render_item( self.meta )
        return meta
