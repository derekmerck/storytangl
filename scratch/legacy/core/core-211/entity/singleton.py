from __future__ import annotations
from typing import ClassVar, Optional, Self
import functools
from uuid import UUID
from importlib import resources
import logging

import yaml
from pydantic import BaseModel, model_validator, ConfigDict

from tangl.type_hints import UniqueLabel
from tangl.utils.uuid_for_secret import uuid_for_secret
from .entity import Entity
from .smart_new import SmartNewHandler

logger = logging.getLogger("tangl.singleton")

class SingletonEntity(Entity):
    """
    A base class for creating singleton entities.  Ensures that only one instance
    of each entity exists for a given label.

    Key Features:
        - get_instance(label): Returns an existing instance of the class by label
    """

    # model_config = ConfigDict(frozen=True)

    def __init_subclass__(cls, **kwargs):
        # Every subclass can manage its own instances. However, if you want to reuse a
        # super-classes instances, just set it in the class definition.
        if cls.__dict__.get("_instances") is None:
            cls._instances = dict()

    _instances: ClassVar[dict[UniqueLabel, SingletonEntity]] = dict()
    # base class has to init its own instances, bc it doesn't call its own __init_subclass__

    @classmethod
    def get_instance(cls, label: UniqueLabel) -> Self:
        """
        Retrieves an instance of the singleton entity by its label.

        :param label: The unique label of the entity to retrieve.
        :return: The instance of the singleton entity associated with the label.
        :raises KeyError: If no instance with the given label exists.
        """
        return cls._instances[label]

    @classmethod
    def clear_instances(cls):
        cls._instances.clear()

    # todo: this used to allow you to re-new singletons
    #       could move this into the meta-new like self-structuring as well...
    # def __new__(cls, label: UniqueLabel = None, **kwargs):
    #     if not label:
    #         # print( kwargs )
    #         raise ValueError(f"Singletons {cls} must have a unique label.")
    #     if label in cls._instances:
    #         logger.debug( "found self in _instances")
    #         return cls._instances[label]
    #     logger.debug('newing self normally')
    #     return super().__new__(cls)

    def __init__(self, label: UniqueLabel = None, **kwargs):
        """
        Initializes the singleton entity.

        If the entity is already registered, this method does nothing and does not re-initialize
        """
        if not label:
            raise ValueError("Singletons must have a unique label.")
        if label in self._instances:
            # Not new, do not reinitialize
            return
        self._instances[label] = self
        super().__init__(label=label, **kwargs)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs):
        return {
            'obj_cls': self.__class__.__name__,
            'label': self.label
        }

    def __reduce__(self) -> tuple:
        """
        Singleton entities can be pickled by reference since they are immutable
        with respect to their public interface.

        :returns: tuple: The class and label of the entity, used for reconstructing the instance when unpickling.
        """
        return self.__class__.get_instance, (self.label,)

    uid_: Optional[UUID] = None  # Don't need to generate a uid

    @functools.cached_property
    def uid(self) -> UUID:
        return uuid_for_secret(str(self._secret))

    @property
    def _secret(self):
        return self.__class__, self.label

    def __hash__(self):
        return hash(self._secret)

    @classmethod
    def load_instances(cls, data: dict):
        for label, kwargs in data.items():
            cls(label=label, **kwargs)

    @classmethod
    def load_instances_from_yaml(cls, resources_module: str, fn: str):
        with resources.open_text(resources_module, fn) as f:
            data = yaml.safe_load(f)
        cls.load_instances(data)

    @SmartNewHandler.normalize_class_strategy
    def _normalize_singleton_cls(base_cls, label: UniqueLabel = None, **kwargs):
        """
        Either creates a new instance or returns an existing one based on the provided label.

        Args:
            label (NodeLabel): The label used to identify the entity instance.

        Returns:
            SingletonEntity: An existing instance of the singleton entity or None
        """
        if not label:
            raise ValueError("Singleton's require a unique label parameter")
        if label in base_cls._instances:
            return base_cls.get_instance(label)
