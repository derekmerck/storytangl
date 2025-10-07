import json
import re

import pypandoc as pandoc
from panflute import *

def doc2md( doc: Doc, stand_alone=False ):
    """Flatten Panflute Doc to md"""
    ast = doc.to_json()
    json_ast = json.dumps(ast)
    extra_args = []
    if stand_alone:
        extra_args.append('-s')
    extra_args.append('--wrap=none')
    res = pandoc.convert_text(json_ast, format='json', to='markdown', extra_args=extra_args)
    res = res[:-1]      # clip \n at end
    res = md2wiki(res)  # convert to wikilinks
    res = cls2admonition(res)  # convert divs back to admonitions
    # reformat bullet lists
    res = re.sub(r"\n-   ", r"\n  - ", res)
    # # reformat div bocks
    # res = re.sub(r"::: (\w+)\n(.+?)\n:::", r"\2\n{.\1}", res, flags=re.S)
    return res

def blocks2md( *blocks: Block, **kwargs ):
    """Convert Panflute Blocks to md"""
    if not blocks:
        return
    _blocks = []
    for block in blocks:
        if isinstance(block, ListContainer):
            block = Plain(*block)
        _blocks.append( block )

    doc = Doc( *_blocks )
    return doc2md(doc, **kwargs)


def ast2md( *items: Inline | Block | Doc, **kwargs ):
    """Convert Panflute Doc, Blocks, or Inlines to md"""
    if len(items) == 0:
        return None
    elif isinstance( items[0], Inline ):
        """Wrap inlines elems in a block and convert back to md"""
        item = Plain(*items)
        return blocks2md( item, **kwargs )
    elif isinstance(items[0], Doc):
        return doc2md( items[0], **kwargs )
    else:
        return blocks2md( *items, **kwargs )


def wiki2md(source: str):
    """Preprocess [[wikilinks]] into inline [md](links)"""
    wikilinks = re.compile(r"\[\[([^|\]]+)(\|(.[^]]*))?]]")

    def repl(match: re.Match):
        link = match.groups(1)[0]
        if isinstance( match.groups(1)[2], str ):
            label = match.groups(1)[2]
            return f"[{label}]({link})"
        else:
            return f"[]({link})"
            # label = link

    res = wikilinks.sub(repl, source)
    return res


def md2wiki(source: str):
    """Preprocess inline [md](links) into [[wikilinks]]"""
    md_links = re.compile(r"\[([^]]*)]\(([^)]*)\)")

    def repl(match: re.Match):
        link = match.groups(1)[1]
        if match.groups(1)[0]:
            label = match.groups(1)[0]
            return f"[[{link}|{label}]]"
        return f'[[{link}]]'

    res = md_links.sub(repl, source)
    return res

def shortcode2key(source: str):
    """Preprocess inline :shortcode: into `icon: shortcode`"""
    shortcodes = re.compile(r" :(\w+): ")
    res = shortcodes.sub(r' `icon: \1` ', source)
    return res

def tag2key(source: str):
    """Preprocess inline #tag/subtag into `tags: [tag/subtag]`"""
    tags = re.compile(r"(?:^|\s)#([\w/]+)")
    res = tags.sub(r'`tags: [\1]` ', source)
    return res

def admonition2cls(source: str):
    adm = re.compile(r"^> \[!([\w-]*)]\s*([^>]*?)\n(> .*?)\n(?=[^>]|$)", flags=re.S|re.M)

    def repl(match: re.Match):
        cls = match.groups(1)[0]
        content = match.groups(1)[2]
        if match.groups(1)[1]:
            label = match.groups(1)[1]
            return "::: {" + f".{cls} label='{label}'" + "}\n" + content + '\n:::\n'
        return f":::{cls}\n" + content + '\n:::\n'

    res = adm.sub(repl, source)
    return res

def cls2admonition(source: str):
    cls_obj = re.compile(
        r":::\s*((\{\.([\w-]+) label=\"([^}]+)\"})|(\w+))\n([\S\s]+?):::"
    )

    def repl(match: re.Match):
        if isinstance( match.groups(1)[2], str):
            cls = match.groups(1)[2]
            label = match.groups(1)[3]
        elif isinstance( match.groups(1)[4], str):
            cls = match.groups(1)[4]
            label = ""
        quote = match.groups(1)[5]

        return f"> [!{cls}] {label}\n{quote[:-1]}"

    source = cls_obj.sub(repl, source)
    return source

def discard_comments(source: str):
    multi_line_comment = re.compile( r"%%\n[^%]*\n%%" )
    source = multi_line_comment.sub( "", source )

    single_line_comment = re.compile( r"%%.*$" )
    source = single_line_comment.sub( "", source )
    return source

def md2ast(source: str, as_json=False) -> str | dict:
    """Convert a md string to abstract syntax tree"""

    source = wiki2md(source)          # replace wikilinks
    source = shortcode2key(source)    # replace icons w meta
    source = tag2key(source)          # replace tags w meta
    source = admonition2cls(source)   # replace > [!admonition]... with {.cls} >...
    source = discard_comments(source) # discard %% comments

    json_ast = pandoc.convert_text(source, format='markdown', to='json')
    if as_json:
        return json_ast
    ast = json.loads(json_ast)
    return ast
