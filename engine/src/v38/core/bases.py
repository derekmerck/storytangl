# tangl/core/bases.py
"""
# Core Base Features

Entities and variants in Core are mainly composed of the few independent feature axes defined here:
- identity and compare by id
- construction by structuring data and compare by value
- carrying stable content and compare by content
- carrying local state
- ordering (with a creation-time based default)

Additional specialized features and shapes are provided as extensions or helper classes in other core modules:
- grouping and group structuring/unstructuring (in core.registry)
- selection, requirements, satisfaction (in core.selector, core.requirement)
- behaviors, job receipt and auditing, chained function dispatch (in core.behavior, core.dispatch)
- singletons and singleton tokens with local state (in core.singleton)
- graph element surface (in core.graph)
"""
from __future__ import annotations
from functools import total_ordering
from inspect import isclass
from uuid import UUID, uuid4
from typing import Callable, Iterator, Type, Self, ClassVar, Any, Optional
import logging
from abc import abstractmethod
import time
from copy import deepcopy

from shortuuid import ShortUUID
from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo

from tangl.type_hints import Tag, Label, Identifier, UnstructuredData, StringMap
from tangl.utils.hashing import hashing_func

logger = logging.getLogger(__name__)


class BaseModelPlus(BaseModel):
    """
    Adds schema introspection for method and field annotations.
    """

    @classmethod
    def _match_methods(cls, **criteria) -> Iterator[str]:
        # check schema for annotated methods

        def _method_matches(method: Callable):
            for k, v in criteria.items():
                if getattr(method, k, None) != v:
                    return False
            return True

        for cls_ in cls.__mro__:
            for name, attrib in cls_.__dict__.items():
                if callable(attrib):
                    if _method_matches(attrib):
                        yield name

    @classmethod
    def _match_fields(cls, **criteria) -> Iterator[str]:
        # check schema for annotated fields

        def _field_matches(field_info: FieldInfo) -> bool:
            for k, v in criteria.items():
                extra = field_info.json_schema_extra or {}
                # logger.debug(f"{extra}.get({k}) == {v} -> {extra.get(k) == v}")
                if not (getattr(field_info, k, None) == v or extra.get(k) == v):
                    return False
            return True

        for name, info in cls.__pydantic_fields__.items():
            if _field_matches(info):
                yield name

    def _schema_matches(self, **criteria) -> StringMap:
        result = {}
        for field in self._match_fields(**criteria):
            value = getattr(self, field)
            result[field] = value
        for meth in self._match_methods(**criteria):
            meth = getattr(self, meth)
            result[meth.__name__ + "()"] = meth()
        return result

    def force_set(self, attrib_name, value):
        # set field values on frozen instances directly, bypassing validation
        self.__dict__[attrib_name] = value


def is_identifier(meth):
    # deco for methods that return an identifier
    setattr(meth, 'is_identifier', True)
    return meth


