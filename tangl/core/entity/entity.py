"""
entity.py

This module provides the foundational ``Entity`` class, which all
higher-level Tangl classes build upon. The ``Entity`` encapsulates:

- **Data Integrity** via Pydantic fields and validators.
- **Identification** (UUID, label, tags, data hash) for robust instance
  management.
- **Filtering & Searching** through flexible criteria-based matching.
- **Serialization & Deserialization** (model_dump / structure) to cleanly
  separate data handling from application logic.

Derived classes can specialize behavior (like node vs. edge definitions),
while still inheriting the robust core features here.
"""

from __future__ import annotations
from typing import Self, Optional, Any, Iterable, Type
from uuid import UUID, uuid4
import functools
from fnmatch import fnmatch
import logging

import shortuuid
from pydantic import BaseModel, Field, model_validator, field_serializer

from tangl.type_hints import UnstructuredData, Identifier, Hash, Label, Tag, Typelike
from tangl.utils.dereference_obj_cls import dereference_obj_cls

logger = logging.getLogger(__name__)

class Entity(BaseModel):
    """
    The base class for all Tangl managed objects.

    This class extends Pydantic's ``BaseModel`` to integrate fundamental
    identity, labeling, domain scoping, and hashing features. Derived
    classes can build on these capabilities for more specialized behaviors,
    keeping data consistency and filtering logic centralized.

    **Separation of Concerns**:
      - **Data Integrity**: Pydantic ensures type checking and validation.
      - **Identification**: Managed by ``uid``, ``label``, ``tags``, and ``data_hash``.
      - **Filtering & Matching**: Provided by methods like :meth:`matches_criteria`
        and :meth:`filter_by_criteria`.
      - **Serialization & Deserialization**: Provided by :meth:`model_dump`,
        :meth:`unstructure`, and :meth:`structure`.

    :param obj_cls: Consumed by a metaclass or external builder to ensure the correct
                   final model class (subclass) is used during reconstruction.
    :type obj_cls: str | Type[Self]
    :param uid: The unique identifier for each entity (defaults to a UUIDv4).
    :type uid: UUID
    :param label: A short human-readable alias or name for the entity. If
                  not provided, one is generated from the ``uid``.
    :type label: str
    :param tags: A set of string tags for categorization or searching.
    :type tags: set[Tag]
    :param data_hash: An optional cryptographic hash for the entity data.
    :type data_hash: Hash
    :param domain: A string used to categorize or namespace the entity. Allows
                   advanced domain-based filtering.
    :type domain: str
    :param dirty: A boolean indicating whether this entity has been modified
                  since last known valid state.
    :type dirty: bool
    """

    obj_cls: Typelike = Field(init_var=True, default=None)
    uid: UUID = Field(init=False, default_factory=uuid4)
    label: Label = None
    tags: set[Tag] = Field(default_factory=set)
    content_hash: Hash = None
    domain: str = None  # holder for user-defined domain of entity
    dirty: bool = None  # indicator that entity has been tampered with, invalidates certain debugging

    @property
    def short_uid(self) -> str:
        """
         A short, URL-friendly alias for the ``uid``.

         :return: A short-uuid representation of the entity's UUID.
         :rtype: str
         """
        return shortuuid.encode(self.uid)

    @model_validator(mode="after")
    def _set_default_label(self):
        """
        Internal validator that sets a default ``label`` from the ``short_uid``
        if no label was provided. Helps ensure every entity has at least a
        minimal readable label.
        """
        # this is considered 'unset' and won't be serialized
        if self.label is None:
            self.label = self.short_uid[0:6]
        return self

    @field_serializer("tags")
    def _convert_set_to_list(self, values: set):
        """
        Field-level serializer that converts sets to lists, to ensure
        JSON-serializable output for tags.

        :param values: The set of tags.
        :type values: set
        :return: A list of tags.
        :rtype: list
        """
        if isinstance(values, set):
            return list(values)
        return values

    def has_tags(self, *tags: Tag) -> bool:
        """
        Check whether this entity includes *all* of the specified tags.

        :param tags: One or more tags to test for membership.
        :type tags: str
        :return: True if all given tags are found in this entity's tag set.
        :rtype: bool

        Example::

            if my_entity.has_tags("villain", "undead"):
                ...
        """
        if len(tags) == 1 and isinstance(tags[0], (list, set)):
            tags = tags[0]
        return set(tags).issubset(self.tags)

    def get_identifiers(self) -> set[Identifier]:
        """
        Retrieve all known identifiers for this entity. By default,
        these include the ``uid`` (UUID), ``label``, and ``data_hash``.

        Subclasses may override or extend to include additional aliases.

        :return: A set of identifiers usable for matching or searching.
        :rtype: set[Identifier]
        """
        return { self.uid, self.label, self.content_hash }

    def has_alias(self, *aliases: Identifier) -> bool:
        """
        Check whether any of the provided aliases is in this entity's identifiers.

        Useful for matching flexible user-supplied references or multiple labels.

        :param aliases: One or more candidate aliases to check.
        :type aliases: str, UUID, or similar
        :return: True if at least one alias matches one of this entity's identifiers.
        :rtype: bool
        """
        if len(aliases) == 1 and isinstance(aliases[0], (list, set)):
            aliases = aliases[0]
        identifiers = self.get_identifiers()
        identifiers = { x for x in identifiers if x }  # discard empty/falsy identifiers
        return bool( set(aliases).intersection(identifiers) )

    def has_cls(self, obj_cls: Typelike) -> bool:
        """
        Check if this entity is an instance of the specified class or
        subclass thereof. Accepts either a class object or a string
        class name (resolved via :func:`~tangl.utils.dereference_obj_cls`).

        :param obj_cls: The class name or type to compare against.
        :type obj_cls: str | type[Self]
        :return: True if ``self`` is an instance of that class.
        :rtype: bool
        """
        cls_ = dereference_obj_cls(self.__class__, obj_cls)
        return isinstance(self, cls_)

    @classmethod
    def class_distance(cls, obj_cls: Typelike) -> Optional[int]:
        """
        Compute the distance in the MRO (method resolution order) between
        this child class and a target superclass or class name. A distance
        of 0 means exactly the same class, 1 means immediate parent, etc.

        i.e., child_class.class_distance(parent_class) = 1

        :param obj_cls: The class name or type to measure distance from.
        :type obj_cls: str | type[Self]
        :return: The integer distance or None if the target is not in the MRO.
        :rtype: int | None
        """
        cls_ = dereference_obj_cls(cls, obj_cls)
        if cls is cls_:
            return 0
        # logger.debug(f"Resolved {cls_}")
        if not issubclass(cls, cls_):
            raise ValueError(f"{cls.__name__} is not a subclass of {cls_.__name__}, cannot compute class dist")
        return cls.__mro__.index(cls_) + 1

    def has_domain(self, domain: str) -> bool:
        """
        Check if this entity's ``domain`` matches the specified domain pattern.
        Supports wildcard matching via ``fnmatch``.

        :param domain: A string domain pattern, e.g. ``"mydomain.*"`` or exact match.
        :type domain: str
        :return: True if the entity's domain matches the pattern.
        :rtype: bool
        """
        if not isinstance(self.domain, str) or not isinstance(domain, str):
            return False
        if '*' in domain:
            # compare strings with * in test with fnmatch
            return fnmatch(self.domain, domain)
        return self.domain == domain

    def matches_criteria(self, **criteria) -> bool:
        """
        Evaluate whether this entity meets all provided criteria. Each
        criterion is tested using a dedicated ``has_<criterion>`` method,
        if available, or by direct attribute comparison.

        :param criteria: Key-value pairs for the match check. E.g.
                         ``matches_criteria(domain="mydomain", label="foo")``.
        :type criteria: Any
        :raises ValueError: If no criteria are provided, or if a criterion
                            doesn't map to a known property or method.
        :return: True if the entity passes *all* specified criteria.
        :rtype: bool
        """
        if not criteria:
            raise ValueError("No criteria specified, return value is undefined.")

        for criterion, value in criteria.items():
            # try any explicitly defined tests first
            if hasattr(self, f"has_{criterion}"):
                return getattr(self, f"has_{criterion}")(value)
            # if the attribute is directly available, try comparing it
            elif hasattr(self, criterion):
                return getattr(self, criterion) == value
            else:
                raise ValueError(f"Untestable comparator for {criterion} on {self.__class__}")

        return True  # all checks passed

    @classmethod
    def filter_by_criteria(cls, entities: Iterable[Self], return_first: bool = False, **criteria) -> Self | list[Self] | None:
        """
        Filter an iterable of entities, returning only those that meet the
        specified criteria. Can optionally short-circuit by returning the
        first match.

        :param entities: An iterable of entities to filter.
        :type entities: Iterable[Self]
        :param return_first: If True, stop and return the first matching entity.
        :type return_first: bool
        :param criteria: Key-value pairs for matching (see :meth:`matches_criteria`).
        :return: A single entity if ``return_first=True``; otherwise a list of all matches.
        :rtype: Self | list[Self] | None
        """
        matches = (e for e in entities if e.matches_criteria(**criteria))
        if return_first:
            return next(matches, None)
        return list(matches)

    @functools.wraps(BaseModel.model_dump)
    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """
        Extended dump method that ensures certain critical fields
        (e.g. ``uid`` and ``obj_cls``) are included even when they might
        be considered unset or default.

        :param args: Forwarded to Pydantic's :meth:`BaseModel.model_dump`.
        :param kwargs: Forwarded to Pydantic's :meth:`BaseModel.model_dump`.
        :return: A dictionary representation of the entity suitable for serialization.
        :rtype: dict[str, Any]
        """
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", True)
        kwargs['by_alias'] = True  # for round-trip
        data = super().model_dump(**kwargs)
        data['uid'] = self.uid  # uid is _always_ unset initially, so we have to include it manually
        data['obj_cls'] = self.__class__  # for restructuring to the correct model type
        return data

    def unstructure(self, *args, **kwargs) -> UnstructuredData:
        """
        Convert the given entity into a generic Python data structure suitable
        for JSON/YAML serialization. In practice, calls :meth:`model_dump`.

        :param args: Forwarded to :meth:`model_dump`.
        :param kwargs: Forwarded to :meth:`model_dump`.
        :return: A JSON/YAML-friendly dict representation.
        :rtype: UnstructuredData
        """
        return self.model_dump(*args, **kwargs)

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        """
        Reconstruct an entity (including subclass resolution) from a
        previously dumped data structure. Uses ``obj_cls`` to find the
        correct subclass, then instantiates.

        :param data: The unstructured data from :meth:`unstructure`.
        :type data: dict
        :return: A rehydrated entity (or subclass).
        :rtype: Self
        :raises ValueError: If the stated ``obj_cls`` cannot be found or
                            does not match a valid subclass.
        """
        obj_cls = data.pop("obj_cls", None)
        obj_cls = dereference_obj_cls(cls, obj_cls)
        this = obj_cls(**data)
        return this

    @classmethod
    def cmp_fields(cls):
        """
        Identify which fields should be used for equality checks. By default,
        this returns all fields unless the field metadata explicitly sets
        ``cmp=False`` in ``json_schema_extra``.

        :return: A list of field names used in :meth:`__eq__`.
        :rtype: list[str]
        """
        res = []
        for field_name, field_info in cls.__pydantic_fields__.items():
            extra = field_info.json_schema_extra or {}
            if extra.get('cmp', True):
                res.append(field_info.alias or field_name)
        return res

    def __eq__(self, other: Self) -> bool:
        """
        Compare two entities for equality by checking all ``cmp_fields``.
        Recursively avoids comparing linked sub-objects to prevent infinite
        loops in graphs.

        :param other: Another entity to compare.
        :type other: Any
        :return: True if the fields returned by :meth:`cmp_fields` are equal.
        :rtype: bool
        """
        if self.__class__ is not other.__class__:
            return False
        for field in self.cmp_fields():
            if getattr(self, field) != getattr(other, field):
                return False
        return True
