from __future__ import annotations
from typing import Type, Self
from functools import lru_cache
import logging


try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.WARNING)

class InheritanceAware:
    """
    Provides subclass and superclass introspection
    """

    @lru_cache(maxsize=None)
    @staticmethod
    def get_all_subclasses(cls) -> set[Type]:
        """
        Recursively get all subclasses of the class.
        """
        subclasses = set(cls.__subclasses__())
        for subclass in subclasses.copy():
            subclasses.update(subclass.get_all_subclasses(subclass))
        subclasses.add(cls)
        return subclasses

    def __init_subclass__(cls, **kwargs):  # consumes pydantic metaclass kwargs
        # Reset our cached subclass lookup tables
        cls.get_all_subclasses.cache_clear()
        super().__init_subclass__()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        # If the model uses pydantic, it calls this method instead of __init_subclass__
        cls.get_all_subclasses.cache_clear()
        super().__pydantic_init_subclass__(**kwargs)

    @classmethod
    def get_subclass_by_name(cls, cls_name: str) -> Type[Self]:
        """
        Get a subclass by its name, searching recursively through all subclasses.
        """
        subclasses_by_name_map = {subclass.__name__: subclass for subclass in cls.get_all_subclasses(cls)}
        return subclasses_by_name_map[cls_name]
