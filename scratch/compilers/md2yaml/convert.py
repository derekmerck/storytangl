import io

from panflute import Doc, load

from .ast_node import Node
from .ast_utils import md2ast, ast2md
from .treeify2 import treeify
from .untree import untree


def doc2tree( source: Doc | str, flat=True ) -> Node | dict:
    if isinstance(source, str):
        json_ast = md2ast(source, as_json=True)
        doc = load(io.StringIO(json_ast))
    elif isinstance(source, Doc):
        doc = source
    else:
        raise TypeError
    root = treeify(doc)
    # if isinstance(doc, str):
    #     json_ast = md2ast(doc, as_json=True)
    #     doc = load(io.StringIO(json_ast))
    # doc.root = Node()
    # doc.current = doc.root
    # root = treeify(doc)
    if flat:
        return root.to_dict()
    return root


def tree2doc( data: dict, flat=True ) -> Doc | str:

    node = Node( **data )
    doc = untree(node)
    if flat:
        return ast2md( doc, stand_alone=True )
    return doc