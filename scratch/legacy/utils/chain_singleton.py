"""
This was an interesting idea exploring chained instance inheritance
"""

from typing import ClassVar
from collections import UserDict

from pydantic import Field

from tangl.type_hints import UniqueLabel
from tangl.core.entity import Singleton as SingletonEntity


class SingletonMap(SingletonEntity, UserDict):

    data: dict = Field( default_factory=dict )


class ChainSingletonMap(SingletonMap):

    # No longer works like this, always uses a private sub-registry
    # _instances: ClassVar[dict] = SingletonMap._instances

    extends: list[UniqueLabel] = Field( default_factory=list )

    @property
    def _extends(self) -> list[SingletonMap]:
        return [self.get_instance(e) for e in self.extends]

    def __missing__(self, key):
        for ee in self._extends:
            val = ee.__getitem__(key)
            if val is not None:
                return val
        raise KeyError

    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError as e:
            try:
                return self.__getitem__(item)
            except KeyError:
                raise e

