from __future__ import annotations
from typing import Self, ClassVar

from pydantic import Field
from sphinx_markdown_builder.contexts import UniqueString

from tangl.type_hints import UnstructuredData
from .entity import Structurable
from .collection import Registry

class Singleton(Structurable):
    # More than anything this is a serialization strategy for persisting
    # objects that carry unserializable runtime behaviors.

    _instances: Registry[Singleton] = Field(default_factory=Registry)

    @classmethod
    def get_instance(cls, label) -> Singleton:
        return cls._instances[label]

    @classmethod
    def structure(cls, data: UnstructuredData):
        cls_ = data.pop('kind')  # type: Self
        label = data.pop('label')
        return cls_.get_instance(label)

    def unstructure(self) -> UnstructuredData:
        return {'kind': self.__class__, 'label': self.label}


class Token(Structurable):
    ref_kind: ClassVar[Singleton]
    ref_label: UniqueString