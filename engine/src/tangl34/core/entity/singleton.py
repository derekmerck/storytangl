from typing import ClassVar, Self

from pydantic import ConfigDict

from ..type_hints import UnstructuredData
from .entity import Entity
from .registry import Registry


class Singleton(Entity):

    model_config = ConfigDict(frozen=True)

    _instances: ClassVar[Registry[Self]] = dict()

    @classmethod
    def get_instance(cls, label) -> Entity:
        return next(*cls._instances.find_one(label=label))

    def __new__(cls, *, label: str = None, **kwargs):
        if cls.get_instance(label=label):
            raise RuntimeError("Use 'get_instance' instead")
        return super().__new__()

    def __reduce__(self):
        return self.get_instance, self.label

    @classmethod
    def structure(cls, data) -> Self:
        obj_cls = data.pop('obj_cls')
        label = data.pop('label')
        return obj_cls(label=label)

    def unstructure(self) -> UnstructuredData:
        return {'obj_cls': self.__class__, 'label': self.label}
