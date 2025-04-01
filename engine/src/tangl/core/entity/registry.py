"""
registry.py

This module provides the :class:`Registry` class, which is both a Tangl
:class:`~tangl.entity.Entity` and a :class:`~collections.abc.MutableMapping`
of UUID -> Entity. It allows for flexible, criteria-based searching and
serialization/deserialization of the contained entities.

**Separation of Concerns**:
  - **Collection Management**: By conforming to the MutableMapping interface,
    developers can treat a Registry almost like a normal dictionary (with some
    constraints).
  - **Entity Integration**: Inheriting from :class:`~tangl.entity.Entity` lets
    the registry itself have a domain, tags, or other metadata. This unifies
    the "bookkeeping container" concept with the same identification and
    serialization rules used across all Tangl objects.
  - **Search & Filter**: Built-in methods like :meth:`find` and :meth:`find_one`
    leverage the :meth:`~tangl.entity.Entity.matches_criteria` logic, so the
    registry can seamlessly search across multiple entity subtypes.

Usage:
  >>> my_registry = Registry()
  >>> my_registry.add(Entity(domain="sci-fi"))
  >>> results = my_registry.find(domain="fantasy.*")
"""

from __future__ import annotations
from typing import TypeVar, Generic, Self, Optional, Any, MutableMapping, Iterator, Iterable
from uuid import UUID
import functools
import logging
from collections import Counter

from pydantic import BaseModel, PrivateAttr

from tangl.type_hints import UniqueLabel, UnstructuredData
from tangl.utils.dereference_obj_cls import dereference_obj_cls
from .entity import Entity

logger = logging.getLogger(__name__)

VT = TypeVar('VT', bound=Entity)