class HasIdentity(BaseModelPlus):
    """
    **UID vs Identifier**
    - The `uid` field is always a `UUID` (the canonical registry index key).
    - `Identifier` is a broader alias used for matching and references: `UUID | str | bytes`
      (e.g., shortcodes, labels, or hash digests).
    - `Registry.get(uid=...)` is the only API that requires a UUID.
    - Selection APIs (`find_*`, `Selector.identifier`, `has_identifier`) operate on `Identifier`.

    **Contract:**
    - `get_identifiers()` must be stable and cheap
    - At minimum yields `uid`; may yield `label` and computed aliases (shortcodes, hashes)
    - Identity is NOT derived from content hashes or ordering

    Example:
        >>> e = HasIdentity(label="test", tags={'foo', 'bar'})
        >>> repr(e)
        '<HasIdentity:test>'
        >>> all( [e.has_identifier("test"),
        ...       e.has_identifier(e.uid),
        ...       e.has_identifier(e.shortcode()) ] ) # method and attribute schema annotations
        True
        >>> e.has_tags('foo', 'bar') and not e.has_tags("foobar")
        True
        >>> e.has_kind(BaseModelPlus)  # aliases 'is-instance'
        True
        >>> f = HasIdentity(uid=e.uid, label="not-test")
        >>> e is not f and e.eq_by_id(f) and e == f and e != HasIdentity()  # compare by id
        True
    """
    uid: UUID = Field(default_factory=uuid4, json_schema_extra={"is_identifier": True})
    label: Optional[Label] = Field(None, json_schema_extra={'is_identifier': True})
    tags: set[Tag] = Field(default_factory=set)

    @is_identifier
    def get_label(self):
        return self.label or self.shortcode()

    @is_identifier
    def id_hash(self) -> bytes:
        # distinct from content_hash
        return hashing_func(self.__class__, self.uid)

    def eq_by_id(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        return self.id_hash() == other.id_hash()

    def __eq__(self, other: Self) -> bool:
        return self.eq_by_id(other)

    @is_identifier
    def shortcode(self) -> str:
        return ShortUUID().encode(self.uid)

    def get_identifiers(self) -> set[Identifier]:
        return set(self._schema_matches(is_identifier=True).values())

    def has_identifier(self, identifier: Identifier) -> bool:
        return identifier in self.get_identifiers()

    def has_tags(self, *tags: Tag) -> bool:
        # normalize first term
        if len(tags) == 0:
            return True
        if len(tags) == 1 and tags[0] is None:
            return True
        if len(tags) == 1 and isinstance(tags[0], tuple | list | set):
            tags = tags[0]
        return set(tags).issubset(self.tags)

    def has_kind(self, kind: Type) -> bool:
        return isinstance(self, kind)

    def __repr__(self):
        return f"<{self.__class__.__name__}:{self.get_label()}>"


class Unstructurable(BaseModelPlus):
    """
    'Structuring' is the basic way to create an entity from keyword initialization
    data and 'Unstructuring' is the basic way to reduce an existing instance back to
    constructor form.  Unstructured data reprsentation is useful for compare-by-value,
    persistence, and encoding data transfer objects.

    UnstructuredData may include a class override for in a "kind" field, for
    restructuring to the proper type.  UnstructuredData may include recursively
    unstructured data only in certain classes, such as Registry, by design.

    There are 3 distinct phases encode/decode for wire:
    1. Un/Structuring -> convert models into `dict[str, Any]` ('UnstructuredData') suitable for constructing a new object.
    2. Un/Flattening -> convert UnstructuredData into `dict[str, Primitive]` ('FlatData'), where Primitives are yaml/json safe (no types, uuids, timestamps, enums, sets, etc.).  For unflattening, Kind-resolution uses an explicit `KindRegistry`.
    3. De/Serialize -> dependent on backend choice, maybe binary (pickle/bson) or strings (json/yaml).

    Flattening and Serialization are entirely independent of model type and managed by the persistence service.  They are _not_ addressed in core.

    Example:
        >>> class E(Unstructurable, HasIdentity): ...
        >>> e = E(label="test")
        >>> data = e.unstructure()
        >>> data['kind'] is E and data['label'] == 'test'  # injects kind field
        True
        >>> ee = Unstructurable.structure(data)
        >>> e is not ee and e.eq_by_value(ee) and ee == e  # round-trip compares by value
        True
    """
    @classmethod
    def structure(cls, data) -> Self:
        cls_ = data.pop('kind', cls)
        if not isclass(cls_):
            raise TypeError(f"Expected {cls_} to be a class")
        return cls_(**data)

    guard_unstructure: ClassVar[bool] = False

    def unstructure(self) -> UnstructuredData:
        """"
        - If an entity class is allowed to carry non-serializable logic, set the
          class flag 'guard_unstructure' to disabling unstructuring.
        - Reducing kind to a qualname is a _serialization_ concern NOT a
          structuring concern
        """
        if self.guard_unstructure:
            raise TypeError(
                f"Entities of type {type(self)} may carry non-serializable logic and should not need to be unstructured.")

        exclude_fields = set( self._match_fields(exclude=True) )
        data = self.model_dump(exclude=exclude_fields)
        data['kind'] = self.__class__
        return data

    def eq_by_value(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        self_data = self.unstructure()
        other_data = other.unstructure()
        return self_data == other_data

    def __eq__(self, other: Self) -> bool:
        # Order of inheritance matters for this, right-most wins
        return self.eq_by_value(other)

    def evolve(self, **updates) -> Self:
        # include a new uid in updates if you want a similar copy rather than an exact copy
        data = self.unstructure()
        data = deepcopy(data)  # clean copy
        if updates:
            data = data | updates
        return self.structure(data)


class HasContent(BaseModelPlus):
    """
    Entities that carry a stable content payload may be compared by content rather than identity or value.  This can be used as a singleton flag.

    Example:
        >>> class E(HasContent):
        ...     attrib: str
        ...     def get_content(self): return self.attrib
        >>> e = E(attrib="foo"); f = E(attrib="foo")
        >>> assert e is not f and e.eq_by_content(f) and e == f and e != E(attrib="bar")  # compares by content
    """

    @abstractmethod
    def get_content(self) -> Any: ...

    @is_identifier
    def content_hash(self) -> bytes:
        return hashing_func(self.get_content())

    def eq_by_content(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        return self.content_hash() == other.content_hash()

    def __eq__(self, other: Self) -> bool:
        return self.eq_by_content(other)

@total_ordering
class HasOrder(BaseModelPlus):
    """
    Entities that are sortable need a sensible default ordering.

    'seq' is guarenteed to be monotonically increasing over all runs and
    can be added to any sort key as a deterministic tie-breaker.

    Example:
        >>> e = HasOrder(seq=3); f = HasOrder(seq=1); g = HasOrder(seq=2)
        >>> assert f < g < e     # forced order respected
        >>> h = HasOrder(); i = HasOrder(); j = HasOrder()
        >>> assert h < i < j     # default order respected
    """

    seq: int = Field(None, init=False, validate_default=True)
    _seq: ClassVar[int] = time.time_ns()  # initialize to something strictly larger than the previous run

    @classmethod
    def next_seq(cls) -> int:
        cls._seq += 1
        return cls._seq

    @field_validator("seq", mode="before")
    @classmethod
    def _set_seq(cls, data):
        if data is None:
            return cls.next_seq()
            # does 'before' activate prior to when the attribs get frozen?
        return data

    def has_seq_in(self, low: int, high: int) -> bool:
        # foo.has_seq_in(1,2)  ->  1 <= foo.seq <= 2
        # probably need to spread low if it arrives as a tuple and no high like tags
        return low <= self.seq < high

    def sort_key(self):
        return self.seq

    def __lt__(self, other):
        return self.sort_key() < other.sort_key()


class HasState(BaseModelPlus):
    """
    Entities that carry a mutable runtime state define a 'locals' mapping
    that can be folded into a scoped namespace by context.
    """
    locals: StringMap = Field(default_factory=dict)
