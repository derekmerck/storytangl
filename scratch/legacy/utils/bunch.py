from typing import *
from collections import UserDict


class Bunch(UserDict):
    """Creates dict ns with upper and lower keys for each key"""

    aliases = {}

    def __init__(self, adict):
        super().__init__(adict)
        self.__dict__.update(self.data)

    @classmethod
    def keys_for(cls, key):
        res = []
        if hasattr(key, "lower") and hasattr(key, "upper"):
            res.append( key.lower() )
            res.append( key.upper() )
        return res

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        for k in self.keys_for(key):
            self.data[k] = self.data[key]
            if k in self.aliases:
                aliases = self.aliases.get(k)
                for a in aliases:
                    for kk in self.keys_for(a):
                        self.data[kk] = self.data[key]


class Spans(Bunch):

    aliases = {
        "player": ["p", "pov"],
        "guy": ["guy0", "guy1", "guy2", "guy3", "guy4"],
        "girl": ["girl0", "girl1", "girl2", "girl3", "girl4"],
    }

    def __setitem__(self, key, value):
        value_ = f"<span style='color:{value}'>"
        super().__setitem__(key, value_)

    def FOR(self, el):
        if hasattr(el, "text_color"):
            value = el.text_color
            return self.s( value )

    @property
    def END(self):
        return "</span>"

    END_S = END

    @classmethod
    def s(cls, value):
        s = f"<span style='color:{value}'>"
        return s

