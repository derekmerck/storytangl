from __future__ import annotations
from typing import *
import io as _io
import re

import yaml
from panflute import *

from .ast_utils import md2ast

if TYPE_CHECKING:     # pragma: no cover
    from ast_node import AstNode as Node

RESERVED_KEYS = ['label', 'untree_as', 'ref', 'images', 'next', 'uid', "icon", "tags", 'cls']

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        # thanks to https://stackoverflow.com/a/72265455
        text_list = [line.rstrip() for line in data.splitlines()]
        fixed_data = "\n".join(text_list)
        return dumper.represent_scalar('tag:yaml.org,2002:str', fixed_data, style='|')
    elif len(data) > 100:  # check for long string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)

# to use with safe_dump:
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)

def untree(node: Node, doc=None):
    # `Untree` mangles a section-tree back into markdown format.  Data
    # and structure should be preserved through round trip transformation.
    #
    # See 'RESERVED_KEYS' for meta-metadata.  The meta field 'untree_as'
    # distinguishes ambiguities.

    doc = doc or Doc()
    meta = {k: v for k, v in node.meta.items() if k not in RESERVED_KEYS}
    for k, v in meta.items():
        if isinstance(v, str):
            v = re.sub("'", '"', v)
            meta[k] = v
        if isinstance(v, list):
            for i, vv in enumerate(v):
                try:
                    vv = re.sub("'", '"', vv)
                    meta[k][i] = vv
                except TypeError:
                    # not a sting
                    pass

    match node.meta.get('untree_as'):
        case "list":

            el = Plain()

            icon_ = node.meta.get('icon')
            if icon_:
                try:
                    icon = re.match( r'{{ ?ICON\.(\w+) ?}}', icon_).group(1)
                except AttributeError:
                    icon = icon_
                    # raise
                short_code = f":{icon.lower()}:"
                el.content += [ Str(short_code), Space ]

            label = node.meta.get('label', '')  # link to the same section
            ref = node.meta.get('ref', [node.meta.get('next', '')])
            if ref:
                if not isinstance(ref, list):
                    ref = [ref]
                if ref[0].find("/") < 0:
                    ref[0] = "#" + ref[0]
                else:
                    ref[0] = re.sub('/', "#", ref[0])
                    # ref[0] = re.sub('/[\w]', lambda match: f"#{match[0].upper()}", ref[0])
                ref[0] = re.sub("_", " ", ref[0])
                print( label, ref[0])
                content = Link(Str(label), url=ref[0])
            else:
                content = Str( label )
            el.content.append( content )
            if meta:
                v = yaml.dump(meta, default_flow_style=True)[:-1]
                el.content += [Space, Code(text=v)]

            tags = node.meta.get('tags', [])
            if tags:
                for tag in tags:
                    el.content += [Space, Str(f"#{tag}")]

            return el

        case _:

            if 'label' in node.meta:
                kwargs = {'level': node.depth}
                # identifier = node.meta.get('uid')
                # if identifier:
                #     kwargs['identifier'] = identifier
                # cls = node.meta.get('cls')
                # if cls:
                #     kwargs['classes'] = [cls]
                label = re.sub("_", " ", node.meta['label'])
                label = label.title()
                header = Header( Str(label), **kwargs )
                doc.content.append( header )

                tags = node.meta.get('tags', [])
                if tags:
                    content = []
                    for tag in tags:
                        content += [Str(f"#{tag}"), Space]
                    doc.content.append( Plain( *content[:-1] ) )


            if meta:
                if not doc.content:
                    doc.metadata = meta
                else:
                    doc.content.append( CodeBlock(text=yaml.safe_dump(meta), classes=['yaml']) )

                #     s += "---\n" + yaml_block + "...\n\n"
                # else:
                #     s += "```\n" + yaml_block + "```\n\n"

            for im in node.meta.get('images', []):
                el = Image(url=im)
                doc.content.append(Plain(el))

            if node.content:
                json_content = md2ast( node.content, as_json=True )
                doc_content = load(_io.StringIO(json_content))
                doc.content += doc_content.content

            list_children = []
            for child in node.children:
                if child.meta.get('untree_as') == "list":
                    list_children.append( ListItem( untree(child) ) )
                else:
                    untree(child, doc)
            if list_children:
                doc.content.append( BulletList( *list_children ) )

    return doc
