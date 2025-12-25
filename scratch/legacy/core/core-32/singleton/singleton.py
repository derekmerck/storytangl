"""
singleton.py

This module provides a :class:`Singleton` base class for specialized
entities that should only ever have one instance per (sub)class label.
It extends :class:`~tangl.entity.Entity` with logic to maintain a
central :class:`~tangl.registry.Registry` of singletons keyed by label.
"""

from __future__ import annotations
from typing import ClassVar, Self, Any, Iterable
import functools
import logging

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict, PrivateAttr

from tangl.type_hints import UniqueLabel, UnstructuredData
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from tangl.core import Entity, Registry

logger = logging.getLogger(__name__)


class Singleton(Entity):
    """
    Singleton is a base mixin class for creating unique, reference-based entities in StoryTangl.
    It ensures that only one instance exists per unique label within each subclass hierarchy.

    Key Features
    ------------
    * **Unique Instances**: Only one instance exists for each label within a class.
    * **Hierarchical Registry**: Each subclass maintains its own registry of instances.
    * **Reference-based Access**: Instances are retrieved by label rather than constructed.
    * **Instance Management**: Methods to add, remove, or clear instances.

    Usage
    -----
    .. code-block:: python

        from tangl.core import Singleton

        class MyConstant(Singleton):
            value: int = 0

        # Create an instance
        const1 = MyConstant(label="CONST_1", value=42)

        # Later, retrieve the same instance
        const1_again = MyConstant.get_instance("CONST_1")

        # Or automatically retrieve when trying to create with the same label
        same_const = MyConstant(label="CONST_1", value=100)  # Returns existing instance
        print(const1 is same_const)  # True
        print(same_const.value)      # 42 (original value preserved)

    Advanced Features
    ----------------
    * **Subclass Searching**: Find instances across the hierarchy with `search_subclasses=True`.
    * **Instance Creation**: Create instances on-demand with `create=True`.
    * **Instance Management**: Remove instances with `discard_instance` or clear all with `clear_instances`.
    * **Bulk Loading**: Initialize multiple instances from data structures or YAML files.

    Implementation Notes
    -------------------
    * Each subclass maintains its own instance registry to avoid cross-contamination.
    * Singleton instances are pickle-able and can be safely serialized.
    * Labels must be unique within a class; attempting to create a duplicate returns the existing instance.

    Related Components
    -----------------
    * :class:`~tangl.core.entity.SingletonEntity`: Combines Singleton with Entity for immutable reference concepts.
    * :class:`~tangl.core.entity.InheritingSingleton`: Singleton with inheritance from other instances.
    * :class:`~tangl.core.graph.Token`: Wrapper for using Singletons in a graph structure.
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

    # No longer relevant, since __new__ is now idempotent
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
        if self not in self._instances:
            self._instances.add(self)
        return self

    @classmethod
    def get_instance(cls, label: UniqueLabel, search_subclasses: bool = False) -> Self:
        """
        Retrieve an existing Singleton instance (if any) by label.

        :param label: The label to look up.
        :type label: str
        :param search_subclasses: Whether subclasses should be searched for a match.
        :type search_subclasses: bool
        :return: The existing instance if found, otherwise None.
        :rtype: Self | None
        """
        return cls.find_instance(label=label, search_subclasses=search_subclasses)

    @classmethod
    def has_instance(cls, label: UniqueLabel, search_subclasses: bool = False) -> bool:
        return cls.get_instance(label=label, search_subclasses=search_subclasses) is not None

    @classmethod
    def find_instance(cls, search_subclasses: bool = False, **criteria, ) -> Self:
        if x :=  cls._instances.find_one(**criteria):
            return x
        elif search_subclasses:
            for subcls in cls.__subclasses__():
                if x := subcls.find_instance(**criteria, search_subclasses=True):
                    return x

    @classmethod
    def find_instances(cls, search_subclasses: bool = False, **criteria) -> list[Self]:
        res = []
        res.extend( cls._instances.find(**criteria) )
        if search_subclasses:
            for subcls in cls.__subclasses__():
                res.extend( subcls.find_instances(**criteria, search_subclasses=True) )
        return res

    @classmethod
    def all_instances(cls) -> Iterable[Self]:
        return cls._instances.values()

    @classmethod
    def all_instance_tags(cls):
        return cls._instances.all_tags()

    @classmethod
    def all_instance_labels(cls):
        return cls._instances.all_labels()

    @classmethod
    def discard_instance(cls, label):
        if x := cls._instances.find_one(label=label):
            cls._instances.remove(x)

    @classmethod
    def clear_instances(cls, clear_subclasses: bool = False):
        """
        Clear all instances from this class-level registry. Useful in
        testing contexts or to reset state.
        """
        cls._instances.clear()

        if clear_subclasses:
            for cls_ in cls.__subclasses__():
                cls_.clear_instances(clear_subclasses=True)

    def __reduce__(self) -> tuple:
        """
        Singletons can be pickled by reference since they are immutable with respect to
        their public interface.

        :returns: tuple: The class and label of the entity, used for reconstructing the
           instance when unpickling.
        """
        return self.__class__.get_instance, (self.label, )

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

    # Loaders

    @classmethod
    def load_instances(cls, data: dict):
        for label, kwargs in data.items():
            cls(label=label, **kwargs)

    @classmethod
    def load_instances_from_yaml(cls, resources_module: str, fn: str):
        import yaml
        from importlib import resources
        with resources.open_text(resources_module, fn) as f:
            data = yaml.safe_load(f)
        cls.load_instances(data)