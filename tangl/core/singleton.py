from __future__ import annotations
from typing import ClassVar, Self, Any
import functools
import logging

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict

from tangl.type_hints import UniqueLabel, UnstructuredData
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from .entity import Entity
from .registry import Registry

logger = logging.getLogger(__name__)


class Singleton(Entity):

    model_config = ConfigDict(frozen=True)

    _instances: ClassVar[Registry[Self]] = Registry[Self]()

    def __hash__(self):
        return hash((self.__class__, self.label),)

    @classmethod
    def __init_subclass__(cls, isolate_registry: bool = True, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if isolate_registry:
            # create a new registry for this subclass, otherwise `get_instance` refers to the super class
            cls._instances = Registry[Self]()

    label: UniqueLabel = Field(...)   # required now, must be unique w/in class

    @field_validator("label")
    @classmethod
    def check_unique(cls, label_value: str):
        if cls.get_instance(label_value):
            raise ValueError(f"Instance {label_value} already registered.")
        return label_value

    @model_validator(mode="after")
    def register_instance(self):
        # This will raise value error if it already exists, but we check that explicitly as well
        self._instances.add(self)

    @classmethod
    def get_instance(cls, label: str) -> Self:
        # We don't want to get by uid, want to get by label
        # todo: add a 'search_everywhere' flag to look in superclass and subclass registries
        return cls._instances.find_one(label=label)

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        # singletons can structure from class and label alone
        return { 'obj_cls': self.__class__.__name__, 'label': self.label }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        label = data.pop("label")  # this will throw a key error if it's not set properly
        this = obj_cls.get_instance(label)
        return this
