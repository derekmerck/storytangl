"""
singleton.py

This module provides a :class:`Singleton` base class for specialized
entities that should only ever have one instance per (sub)class label.
It extends :class:`~tangl.entity.Entity` with logic to maintain a
central :class:`~tangl.registry.Registry` of singletons keyed by label.
"""

from __future__ import annotations
from typing import ClassVar, Self, Any
import functools
import logging

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict, PrivateAttr

from tangl.type_hints import UniqueLabel, UnstructuredData
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from .entity import Entity
from .registry import Registry

logger = logging.getLogger(__name__)


class Singleton(Entity):
    """
    A base class for Tangl entities that must be unique within a given
    subclass, identified by a required ``label``. Each subclass has its
    own registry of instances, so that any attempt to create a second
    instance of the same label triggers an error.

    **Key Features**:
      - The :attr:`label` is required, ensuring each instance has a
        unique key.
      - A dedicated registry per subclass (see :meth:`__init_subclass__`)
        is used to store and retrieve singletons.
      - Instances are automatically registered during validation, enforcing
        uniqueness at construction time.

    **Behavior**:
      - ``model_config = ConfigDict(frozen=True)`` ensures immutability:
        fields cannot be changed after creation.
      - If an entity with the same label already exists, the constructor
        raises a :exc:`ValueError`.
    """

    model_config = ConfigDict(frozen=True)
    """
    Make the model immutable after instantiation.
    """

    _instances: ClassVar[Registry[Self]] = Registry[Self]()
    """
    A class-level registry of Singleton instances for this class.
    Each subclass gets its own registry instance.
    """

    def __new__(cls, label, **kwargs):
        if x := cls.get_instance(label):
            return x
        return super().__new__(cls)

    _initialized: bool = PrivateAttr(False)

    def __init__(self, label, **kwargs) -> None:
        # prevent init code from running again
        if hasattr(self, "__pydantic_private__") and self._initialized:
            return
        super().__init__(label=label, **kwargs)
        self._initialized = True

    def __hash__(self):
        """
        Define a custom hash function so Singleton instances can be
        used in sets or as dictionary keys. The hash is derived from
        the class type and the label.

        :return: The combined hash of (class, label).
        :rtype: int
        """
        return hash((self.__class__, self.label),)

    @classmethod
    def __init_subclass__(cls, isolate_registry: bool = True, **kwargs) -> None:
        """
        Intercepts subclass creation to optionally isolate the registry
        so each subclass tracks its own Singleton instances.

        :param isolate_registry: If True (default), a fresh registry is
                                 allocated for the subclass. If False,
                                 the subclass shares the parent's registry.
        :type isolate_registry: bool
        """
        super().__init_subclass__(**kwargs)
        if isolate_registry:
            # create a new registry for this subclass, otherwise `get_instance` refers to the super class
            cls._instances = Registry[Self]()

    label: UniqueLabel = Field(...)   # required now, must be unique w/in class
    """
    A required label that identifies this singleton. Must be unique
    within a given subclass registry.
    """

    # No longer relevant, since __new__ is idempotent
    # # noinspection PyNestedDecorators
    # @field_validator("label")
    # @classmethod
    # def _check_unique(cls, label_value: UniqueLabel):
    #     """
    #     Field validator that ensures no existing Singleton in this class
    #     has the same label. Raises :exc:`ValueError` if another instance
    #     is already registered under that label.
    #
    #     :param label_value: The proposed label for the new instance.
    #     :type label_value: str
    #     :raises ValueError: If the label is already registered for this class.
    #     :return: The validated label.
    #     :rtype: str
    #     """
    #     if cls.get_instance(label_value):
    #         raise ValueError(f"Instance {label_value} already registered.")
    #     return label_value

    @model_validator(mode="after")
    def _register_instance(self):
        """
        Model validator that adds this newly-created instance to the
        subclass's registry. Ensures the uniqueness contract is enforced
        at construction time.

        :return: This Singleton instance, for chaining.
        :rtype: Self
        """
        self._instances.add(self)
        return self

    @classmethod
    def get_instance(cls, label: UniqueLabel) -> Self:
        """
        Retrieve an existing Singleton instance (if any) by label.

        :param label: The label to look up.
        :type label: str
        :return: The existing instance if found, otherwise None.
        :rtype: Self | None
        """
        # todo: add a 'search_everywhere' flag to look in superclass and subclass registries
        return cls._instances.find_one(label=label)

    @classmethod
    def find_instance(cls, **criteria) -> Self:
        return cls._instances.find_one(**criteria)

    @classmethod
    def find_instances(cls, **criteria) -> list[Self]:
        return cls._instances.find(**criteria)

    @classmethod
    def all_instance_tags(cls):
        return cls._instances.all_tags()

    @classmethod
    def all_instance_labels(cls):
        return cls._instances.all_labels()

    @classmethod
    def clear_instances(cls):
        """
        Clear all instances from this class-level registry. Useful in
        testing contexts or to reset state.
        """
        cls._instances.clear()

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """
        Generate a minimal representation of this Singleton, including only
        ``obj_cls`` and ``label``.

        .. note::
           This method **does not** call or delegate to the base Pydantic
           ``model_dump`` method. Any ``*args`` or ``**kwargs`` are accepted
           only for interface compatibility; they have no effect on the output.

        :param args: Unused positional arguments, accepted for API consistency.
        :param kwargs: Unused keyword arguments, accepted for API consistency.
        :return: A dictionary containing ``obj_cls`` and ``label``.
        :rtype: dict[str, Any]

        Usage::
          >>> my_singleton = MySingletonClass(label="GLOBAL_SETTINGS")
          >>> my_singleton.model_dump()
          {"obj_cls": "MySingletonClass", "label": "GLOBAL_SETTINGS"}
        """
        return { 'obj_cls': self.__class__.__name__, 'label': self.label }

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        """
        Recreate a Singleton from the provided data. The ``label`` is
        used to look up the existing instance in the registry. If
        it does not exist, this method implicitly creates it—though
        typically a previously-registered instance is expected.

        :param data: The unstructured data containing at least ``obj_cls``
                     and ``label``.
        :type data: dict
        :return: The corresponding Singleton instance.
        :rtype: Self
        :raises KeyError: If ``label`` is missing from ``data``.
        :raises ValueError: If the specified subclass is not found.
        """
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        label = data.pop("label")  # this will throw a key error if it's not set properly
        this = obj_cls.get_instance(label)
        return this
