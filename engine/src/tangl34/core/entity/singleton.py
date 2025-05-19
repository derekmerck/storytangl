from typing import ClassVar, Self

from pydantic import ConfigDict, Field

from ..type_hints import UnstructuredData
from .entity import Entity
from .registry import Registry


class Singleton(Entity):

    model_config = ConfigDict(frozen=True)

    label: str = Field(...)

    _instances: ClassVar[Registry[Self]]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._instances = Registry[cls](label=f"{cls.__name__}_instances")

    @classmethod
    def get_instance(cls, label) -> Entity:
        if label in [ i.label for i in cls._instances ]:
            return next(*cls._instances.find_one(label=label))

    def __new__(cls, *, label: str, **kwargs):
        if cls.get_instance(label=label):
            raise RuntimeError("Use 'get_instance' instead")
        return super().__new__(cls)

    def __reduce__(self):
        return self.get_instance, self.label

    @classmethod
    def structure(cls, data) -> Self:
        obj_cls = data.pop('obj_cls')
        label = data.pop('label')
        return obj_cls(label=label)

    def unstructure(self) -> UnstructuredData:
        return {'obj_cls': self.__class__, 'label': self.label}
