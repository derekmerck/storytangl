from typing import ClassVar, Self
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from tangl.type_hints import UnstructuredData, UniqueLabel, Identifier
from ..entity import Entity
from ..registry import Registry


class Singleton(Entity):
    model_config = ConfigDict(frozen=True)
    label_: UniqueLabel = Field(..., alias="label")
    # Required now, must be unique within the class registry

    _instances: ClassVar[Registry[Self]] = Registry(label="singleton_instances")
    """
    A class-level registry of Singleton instances for this class.
    Each subclass gets its own registry instance.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        cls._instances = Registry[cls](label=f"{cls.__name__.lower()}_instances")

    @classmethod
    def get_instance(cls, key: Identifier) -> Self:
        # Generally we don't want to use UID b/c it's inconsistent between runs
        if isinstance(key, UUID):
            return cls._instances[key]
        elif isinstance(key, str):
            if key in [ i.label for i in cls._instances ]:
                return cls.find_instance(label=key)
        else:
            raise TypeError(f"{key} is not an instance of {cls.__name__}")

    @classmethod
    def has_instance(cls, key: Identifier) -> bool:
        # Generally we don't want to use UID b/c it's inconsistent between runs
        if isinstance(key, UUID):
            return key in cls._instances
        elif isinstance(key, str):
            return key in [ i.label for i in cls._instances ]
        else:
            raise TypeError(f"{key} is not an instance of {cls.__name__}")

    @classmethod
    def find_instance(cls, **criteria) -> Self:
        return cls._instances.find_one(**criteria)

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

    def __del__(self):
        self._instances.remove(self)

    @classmethod
    def structure(cls, data) -> Self:
        obj_cls = data.pop('obj_cls')
        label = data.pop('label')
        return obj_cls.get_instance(label)

    def unstructure(self) -> UnstructuredData:
        return UnstructuredData({'obj_cls': self.__class__, 'label': self.label})
