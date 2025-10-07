"""
More manageable document class
"""
from __future__ import annotations
from typing import *
from pprint import pformat
import re

import attr

from .statement import Statement

if TYPE_CHECKING:
    from stanza.models.common.doc import Document as StanzaDocument


@attr.define
class Document:
    statements: list[Statement] = attr.ib( factory=list )
    text: str = None
    entities: list[dict] = attr.ib( factory=list )

    def __attrs_post_init__(self):
        for s in self.statements:
            s.parent = self

    def iterwords(self) -> Iterator:
        for s in self.statements:
            for w in s.words:
                yield w

    def filter(self, func: Callable) -> Iterator:
        return filter( func, self.iterwords() )

    def render(self, ctx: dict = None, post: dict = None, **kwargs) -> str:
        ctx = ctx or {}
        ctx |= kwargs
        res = ""
        for s in self.statements:
            res += s.render(ctx)
            res += " "
        # spaces inside quotes and parens
        res = re.sub(r"\"( *)([^\"]+?)( *)\"", r'"\2"', res)
        res = re.sub(r"\(( *)([^\)]+?)( *)\)", r'(\2)', res)

        # post-processing touch ups
        post = post or {}
        for k, v in post.items():
            res = re.sub(k, v, res)

        return res[:-1] + "\n"

    @classmethod
    def from_stanza(cls: Document, doc: StanzaDocument):
        statements = []
        for s in doc.sentences:
            statements.append( Statement.from_stanza(sentence=s) )
        return cls( statements=statements, entities=doc.entities, text=doc.text )

    @classmethod
    def from_passage(cls: Document, passage: str, lemmas: dict = None):
        from scratch.lang import LexRef
        sdoc = LexRef.annotate(passage, lemmas)
        return Document.from_stanza(sdoc)

    def pretty_print(self):
        res = []
        for s in self.statements:
            res_ = []
            for i, w in enumerate(s.words):
                ww = w.as_dict() | {'id': i + 1}
                res_.append(ww)
            res.append( res_ )
        return pformat(res)

    def adopt_voice(self, voice: 'Voice', **kwargs):
        for w in self.iterwords():
            if voice.adopts.adopts_word(w):
                w.voice = voice

    def adopt_voices(self, *voices):
        for voice in voices:
            self.adopt_voice(voice)
