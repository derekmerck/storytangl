from __future__ import annotations
from typing import *
from pprint import pformat
import re

import attr

from tangl.lang.pos import TreeBankSymbols as TBS
from tangl.lang.pronoun import Pronoun, PoV, PT, Gens

if TYPE_CHECKING:
    from tangl.narrator.voice import Voice
    from stanza.models.common.doc import Word as StanzaWord

@attr.define
class Word:

    text: str = None    # original word from text
    lemma: str = None   # word stem
    symbol: TBS = attr.ib(default=None,
                          converter=TBS,
                          validator=attr.validators.instance_of(TBS))  # treebank symbol tag

    plural: bool = False
    person: int = 3
    deprel: str = None
    poss: bool = None

    @property
    def pov(self):
        if self.symbol in [TBS.PRP5, TBS.PRP]:
            try:
                return Pronoun.pov_of(self.text)
            except ValueError:
                print("Inconclusive pronoun pov!")
                raise

        if self.symbol in [TBS.VBD, TBS.VBP]:
            # pov = LexRef.deconjugate(self.lemma, self.text)
            # print( self.lemma, self.text, pov )
            # don't need to deconjugate everything
            if self.text.lower() in ['were', 'are']:
                self.plural = True

        if self.person is not None and self.plural is not None:
            return Pronoun.PoV((self.person, self.plural))

        return None

    @property
    def pt(self):
        if self.symbol is TBS.PRP5:
            return PT.PA
        elif self.symbol is TBS.PRP:
            try:
                return Pronoun.type_of(self.text)
            except ValueError:
                print("Inconclusive pronoun type!")
                raise
        if self.symbol.is_noun():
            if re.findall("nsubj", self.deprel):
                return PT.S
            elif re.findall("obj|iobj|obl", self.deprel):
                return PT.O
            elif re.findall("nmod", self.deprel):
                return PT.PA

    @property
    def gens(self):
        if self.symbol in [TBS.PRP, TBS.PRP5]:
            try:
                return Pronoun.gender_of(self.lemma)
            except ValueError:
                pass
        return Gens.X_

    _head: int = None
    @property
    def head(self) -> Word | int:
        if self.parent:
            return self.parent.words[self._head-1]
        return self._head

    ner: str = None
    span: tuple[int, int] = None

    parent: 'Statement' = attr.ib(default=None, repr=False)

    _voice: 'Voice' = None   # managing Voice

    @property
    def voice(self):
        from tangl.narrator.voice import Voice
        if self._voice is not None:
            return self._voice
        elif self.pov is not None:
            return Voice(pov=self.pov, gens=self.gens)

    @voice.setter
    def voice(self, value: 'Voice'):
        self._voice = value

    def render(self, ctx: dict = None):
        ctx = ctx or {}
        if self.text == "\"":
            ctx["quoted"] = not ctx.get("quoted", False)
        if self.voice and not ctx.get("quoted", False):
            return self.voice.render_word(self, ctx)
        elif self.voice and self.symbol is TBS.NNP:
            return self.voice.render_word(self, ctx)
        else:
            return self.text


    @classmethod
    def from_stanza(cls, word: StanzaWord):

        plur = None
        person = None
        poss = None
        if hasattr(word, 'feats') and word.feats:
            if word.feats.find("Plur") >= 0:
                plur = True
            elif word.feats.find("Sing") >= 0:
                plur = False
            match = re.search(r"Person=(\d)", word.feats)
            if match:
                person = int( match[1] )
            match = re.search(r"Poss=(Yes|No)", word.feats)
            if match:
                poss = bool( match[1] )
        if "poss" in word.deprel:
            poss = True

        try:
            symbol = TBS(word.xpos)
        except ValueError:
            if word.deprel == "punct" or word.upos.lower() == "punct":
                symbol = TBS.PUNC
            else:
                print( word )
                raise ValueError("Unable to assign symbol!")
                symbol = None

        if word.ner != 'O':
            ner = word.ner
        else:
            ner = None

        span = (word.start_char, word.end_char)

        kwargs = {
            'text': word.text,
            'lemma': word.lemma,
            'symbol': symbol,
            'plural': plur,
            'person': person,
            'head': word.head,
            'deprel': word.deprel,
            'span': span,
            'poss': poss,
            'ner': ner
        }

        res = cls(**kwargs)
        return res

    def as_dict(self) -> dict:
        from tangl.utils.attrs import as_dict as _as_dict
        res = _as_dict(self)
        for prop in ['pt', 'pov', 'gens']:
            # print( getattr(self, prop) )
            val = getattr(self, prop)
            if val is not None:
                res[prop] = val
        res['rendered'] = self.render()
        return res

    def pretty_print(self) -> str:
        res = self.as_dict()
        return pformat(res)

