from typing import ClassVar, Self

from pydantic import ConfigDict, Field, model_validator

from tangl.type_hints import UnstructuredData, UniqueLabel
from ..entity import Entity
from ..registry import Registry


class Singleton(Entity):
    model_config = ConfigDict(frozen=True)
    label: UniqueLabel = Field(...)  # Must be unique within the class registry

    _instances: ClassVar[Registry[Self]] = Registry(label="singleton_instances")
    """
    A class-level registry of Singleton instances for this class.
    Each subclass gets its own registry instance.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._instances = Registry[cls](label=f"{cls.__name__.lower()}_instances")

    @classmethod
    def get_instance(cls, label) -> Self:
        if label in [ i.label for i in cls._instances ]:
            return cls._instances.find_one(label=label)

    @classmethod
    def has_instance(cls, label) -> bool:
        return label in [ i.label for i in cls._instances ]

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()

    @classmethod
    def all_instances(cls):
        return cls._instances.all()

    @classmethod
    def all_instance_labels(cls):
        return cls._instances.all_labels()

    @classmethod
    def all_instance_tags(cls):
        return cls._instances.all_tags()

    @model_validator(mode="before")
    def _confirm_new(cls, data):
        label = data.get('label')
        if cls.has_instance(label):
            raise KeyError(f"Label {label} is already registered, 'get_instance' instead")
        return data

    @model_validator(mode="after")
    def _register_instance(self):
        # Ensures uniqueness contract is enforced at construction time
        if self not in self._instances:
            self._instances.add(self)
        return self

    def __reduce__(self):
        return self.get_instance, (self.label,)

    def __hash__(self):
        return hash((self.__class__, self.label),)

    @classmethod
    def structure(cls, data) -> Self:
        obj_cls = data.pop('obj_cls')
        label = data.pop('label')
        return obj_cls.get_instance(label=label)

    def unstructure(self) -> UnstructuredData:
        return UnstructuredData({'obj_cls': self.__class__, 'label': self.label})
