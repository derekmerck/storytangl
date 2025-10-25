from __future__ import annotations

import types
from typing import *
from pprint import pformat

import attr

from tangl.lang.pos import TreeBankSymbols as TBS
from .word import Word

if TYPE_CHECKING:
    from .document import Document
    from stanza.models.common.doc import Sentence as StanzaSentence


@attr.define
class Statement:
    words: list[Word] = attr.ib( factory=list )
    text: str = None
    entities: list[dict] = None
    parent: Document = attr.ib( default=None, repr=False )

    def __attrs_post_init__(self):
        for w in self.words:
            w.parent = self
            if w.pov is not None and w.head.pov is not None:
                if "nsubj" in w.deprel and w.head.pov is not w.pov:
                    print(f"pov mismatch error: {w.head.text}/{w.head.pov} != {w.text}/{w.pov}")

    def render(self, ctx: dict = None) -> str:
        ctx = ctx or {}
        # print(self.text)
        res = ""
        for i, w in enumerate( self.words ):
            rendered = w.render(ctx)
            if len(res) == 0 or \
                    (w.symbol is TBS.PUNC and w.text not in "\"(") or \
                    rendered in ["n't", "'re", "'ll", "'m", "'s", "'d"] or \
                    res.endswith("-"):
                res += rendered
            else:
                res = res + " " + rendered
        res = res[0].upper() + res[1:]
        return res

    @classmethod
    def from_stanza(cls, sentence: StanzaSentence):
        words = []
        for w in sentence.to_dict():
            # dumb but word doesn't carry NER unless its dictified at the sentence level
            w = types.SimpleNamespace(**w)
            words.append(Word.from_stanza(w))
        return cls(words=words, text=sentence.text, entities=sentence.entities)

    def pretty_print(self):
        res = []
        for i, w in enumerate(self.words):
            ww = w.as_dict() | {'id': i+1}
            res.append(ww)
        return pformat(res)