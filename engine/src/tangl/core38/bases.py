# tangl/core/bases.py
# language=markdown
"""
# Core base features (v38)

This module defines the *orthogonal* traits that most core objects are composed from.
The goal is to keep identity, value construction, content hashing, ordering, and mutable
state independent so higher layers can combine them without accidental coupling.

## Two loops to keep separate

Core supports two distinct round-trip loops. They intentionally do **not** cross:

1) **Persistence loop (runtime save/load)**

```
Live object  ── unstructure ─▶  UnstructuredData  ── structure ─▶  Live object
```

- Used for persistence, debugging, and transfer inside the engine.
- Preserves identifiers and runtime state (e.g., `uid`, `seq`, locals, etc.).
- May contain Python-native objects (e.g., `Type` references) and is *not* wire-safe.

2) **Authoring loop (compile/decompile scripts)**

The authoring loop is handled by `core.template` and intentionally sits *outside* this
module, but it depends on the contracts defined here.

```
Script dict  ── compile ─▶  EntityTemplate  ── decompile ─▶  Script dict
```

- Used for script linting, normalization, and author-friendly export.
- Strips “framework noise” (uids, ordering, caches) by policy.

## Trait axes

| Concern       | Trait            | Contract (in one sentence) |
|---------------|------------------|----------------------------|
| Identity      | `HasIdentity`    | Stable identifiers; never derived from ordering or content. |
| Structuring   | `Unstructurable` | Canonical constructor form; enables compare-by-value and persistence. |
| Content       | `HasContent`     | Stable content hashing; meaningful only for frozen content. |
| Ordering      | `HasOrder`       | Deterministic ordering; never participates in identity. |
| State         | `HasState`       | Mutable locals; not used for identity or content hashing. |
| Utilities     | `BaseModelPlus`  | Schema introspection helpers and force-set escape hatch. |

### Composition rule of thumb

- Use `HasIdentity` when you need stable references (`uid`, `label`, shortcodes).
- Use `Unstructurable` when you need a reversible constructor form.
- Use `HasContent` when “same content” should imply equivalence.
- Use `HasOrder` when you need deterministic ordering (e.g., registries, streams).
- Use `HasState` when you need mutable runtime locals.

Inheritance order matters for `__eq__`:

- `HasIdentity.__eq__` compares by id.
- `Unstructurable.__eq__` compares by value.
- `HasContent.__eq__` compares by content.

If you compose multiple traits, the **left-most** base class wins for `__eq__`.
For example `class Foo(HasContent, HasIdentity)` will compare by content by default.

## UnstructuredData (what it is and is not)

`UnstructuredData` is a Python-native `dict[str, Any]` constructor form.

- It is designed for *internal* use.
- It may include live `Type` references in the `kind` field.
- It may include sets, UUIDs, timestamps, and other non-JSON/YAML types.

If you need wire-safe JSON/YAML, that is a *persistence service* concern:

1. un/structure → `UnstructuredData`
2. flatten/unflatten → wire-safe primitives
3. serialize/deserialize → bytes/strings

Core only defines step (1).

## Where to look next

- `core.selector`, `core.requirement` for matching and satisfaction.
- `core.registry` for registry ownership and grouping.
- `core.template` for the authoring loop (compile/decompile + materialize).
- `core.entity.Entity` for the default composition (`Unstructurable + HasIdentity`).
- `core.behavior`, `core.dispatch` for hookable behaviors and receipts.

The :func:`is_identifier` symbol in this module is a decorator utility, not a trait.

"""

from __future__ import annotations

from abc import abstractmethod
from copy import deepcopy
from functools import total_ordering
from inspect import isclass
import logging
import time
from typing import Any, Callable, ClassVar, Iterator, Optional, Self, Type
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo
from shortuuid import ShortUUID

