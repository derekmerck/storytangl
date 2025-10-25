import warnings
import urllib

import yaml
from panflute import *

from .ast_node import AstNode as Node


HorizontalSpaces = (Space, LineBreak, SoftBreak)
VerticalSpaces = (Para, )
# elements that are parsed into other forms

Ignore = (Citation, DefinitionList, BulletList, Code, CodeBlock, Header)


def treeify(doc):
    # `Treeify` rips data from a simple md-based format and restructures it as
    # a tree based on sections and list items.

    def handle_meta(el: Element | dict, tree):
        try:
            if hasattr(el, 'text'):
                meta = yaml.safe_load(el.text)
            elif isinstance(el, dict):
                meta = el
            else:
                raise
        except TypeError as e:
            warnings.warn(f"Tried to parse meta {el} but failed")
            print(e)

        for k, v in meta.items():
            if k in tree.meta and isinstance(tree.meta[k], list) and isinstance(v, list):
                tree.meta[k].extend( v )
            else:
                if k in tree.meta:
                    print(f'clobbering meta {k}')
                tree.meta[k] = v

    def handle_element(el, tree):
        if isinstance(el, Code):
            handle_meta(el, tree)
            return
        elif isinstance(el, Image):
            key = Node._render_ast(el.content)
            value = urllib.parse.unquote( el.url )
            meta = {'images': {key: value}}
            handle_meta(meta, tree)
            # if 'images' not in tree.meta:
            #     tree.meta['images'] = [el.url]
            # else:
            #     tree.meta['images'].append( el.url )
            # tree.add_content(el.content)
            return
        elif isinstance(el, Link):
            # links in meta are references to other trees
            key = Node._render_ast(el.content)
            value = urllib.parse.unquote( el.url )
            meta = {'links': {key: value}}
            handle_meta(meta, tree)
            # if 'ref' not in tree.meta:
            #     tree.meta['ref'] = [el.url]
            # else:
            #     tree.meta['ref'].append( el.url )
            # tree.add_content(el.content)
            return
        return el

    def handle_content(content, tree) -> list[Block|Element]:
        _content = []
        for el in content:
            if isinstance(el, Block):
                _item = handle_block(el, tree)
            elif isinstance(el, Element):
                _item = handle_element(el, tree)
            else:
                raise RuntimeError
            if _item:
                _content.append(_item)
        return _content

    def handle_block(el, tree):

        if isinstance(el, (Para, Plain, BlockQuote, Div)):
            _content = handle_content(el.content, tree)
            el.content = _content
            return el

        elif isinstance(el, CodeBlock):
            # code blocks are assumed to be yaml format variables
            handle_meta(el, tree)

    root = Node(meta=doc.get_metadata())
    tree = root

    # Top level is the _only place_ sections will need to be parsed out,
    # so this processing doesn't need to recurse.
    for el in doc.content:

        if isinstance(el, Header):
            node = Node()
            _content = handle_content(el.content, tree)
            node.meta['label'] = _content
            if el.level == tree.depth:
                # sibling
                tree.parent.add_child(node)
            elif el.level > tree.depth:
                # child
                tree.add_child(node)
            elif el.level < tree.depth:
                # uncle
                tree.parent.parent.add_child(node)
            tree = node

        elif isinstance(el, BulletList):
            _current = tree
            for item in el.content:
                node = Node(untree_as='list')
                tree.add_child(node)
                _content = handle_content(item.content, node)
                node.add_content( _content )

        elif isinstance(el, Block):
            block = handle_block(el, tree)
            if block:
                tree.add_content(block)

        else:
            print( el )
            raise RuntimeError

    return root

