from __future__ import annotations

import uuid
from typing import *
import itertools
from collections import UserDict, defaultdict, ChainMap
import random

import attr

from tangl.utils.singleton import Singleton
from tangl.utils.type_vars import Uid

@attr.define
class Voice:
    pov: str = None

    def has(self, val) -> bool:
        return True


@attr.define
class DynamicExpression(Singleton, UserDict):

    template: str = None
    words: dict[DynamicWord] = attr.ib( default=dict )

    def __call__(self, voice: Voice = None, context: dict = None): ...



@attr.define
class DynamicWord(Singleton, UserDict):
    """
    This is a typed synonym word-bank.
    """

    shuffle: bool = True

    def __init__(self, uid: Uid = None, shuffle: bool = True, **kwargs):
        UserDict.__init__(self, **kwargs)
        self.data = defaultdict(list, **self.data)
        self.__attrs_init__(uid=uid, shuffle=shuffle)

    def __ior__(self, other: Mapping) -> ChainMap[DynamicWord]:
        return ChainMap( self, other )

    def __call__(self, voice: Voice = None):
        if voice is None:
            words = list( itertools.chain( self.values() ) )
            if len( words ) > 1:
                return random.choice(words)
            return words[0]

        keys = list( filter( lambda x: not x.startswith("_"), self.keys() ) )
        if self.shuffle:
            random.shuffle(keys)

        for k in keys:
            if voice.has( k ):
                words = self[k] + self["_"]
                if len( words ) > 1:
                    random.choice( words )
                return words[0]

        words = self["__"]
        if len(words) > 1:
            random.choice(words)
        elif words:
            return words[0]
        else:
            raise ValueError("No matching or default words available!")
