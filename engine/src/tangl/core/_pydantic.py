from __future__ import annotations

import logging
from typing import Any, Callable, ClassVar, Iterator, Optional, Self, Type

from pydantic import BaseModel, Field, field_validator, model_serializer
from pydantic.functional_serializers import SerializerFunctionWrapHandler
from pydantic.fields import FieldInfo

from tangl.type_hints import StringMap

logger = logging.getLogger(__name__)


class BaseModelPlus(BaseModel):
    """Pydantic base model with schema introspection and escape hatches.

    Why
    ---
    The core trait system uses schema metadata instead of hardcoded field lists.
    This keeps identifier and matching behavior composable across mixed traits.

    Key Features
    ------------
    - :meth:`_match_fields` discovers fields by ``Field`` metadata and
      ``json_schema_extra`` markers.
    - :meth:`_match_methods` discovers methods by custom attributes.
    - :meth:`_schema_matches` combines both into a single value map.
    - :meth:`force_set` writes directly to ``__dict__`` for controlled bypasses
      on frozen models.
    - Set-valued fields serialize as **sorted lists** so dumps and the hashes
      derived from them are deterministic — see :meth:`_sort_set_fields`.

    Example:
        >>> class F(BaseModelPlus):
        ...     x: int = Field(0, json_schema_extra={"is_identifier": True})
        ...     y: int = 0
        >>> list(F._match_fields(is_identifier=True))
        ['x']

        >>> class M(BaseModelPlus):
        ...     @property
        ...     def nope(self):
        ...         return 1
        ...     def yes(self):
        ...         return 2
        >>> setattr(M.yes, "foo", True)
        >>> list(M._match_methods(foo=True))
        ['yes']

        >>> class S(BaseModelPlus):
        ...     x: int = Field(42, json_schema_extra={"magic": True})
        >>> S()._schema_matches(magic=True)
        {'x': 42}

        >>> from pydantic import ConfigDict
        >>> class Frozen(BaseModelPlus):
        ...     model_config = ConfigDict(frozen=True)
        ...     x: int = 0
        >>> f = Frozen(x=1)
        >>> f.force_set("x", 99)
        >>> f.x
        99
    """

    @model_serializer(mode="wrap")
    def _sort_set_fields(self, handler: SerializerFunctionWrapHandler, info) -> Any:
        """Serialize set-valued fields as sorted lists, in every dump mode.

        Sets have no defined iteration order, and for sets of strings that order
        varies between processes under hash randomization. Since ``unstructure()``
        is built on ``model_dump`` and the hashes are built on ``unstructure()``, an
        unsorted set field made ``value_hash`` differ on every run — and ``tags`` is
        on every entity, so this reached almost everything.

        This runs at the *model* level rather than per field: a wildcard
        ``field_serializer`` intercepts each field individually and breaks
        ``exclude_defaults`` propagation into nested models. Wrapping the whole dump
        and normalizing afterward leaves the handler's own rules untouched.

        The live attribute decides what to sort, not the dumped value, because JSON
        mode has already listified the set by the time we see it. That means walking
        *fields* rather than output keys: under ``by_alias=True`` the dumped key is the
        alias, and ``getattr(self, alias)`` finds nothing. ``BaseScriptItem`` both
        defaults to ``by_alias=True`` and carries aliased set fields
        (``req_ancestor_tags``), so keying off the output name silently skipped it.

        Sorting by ``str`` is deterministic for the value-like members these sets
        actually hold (str, enum, UUID, int). It is **not** a general guarantee: a
        set of objects using the default ``repr`` sorts by memory address and stays
        unstable. See the hash stability contract in
        ``design/core/CONTENT_ADDRESSABLE.md``.
        """
        data = handler(self)
        if not isinstance(data, dict):
            return data
        for name, field in type(self).model_fields.items():
            raw = getattr(self, name, None)
            if not isinstance(raw, (set, frozenset)):
                continue
            # the field may appear under its own name or either alias
            for key in (name, field.serialization_alias, field.alias):
                if key in data and isinstance(data[key], (set, frozenset, list, tuple)):
                    data[key] = sorted(data[key], key=str)
                    break
        return data

    @classmethod
    def _match_methods(cls, **criteria) -> Iterator[str]:
        """Yield method names whose attributes satisfy `criteria`."""

        def _method_matches(method: Callable):
            for k, v in criteria.items():
                if getattr(method, k, None) != v:
                    return False
            return True

        seen_names: set[str] = set()
        for cls_ in cls.__mro__:
            for name, attrib in cls_.__dict__.items():
                if name in seen_names:
                    continue
                seen_names.add(name)
                if callable(attrib) and _method_matches(attrib):
                    yield name

    @classmethod
    def _match_fields(cls, **criteria) -> Iterator[str]:
        """Yield field names whose FieldInfo (or json_schema_extra) satisfy `criteria`."""

        def _field_matches(field_info: FieldInfo) -> bool:
            for k, v in criteria.items():
                extra = field_info.json_schema_extra or {}
                if not (getattr(field_info, k, None) == v or extra.get(k) == v):
                    return False
            return True

        for name, info in cls.model_fields.items():
            if _field_matches(info):
                yield name

    def _schema_matches(self, **criteria) -> StringMap:
        """Return a mapping of matching field/method schema annotations to values."""
        result: StringMap = {}
        for field in self._match_fields(**criteria):
            result[field] = getattr(self, field)
        for meth in self._match_methods(**criteria):
            m = getattr(self, meth)
            result[m.__name__ + "()"] = m()
        return result

    def force_set(self, attrib_name: str, value: Any) -> None:
        """Set field values on frozen instances directly, bypassing validation."""
        if attrib_name not in type(self).model_fields:
            raise AttributeError(f"Unknown field: {attrib_name}")
        self.__dict__[attrib_name] = value
        self.__pydantic_fields_set__.add(attrib_name)

    @classmethod
    def __fqn__(cls) -> str:
        return f"{cls.__module__}.{cls.__name__}"

    @classmethod
    def dereference_cls_name(cls, name: str) -> Type[Self] | None:
        """Resolve a class name/fqn against ``cls`` and its subclass tree."""
        if name == cls.__qualname__ or name == cls.__fqn__():
            return cls
        for sub_cls in cls.__subclasses__():
            if resolved := sub_cls.dereference_cls_name(name):
                return resolved
        return None
