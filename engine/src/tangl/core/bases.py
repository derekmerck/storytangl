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

- `core.selector` for matching.
- `vm.provision.requirement` for satisfaction and provisioning contracts.
- `core.registry` for registry ownership and grouping.
- `core.template` for the authoring loop (compile/decompile + materialize).
- `core.entity.Entity` for the default composition (`Unstructurable + HasIdentity`).
- `core.behavior`, `core.dispatch` for hookable behaviors and receipts.
- `vm.traversable` for VM-specific `HasAvailability` and `HasEffects` traits.

The :func:`is_identifier` symbol in this module is a decorator utility, not a trait.

"""

from __future__ import annotations

from abc import abstractmethod
from copy import deepcopy
from functools import total_ordering
from inspect import isclass, signature
import logging
import time
from types import UnionType
from typing import (
    Any,
    Callable,
    ClassVar,
    Optional,
    Self,
    Type,
    Union,
    get_args,
    get_origin,
)
from uuid import UUID, uuid4

from pydantic import Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from shortuuid import ShortUUID

from tangl.type_hints import Identifier, Label, StringMap, Tag, UnstructuredData, Hash
from tangl.utils.hashing import hashing_func
from ._pydantic import BaseModelPlus

logger = logging.getLogger(__name__)


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
    - Pydantic ``model_dump()`` is not a substitute for this constructor form.
      It does not know StoryTangl's graph-reference conventions and can silently
      deep-dump live entity pointers or omit mutated default managers. Runtime
      graph state must prove itself through ``unstructure()`` / ``structure()``.
    - `evolve()` preserves ``uid`` by default; pass ``uid=uuid4()`` for a new identity.
    - `evolve()` uses ``deepcopy`` internally; for entities with large mutable state,
      consider field-level cloning if performance becomes a hotspot.
    - `value_hash()` is recomputed from current constructor-form data on each call.
    - Fields marked with ``json_schema_extra={"exclude": True}`` are omitted from
      :meth:`unstructure` output.
    - Fields marked with ``json_schema_extra={"include": True}`` are persisted
      whenever their value diverges from the field default, even if the field
      was only mutated in place and never reassigned (so ``exclude_unset``
      cannot drop them). Still-default/empty values remain elided, so this does
      not chum snapshots with nulls or defaults.
    - Recursive constructor-form handling is a separate concern from inclusion.
      The field marker ``json_schema_extra={"unstructurable": True}`` means
      "walk this embedded value through its own
      ``unstructure()`` / ``structure()`` hooks." Full graph entities should not
      be recursively embedded by default; they should be referenced by id unless
      a field deliberately opts into embedded constructor-form semantics.
      This generalizes explicit constructor-form handling for fields like
      ``EntityTemplate.payload``; ``Registry.members`` keeps its bespoke path so
      ``Registry.add()`` can preserve ownership-binding guardrails.
      It should not revive the old automorphic structuring experiments from
      ``scratch/legacy/core/core-23/structuring/``: no self-casting from data,
      self-templating, property-name child inference, or object-self-shaping
      pipeline belongs in the core constructor-form path.
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
    def structure(cls, data: UnstructuredData, _ctx: Any = None) -> Self:
        data = dict(data)
        cls_ = data.pop('kind', cls)
        if not isclass(cls_):
            raise TypeError(f"Expected {cls_} to be a class")
        if hasattr(cls_, "_match_fields"):
            for name in cls_._match_fields(unstructurable=True):
                if name not in data:
                    continue
                field_info = cls_.model_fields[name]
                data[name] = cls._structure_unstructurable_value(
                    data[name],
                    field_info.annotation,
                    _ctx=_ctx,
                )
        return cls_(**data)

    guard_unstructure: ClassVar[bool] = False

    @classmethod
    def _structure_unstructurable_value(
        cls,
        value: Any,
        annotation: Any = Any,
        *,
        _ctx: Any = None,
    ) -> Any:
        """Structure a marked embedded value using annotation or explicit ``kind``."""
        if value is None:
            return None

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin in (Union, UnionType):
            if value is None:
                return None
            for option in args:
                if option is type(None):
                    continue
                return cls._structure_unstructurable_value(value, option, _ctx=_ctx)
            return value

        if origin in (dict,):
            value_type = args[1] if len(args) == 2 else Any
            return {
                key: cls._structure_unstructurable_value(item, value_type, _ctx=_ctx)
                for key, item in value.items()
            }

        if origin in (list, set, frozenset):
            value_type = args[0] if args else Any
            structured = [
                cls._structure_unstructurable_value(item, value_type, _ctx=_ctx)
                for item in value
            ]
            return origin(structured)

        if origin is tuple:
            if len(args) == 2 and args[1] is Ellipsis:
                return tuple(
                    cls._structure_unstructurable_value(item, args[0], _ctx=_ctx)
                    for item in value
                )
            return tuple(
                cls._structure_unstructurable_value(
                    item,
                    args[index] if index < len(args) else Any,
                    _ctx=_ctx,
                )
                for index, item in enumerate(value)
            )

        if isinstance(value, dict):
            cls_hint = value.get("kind", annotation)
            if isclass(cls_hint) and hasattr(cls_hint, "structure"):
                if "_ctx" in signature(cls_hint.structure).parameters:
                    return cls_hint.structure(value, _ctx=_ctx)
                return cls_hint.structure(value)
            if isclass(annotation):
                return annotation(**value)

        return value

    @classmethod
    def _unstructure_unstructurable_value(cls, value: Any) -> Any:
        """Unstructure a marked embedded value without falling back to model_dump."""
        unstructure = getattr(value, "unstructure", None)
        if callable(unstructure):
            return unstructure()
        if isinstance(value, dict):
            return {
                key: cls._unstructure_unstructurable_value(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._unstructure_unstructurable_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._unstructure_unstructurable_value(item) for item in value)
        if isinstance(value, set):
            return [cls._unstructure_unstructurable_value(item) for item in value]
        if isinstance(value, frozenset):
            return [cls._unstructure_unstructurable_value(item) for item in value]
        return value

    @staticmethod
    def _field_default(field_info: FieldInfo) -> Any:
        if field_info.default_factory is not None:
            return field_info.default_factory()
        return field_info.default

    def _should_unstructure_field(
        self,
        name: str,
        field_info: FieldInfo,
        value: Any,
    ) -> bool:
        if field_info.is_required():
            return True
        if name in self.model_fields_set:
            return True
        extra = field_info.json_schema_extra or {}
        if extra.get("include") is not True:
            return False

        default = self._field_default(field_info)
        if default is PydanticUndefined:
            return True
        return self._unstructure_unstructurable_value(value) != (
            self._unstructure_unstructurable_value(default)
        )

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
        unstructurable_fields = set(self._match_fields(unstructurable=True))
        data = self.model_dump(
            exclude=exclude_fields | unstructurable_fields,
            exclude_unset=True,
            exclude_defaults=True,
        )
        include_fields = (
            set(self._match_fields(include=True))
            - exclude_fields
            - unstructurable_fields
        )
        if include_fields:
            # Persist non-default values of opted-in fields even when they were
            # only mutated in place (exclude_unset would otherwise drop them);
            # exclude_defaults still elides untouched defaults so snapshots are
            # not chummed with empty/null state.
            data.update(
                self.model_dump(include=include_fields, exclude_defaults=True)
            )
        for name in unstructurable_fields:
            field_info = type(self).model_fields[name]
            value = getattr(self, name)
            if self._should_unstructure_field(name, field_info, value):
                data[name] = self._unstructure_unstructurable_value(value)
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

    seq: int = Field(
        None,
        init=False,
        validate_default=True,
        json_schema_extra={"dto_exclude": True},
    )
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

    locals: StringMap = Field(
        default_factory=dict,
        json_schema_extra={"contribute_ns": True},
    )
