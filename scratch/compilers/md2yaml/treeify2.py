from collections import defaultdict
import urllib
import re

import yaml
from panflute import Doc, Header, Para, CodeBlock, BulletList, Code, \
    Str, Image, Link, Div, Plain, BlockQuote, HorizontalRule

from .ast_node import AstNode as Node

def treeify(doc: Doc):

    root = Node(meta=doc.get_metadata())
    current_node = root
    expect_new_node = False

    def handle_content( content ) -> tuple:
        content_res = []
        meta_res = defaultdict(list)
        if hasattr(content, "content"):
            # sometimes a container gets passed in
            content = content.content
        for item in content:
            if isinstance(item, Code):
                # grabs tags and inline yaml
                meta = yaml.safe_load( item.text )
                if 'tags' in meta:
                    meta_res['tags'].extend( meta.pop('tags') )
                meta_res.update( meta )
            elif isinstance(item, Str) and item.text.startswith("^"):
                # grabs ^identifiers
                meta_res['id'] = item.text[1:]
            elif isinstance(item, Image):
                meta_res['images'].append(
                    { 'url': urllib.parse.unquote( item.url ),
                      'caption': item.content,
                      **item.attributes } )
            elif isinstance(item, Link):
                meta_res['refs'].append(   (urllib.parse.unquote( item.url ),
                                            item.content,
                                            item.identifier,
                                            item.attributes) )

            else:
                content_res.append( item )
        return content_res, meta_res

    def handle_el( el ):
        nonlocal current_node, expect_new_node
        if isinstance(el, Header):
            node = Node()
            expect_new_node = False
            content, meta = handle_content(el.content)
            id = el.identifier
            id = re.sub(r'tags-[\w-]+$', "", id)  # attaches tags to identifier internally
            node.meta.update({
                **meta,
                'label': content,
                'id': meta.get('id') or id })
            if el.classes:
                # for headers, this is used to annotate node-type
                node.meta['classes'] = el.classes
            if el.level > current_node.depth:
                # it's a child node
                current_node.add_child( node )
            elif el.level == current_node.depth:
                # it's a peer node
                current_node.parent.add_child( node )
            else:
                # it's an uncle
                current_node.parent.parent.add_child( node )
            current_node = node
        elif isinstance(el, Para):
            if expect_new_node:
                # anonymous node
                node = Node(meta={'id': 'anon'})
                expect_new_node = False
                current_node.parent.add_child(node)
                current_node = node
            content, meta = handle_content(el.content)
            current_node.add_content(Para(*content))

            def update_extend( source, update ):
                for k, v in update.items():
                    if k not in source:
                        source[k] = v
                    elif isinstance(source[k], list):
                        source[k] += v
                    else:  # clobber! only req for overwriting default id field
                        source[k] = v

            update_extend( current_node.meta, meta )

        elif isinstance(el, Div):
            # admonitions are a blockquote wrapped with a div
            current_node.add_content(el)
        elif isinstance(el, CodeBlock):
            meta = yaml.safe_load( el.text )
            current_node.meta.update( meta )
        elif isinstance(el, HorizontalRule):
            expect_new_node = True
        elif isinstance(el, BulletList):
            for list_el in el.content:
                node = Node(untree_as='list')
                current_node.add_child(node)
                content, meta = handle_content(*list_el.content)
                node.add_content( content )
                node.meta.update( meta )
                try:
                    if node.render_content().startswith("\>"):
                        # force an anonymous node at the next paragraph
                        expect_new_node = True
                except:
                    pass
        else:
            print( el )
            raise TypeError("Unhandled block type")

    for el in doc.content:
        handle_el( el )

    return root