class Registry(Entity, MutableMapping[UUID, VT], Generic[VT]):
    """
    A specialized :class:`~tangl.entity.Entity` that implements a
    :class:`~collections.abc.MutableMapping` of UUID to another Tangl
    :class:`~tangl.entity.Entity`. This allows easy storage, lookup, and
    filtering of child entities.

    **Behavior & Constraints**:
      - Although this class implements ``MutableMapping``, direct assignment
        via ``__setitem__`` is disallowed to ensure consistent usage of
        :meth:`add`.
      - The registry itself is an Entity, so it can carry its own
        :attr:`uid`, :attr:`label`, :attr:`tags`, etc.
      - Each contained entity must have a unique UUID; overwriting an existing
        key requires an explicit ``allow_overwrite=True`` flag.

    :param _data: A private dictionary that actually stores the entities.
    :type _data: dict[UUID, VT]
    """
    _data: dict[UUID, VT] = PrivateAttr(default_factory=dict)

    def __getitem__(self, key: UUID | UniqueLabel) -> VT:
        """
        Retrieve an entity by UUID or by a label that matches ``entity.label``.

        :param key: The UUID or label of the desired entity.
        :type key: Union[UUID, UniqueLabel]
        :return: The matching entity.
        :rtype: VT
        :raises KeyError: If the key is a UUID not found in the Registry, or
                          if it is a label that doesn't match any entity.
        """
        if isinstance(key, UniqueLabel):
            if x := self.find_one(label=key):
                return x
        return self._data[key]

    def __setitem__(self, key: UUID, value: VT) -> None:
        """
        Prohibited direct assignment. Raises :exc:`NotImplementedError`.

        :raises NotImplementedError: Always, since the registry requires
                                     :meth:`add` for controlled insertion.
        """
        raise NotImplementedError(f"{self.__class__.__name__} is not setable by key, use `add(entity)`.")

    def __delitem__(self, key: UUID) -> None:
        """
        Delete an entity from the Registry.

        :param key: The UUID of the item to remove.
        :type key: UUID

        :raises KeyError: If the key is not found in the Registry.
        """
        del self._data[key]

    def __iter__(self) -> Iterator[UUID]:
        """
        Iterate over the UUIDs of the contained entities.

        :return: An iterator of UUIDs.
        :rtype: Iterator[UUID]
        """
        return iter(self._data)

    def __len__(self) -> int:
        """
        Get the count of entities in this Registry.

        :return: Number of contained entities.
        :rtype: int
        """
        return len(self._data)

    def __contains__(self, item: Entity | UUID) -> bool:
        if isinstance(item, Entity):
            item = item.uid
        return item in self._data

    def __bool__(self) -> bool:
        return bool(self._data)

    def add(self, value: VT, allow_overwrite: bool = False) -> None:
        """
        Add a new entity to the Registry. The entity's UUID is used as
        the map key. By default, duplicates are disallowed.

        :param value: The entity to add.
        :type value: VT
        :param allow_overwrite: Whether to overwrite an existing entity with
                                the same UUID, defaults to False.
        :type allow_overwrite: bool
        :raises ValueError: If an entity with the same UUID already exists
                            and ``allow_overwrite`` is False.
        """
        if not allow_overwrite and value.uid in self._data:
            raise ValueError(f"Cannot overwrite {value.uid} in registry. Pass `allow_overwrite=True` to force overwrite.")
        self._data[value.uid] = value

    def remove(self, value: VT) -> None:
        """
        Remove an entity from the Registry by its UUID, ignoring if not found.

        :param value: The entity to remove (searched by its ``uid``).
        :type value: VT
        """
        self._data.pop(value.uid, None)

    def find(self, **criteria) -> list[VT]:
        """
        Retrieve all entities that match the given criteria. Criteria
        matching is delegated to :meth:`~tangl.entity.Entity.matches_criteria`.

        :param criteria: Key-value pairs to filter on (e.g. ``domain="foo"``,
                         ``label="bar"``).
        :return: All entities that match the criteria.
        :rtype: list[VT]
        """
        return self.filter_by_criteria(self._data.values(), **criteria)

    def find_one(self, **criteria) -> Optional[VT]:
        """
         Retrieve the first entity that matches the given criteria, or
         ``None`` if no match is found.

         :param criteria: Key-value pairs to filter on.
         :return: The first matching entity or ``None``.
         :rtype: Optional[VT]
         """
        return self.filter_by_criteria(self._data.values(), return_first=True, **criteria)

    def values(self) -> Iterable[VT]:
        return self._data.values()

    def all_tags(self) -> Counter:
        res = Counter()
        for c in self.values():
            for t in c.tags:
                res[t] += 1
        return res

    def all_labels(self) -> list[str]:
        return [ v.label for v in self.values() ]

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extended dump that includes all contained entities under ``data``
        in unstructured form. Leverages the parent :meth:`tangl.entity.Entity.model_dump`
        for base fields.

        :param args: Forwarded to Pydantic's ``model_dump``.
        :param kwargs: Forwarded to Pydantic's ``model_dump``.
        :return: A dictionary with the Registry's fields plus a ``data`` key
                 listing each contained entity's unstructured representation.
        :rtype: dict[str, Any]
        """
        data = super().model_dump(**kwargs)
        data['data'] = []
        for v in self.values():
            data['data'].append(v.unstructure())
        return data

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        """
        Reconstruct a Registry (and its contained entities) from a
        previously dumped data structure. Identifies the correct Registry
        subclass via ``obj_cls``, then iterates over each item in ``data``
        to rebuild contained entities.

        :param data: The unstructured data produced by :meth:`model_dump`.
        :type data: dict
        :return: A rehydrated Registry containing entity objects.
        :rtype: Self
        :raises ValueError: If the stated ``obj_cls`` cannot be resolved, or
                            if individual entities fail to structure.
        """
        obj_cls = data.pop("obj_cls")
        obj_cls = dereference_obj_cls(cls, obj_cls)
        this = obj_cls()
        data = data.pop('data', [])
        for v in data:
            item = Entity.structure(v)
            this.add(item)
        return this