from tangl.type_hints import Identifier, Label, StringMap, Tag, UnstructuredData, Hash
from .runtime_op import Predicate, Effect
from tangl.utils.hashing import hashing_func

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

    @classmethod
    def _match_methods(cls, **criteria) -> Iterator[str]:
        """Yield method names whose attributes satisfy `criteria`."""

        def _method_matches(method: Callable):
            for k, v in criteria.items():
                if getattr(method, k, None) != v:
                    return False
            return True

        for cls_ in cls.__mro__:
            for name, attrib in cls_.__dict__.items():
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
        self.__dict__[attrib_name] = value


def is_identifier(meth: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as an identifier producer.

    Why
    ---
    Identifier discovery combines field metadata and method annotations.
    This decorator sets ``is_identifier=True`` on a method so
    :meth:`BaseModelPlus._match_methods` can discover it.

    Fields marked with ``json_schema_extra={"is_identifier": True}`` and methods
    marked with this decorator are both collected by
    :meth:`BaseModelPlus._schema_matches`.

    Example:
        >>> @is_identifier
        ... def my_id():
        ...     return "abc"
        >>> my_id.is_identifier
        True
    """
    setattr(meth, "is_identifier", True)
    return meth


class HasIdentity(BaseModelPlus):
    """Adds stable identity and identifier discovery.

    **UID vs Identifier**
    - The `uid` field is always a `UUID` (the canonical registry index key).
    - `Identifier` is a broader alias used for matching and references: `UUID | str | bytes`
      (e.g., shortcodes, labels, or hash digests).
    - `Registry.get(uid=...)` is the only API that requires a UUID.
    - Selection APIs `Selector.from_identifier()` operate on `Identifier`.

    **Contract:**
    - `get_identifiers()` must be stable and cheap
    - At minimum yields `uid`; may yield `label` and computed aliases (shortcodes, hashes)
    - Labels are stored as provided (sanitization is a higher-layer concern)

    Notes
    -----
    - `get_identifiers()` returns a set built from *both* identifier fields and
      `@is_identifier` method return values.
    - This trait overrides `__eq__` and is intentionally unhashable; use `id_hash()`
      when a stable hash-like identifier is needed.

    Example:
        >>> e = HasIdentity(label="test", tags={'foo', 'bar'})
        >>> repr(e)
        '<HasIdentity:test>'
        >>> all([e.has_identifier("test"), e.has_identifier(e.uid), e.has_identifier(e.shortcode())])
        True
        >>> e.has_tags('foo', 'bar') and not e.has_tags("foobar")
        True
        >>> e.has_kind(BaseModelPlus)  # aliases 'is-instance'
        True
        >>> f = HasIdentity(uid=e.uid, label="not-test")
        >>> e is not f and e.eq_by_id(f) and e == f and e != HasIdentity()  # compare by id
        True
        >>> ids = e.get_identifiers()
        >>> e.uid in ids and "test" in ids and e.shortcode() in ids and e.id_hash() in ids
        True
        >>> e.has_tags() and e.has_tags(None) and e.has_tags({"foo"})
        True
    """

    uid: UUID = Field(default_factory=uuid4, json_schema_extra={"is_identifier": True})
    label: Optional[Label] = Field(None, json_schema_extra={'is_identifier': True})
    tags: set[Tag] = Field(default_factory=set)

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.shortcode()

    @is_identifier
    def id_hash(self) -> Hash:
        # distinct from value_hash, content_hash
        # this _is_ frozen, so we could make this a cached- or shelved-property
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
        """Return ``True`` when all requested tags are present.

        Accepts variadic input (`has_tags("a", "b")`) and a single tuple/list/set
        (`has_tags(("a", "b"))`) for selector compatibility.
        """
        # normalize first term
        if len(tags) == 0:
            return True
        if len(tags) == 1 and tags[0] is None:
            return True
        if len(tags) == 1 and isinstance(tags[0], (tuple, list, set)):
            tags = tags[0]
        return set(tags).issubset(self.tags)

    def has_kind(self, kind: Type) -> bool:
        return isinstance(self, kind)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}:{self.get_label()}>"


class Unstructurable(BaseModelPlus):
    """Adds reversible constructor-form encoding via un/structuring.

    'Structuring' is the basic way to create an object from keyword initialization
    data, and 'Unstructuring' reduces an existing instance back to constructor form.

    UnstructuredData is useful for compare-by-value, persistence, and internal DTOs.

    Notes
    -----
    - Un/structuring is *not* serialization. Unstructured data may carry Python-native
      objects (including live Type references).
    - Wire-safe flattening (JSON/YAML safe primitives) is handled by the persistence
      service layer.
    - `evolve()` preserves ``uid`` by default; pass ``uid=uuid4()`` for a new identity.
    - `evolve()` uses ``deepcopy`` internally; for entities with large mutable state,
      consider field-level cloning if performance becomes a hotspot.
    - `value_hash()` is recomputed from current constructor-form data on each call.
    - Fields marked with ``json_schema_extra={"exclude": True}`` are omitted from
      :meth:`unstructure` output.
    - Set ``guard_unstructure = True`` for classes that should refuse constructor-form
      export because they carry non-serializable behavior.

    Example:
        >>> class E(Unstructurable, HasIdentity): ...
        >>> e = E(label="test")
        >>> data = e.unstructure()
        >>> data['kind'] is E and data['label'] == 'test'
        True
        >>> ee = Unstructurable.structure(data)
        >>> e is not ee and e.eq_by_value(ee) and ee == e
        True
        >>> e2 = e.evolve(label="next")
        >>> e2.label == "next" and e2.uid == e.uid
        True

    See Also
    --------
    - `core.template.EntityTemplate` for compile/decompile + materialization.
    """

    @classmethod
    def structure(cls, data: UnstructuredData) -> Self:
        data = dict(data)
        cls_ = data.pop('kind', cls)
        if not isclass(cls_):
            raise TypeError(f"Expected {cls_} to be a class")
        return cls_(**data)

    guard_unstructure: ClassVar[bool] = False

    def unstructure(self) -> UnstructuredData:
        """Return constructor-form data.

        - If an entity class is allowed to carry non-serializable logic, set
          `guard_unstructure=True` to disable unstructuring.
        - Reducing kind to a qualname is a *serialization* concern, not a
          structuring concern.
        """

        if self.guard_unstructure:
            raise TypeError(
                f"Entities of type {type(self)} may carry non-serializable logic and should not need to be unstructured."
            )

        exclude_fields = set(self._match_fields(exclude=True))
        data = self.model_dump(
            exclude=exclude_fields,
            exclude_unset=True,
            exclude_defaults=True,
        )
        if 'uid' not in data and hasattr(self, 'uid'):
            data['uid'] = getattr(self, 'uid')
        data['kind'] = self.__class__
        return data

    def value_hash(self) -> Hash:
        # Distinct from content hash, this is always based on the Entity's
        # unstructured dict.  For frozen entities, it _may_ be considered
        # to be content.
        return hashing_func(self.unstructure())

    def eq_by_value(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        return self.value_hash() == other.value_hash()

    def __eq__(self, other: Self) -> bool:
        # Order of inheritance matters for this, left-most wins.
        return self.eq_by_value(other)

    def evolve(self, **updates) -> Self:
        # include a new uid in updates if you want a similar copy rather than an exact copy
        data = deepcopy(self.unstructure())
        if updates:
            data = data | updates
        return self.structure(data)


class HasContent(BaseModelPlus):
    """Adds stable content hashing and compare-by-content semantics.

    Content hashing is meaningful as an identifier only when the hashable
    content is stable.  However, it _is_ meaningful as a state comparator
    for unstable content.

    Subclasses must implement :meth:`get_hashable_content`.

    Notes
    -----
    - `content_hash()` is conceptually stable for stable content but is not cached.
    - If composed with other equality traits, Python MRO chooses the left-most `__eq__`.

    Example:
        >>> class E(HasContent):
        ...     content: str
        ...     def get_hashable_content(self): return self.content
        >>> e = E(content="foo"); f = E(content="foo")
        >>> e is not f and e.eq_by_content(f) and e == f and e != E(content="bar")
        True
    """

    @abstractmethod
    def get_hashable_content(self) -> Any:
        ...

    @is_identifier
    def content_hash(self) -> Hash:
        # frozen, could make this into a cached- or shelved-property
        return hashing_func(self.get_hashable_content())

    # todo: want to use a computed_property or cached property _iff_ the model config
    #       is frozen, as with Record and descendents

    def eq_by_content(self, other: Self) -> bool:
        if self.__class__ is not other.__class__:
            return False
        return self.content_hash() == other.content_hash()

    def __eq__(self, other: Self) -> bool:
        return self.eq_by_content(other)


@total_ordering
class HasOrder(BaseModelPlus):
    """Adds deterministic ordering.

    `seq` is guaranteed to be monotonically increasing within a run and can be used as
    a deterministic tie-breaker.

    Notes
    -----
    - `_seq` is seeded with `time.time_ns()` so sequence values are monotonic across runs.
    - Sequence assignment is not thread-safe for strict uniqueness; collisions are harmless
      because `seq` is a tie-breaker, not a primary key.
    - `sort_key()` defaults to `seq`; subclasses may override to provide composite keys.

    Example:
        >>> e = HasOrder(seq=3); f = HasOrder(seq=1); g = HasOrder(seq=2)
        >>> assert f < g < e
        >>> f.has_seq_in(1, 2) and not f.has_seq_in(2, 3)
        True
        >>> g.has_seq_in((1, 3))
        True
        >>> h = HasOrder(); i = HasOrder(); j = HasOrder()
        >>> assert h < i < j
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
        return data

    def has_seq_in(self, low: int, high: int = None) -> bool:
        # foo.has_seq_in(1,2)  ->  low <= foo.seq < high
        if isinstance(low, tuple) and len(low) == 2 and high is None:
            low, high = low
        return low <= self.seq < high

    def sort_key(self):
        return self.seq

    def __lt__(self, other):
        return self.sort_key() < other.sort_key()


class HasState(BaseModelPlus):
    """Adds mutable runtime locals.

    Why
    ---
    Runtime execution frequently needs a scratchpad for transient values. This trait
    provides that scratchpad as a mutable mapping.

    Notes
    -----
    - `locals` is mutable working memory.
    - Identity, content hashing, and ordering traits do not consume `locals`.

    Example:
        >>> s = HasState()
        >>> s.locals["hp"] = 100
        >>> s.locals
        {'hp': 100}
    """

    locals: StringMap = Field(default_factory=dict)


class HasAvailability(BaseModelPlus):
    """Adds predicate-based runtime availability checks.

    Why
    ---
    Many runtime entities need guard conditions that can be serialized and
    evaluated against a scoped namespace. This trait stores those guards as
    :class:`~tangl.core38.runtime_op.Predicate` values.

    Notes
    -----
    - All predicates must evaluate truthy for availability to pass.
    - Empty predicate list means available by default.
    """

    availability: list[Predicate] = Field(default_factory=list)

    def available(self, ns: StringMap | None = None) -> bool:
        if not self.availability:
            return True
        ns = ns or {}
        return all(predicate.satisfied_by(ns) for predicate in self.availability)


class HasEffects(BaseModelPlus):
    """Adds runtime side effects as executable operations.

    Why
    ---
    Runtime entities often need declarative effects that mutate execution
    namespace state during a VM phase. This trait stores those effects as
    :class:`~tangl.core38.runtime_op.Effect` values.
    """

    effects: list[Effect] = Field(default_factory=list)

    def apply_effects(self, ns: StringMap | None = None) -> StringMap:
        ns = ns or {}
        for effect in self.effects:
            effect.apply(ns)
        return ns
