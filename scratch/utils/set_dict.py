from collections import defaultdict
import random
from enum import Enum

class SetDict(defaultdict):
    """
    A dictionary that stores values as sets.

    Provides a built-in `choice` function that returns a random entry from the set.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(set)
        # Manually handle initial items to ensure they are cast to sets
        for key, value in dict(*args, **kwargs).items():
            self[key] = value
    def choice(self, key) -> str | None:
        res = self[key]  # type: set
        return random.choice(list(res)) if res else None

    def __setitem__(self, key, value):
        if not isinstance(value, set):
            if isinstance(value, str):
                value = {value}
            elif isinstance(value, list):
                value = {*value}
            else:
                raise ValueError(f"Cannot cast {value} to a set")
        super().__setitem__(key, value)

    def __reduce__(self):
        # Provide the information needed to reconstruct the object
        return self.__class__, (), self.__dict__, None, iter(self.items())

class EnumTranslatingMapping:
    """
    A mapping with enum'd keys.
    """

    def _k(self, key: str | Enum):
        if isinstance(key, Enum):
            key = key.value
        if isinstance(key, str):
            key = key.lower()
        return key

    def __contains__(self, key):
        return super().__contains__(self._k(key))

    def __getitem__(self, key) -> str:
        return super().__getitem__(self._k(key))

    def __setitem__(self, key, value):
        return super().__setitem__(self._k(key), value)

class EnumdSetDict(EnumTranslatingMapping, SetDict):
    ...
