from typing import ClassVar, Self
from dataclasses import dataclass

from ..entity import Entity
from .scope_mixin import ScopeMixin

@dataclass(kw_only=True)
class GlobalScope(ScopeMixin, Entity):

    # Singleton
    instance: ClassVar = None

    @classmethod
    def get_instance(cls) -> Self:
        if not cls.instance:
            cls.instance = cls()
        return cls.instance

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls.instance is not None:
            raise RuntimeError()
        return super().__new__(cls)

    # # For domains / global scope, expose locals as r/o globals
    # @property
    # def globals(self) -> StringMap:
    #     return self.locals    # alias, purely semantic
